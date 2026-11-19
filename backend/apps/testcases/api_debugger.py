"""
单接口在线调试引擎
- 变量替换与动态函数
- 真实 HTTP 请求 (requests)
- 断言校验 / 后置变量提取
- cURL (bash) 解析
"""
import json
import re
import uuid
import shlex
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit

import requests

REQUEST_TIMEOUT = 15
MAX_BODY_PREVIEW = 500

HTTP_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS')

VARIABLE_PATTERN = re.compile(r'\{\{\s*([^{}]+?)\s*\}\}')

# 断言类型别名兼容 (历史数据使用 json_path / text_contains)
ASSERTION_ALIASES = {
    'status_code': 'status_code',
    'json_path': 'jsonpath',
    'jsonpath': 'jsonpath',
    'response_text': 'response_text',
    'text_contains': 'response_text',
    'response_time': 'response_time',
    'header': 'header',
}

DEFAULT_OPERATOR = {
    'status_code': 'eq',
    'jsonpath': 'eq',
    'response_text': 'contains',
    'response_time': 'lte',
    'header': 'eq',
}


# ---------------- 变量引擎 ----------------
def _dynamic_value(name):
    """内置动态函数, 不支持时返回 None"""
    if name == '$timestamp':
        return str(int(datetime.now().timestamp()))
    if name == '$timestamp_ms':
        return str(int(datetime.now().timestamp() * 1000))
    if name == '$uuid':
        return str(uuid.uuid4())
    if name == '$random_int':
        return str(uuid.uuid4().int % 10000 + 1)
    return None


def render_template(text, variables, unresolved=None):
    """替换 {{变量}} 与 {{$动态函数}}, 未命中则保留原样并记录"""
    if not isinstance(text, str) or '{{' not in text:
        return text

    def _replace(match):
        name = match.group(1).strip()
        dynamic = _dynamic_value(name)
        if dynamic is not None:
            return dynamic
        if name in variables:
            value = variables[name]
            return '' if value is None else str(value)
        if unresolved is not None and name not in unresolved:
            unresolved.append(name)
        return match.group(0)

    return VARIABLE_PATTERN.sub(_replace, text)


def render_structure(value, variables, unresolved=None):
    """递归替换 dict / list / str 中的变量"""
    if isinstance(value, str):
        return render_template(value, variables, unresolved)
    if isinstance(value, list):
        return [render_structure(item, variables, unresolved) for item in value]
    if isinstance(value, dict):
        return {k: render_structure(v, variables, unresolved) for k, v in value.items()}
    return value


def join_url(url, base_url):
    """URL 不以 http 开头时拼接环境域名"""
    url = (url or '').strip()
    if not url:
        return ''
    if re.match(r'^https?://', url, re.I):
        return url
    if base_url:
        return f'{base_url.rstrip("/")}/{url.lstrip("/")}'
    return url


# ---------------- 请求参数归一化 ----------------
def _kv_items(raw):
    """支持 [{key,value,enabled}] / {k: v} / [[k, v]] 三种写法"""
    items = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            items.append({'key': str(key), 'value': '' if value is None else str(value),
                          'enabled': True})
    elif isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                key = str(entry.get('key', '') or '').strip()
                if not key or entry.get('enabled') is False:
                    continue
                value = entry.get('value', '')
                items.append({
                    'key': key,
                    'value': '' if value is None else str(value),
                    'enabled': True,
                })
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                key = str(entry[0]).strip()
                if key:
                    items.append({'key': key, 'value': str(entry[1]), 'enabled': True})
    return items


def _form_items(raw):
    """form-data / urlencoded 的键值对"""
    return _kv_items(raw)


# ---------------- JSONPath ----------------
JSON_PATH_TOKEN = re.compile(r'\.([^.\[\]]+)|\[(\d+)\]|\[\'([^\']*)\'\]|\["([^"]*)"\]')


def resolve_json_path(data, path):
    """解析 $.data.token / $.list[0].id / $[0].name 形式的简易 JSONPath"""
    if path is None:
        raise KeyError('缺少 JSONPath 表达式')
    expr = str(path).strip()
    if not expr or expr == '$':
        return data
    if not expr.startswith('$'):
        expr = '$' + expr
    remainder = expr[1:]
    tokens = []
    for match in JSON_PATH_TOKEN.finditer(remainder):
        dotted, index, single, double = match.groups()
        if index is not None:
            tokens.append(int(index))
        elif dotted is not None:
            tokens.append(dotted)
        elif single is not None:
            tokens.append(single)
        elif double is not None:
            tokens.append(double)
    if not tokens:
        raise KeyError(f'无法解析 JSONPath: {path}')

    current = data
    for token in tokens:
        if isinstance(token, int):
            if isinstance(current, list) and 0 <= token < len(current):
                current = current[token]
            else:
                raise KeyError(f'数组下标越界: [{token}]')
        else:
            if isinstance(current, dict) and token in current:
                current = current[token]
            else:
                raise KeyError(f'字段不存在: {token}')
    return current


# ---------------- 断言 ----------------
def _to_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (TypeError, ValueError):
            return None
    return None


def _truncate(value):
    text = value if isinstance(value, str) else json.dumps(
        value, ensure_ascii=False, default=str)
    if len(text) > MAX_BODY_PREVIEW:
        return text[:MAX_BODY_PREVIEW] + '...'
    return text


def compare_values(actual, operator, expected):
    """返回 (是否通过, 说明)"""
    operator = (operator or 'eq').lower()

    if operator in ('exists', 'not_exists'):
        exists = actual is not None
        passed = exists if operator == 'exists' else not exists
        return passed, '值存在' if exists else '值为空'

    if operator == 'contains':
        return str(expected) in str(actual if actual is not None else ''), ''
    if operator == 'not_contains':
        return str(expected) not in str(actual if actual is not None else ''), ''

    if operator in ('gt', 'gte', 'lt', 'lte'):
        left, right = _to_number(actual), _to_number(expected)
        if left is None or right is None:
            return False, '无法转换为数字比较'
        ops = {
            'gt': left > right,
            'gte': left >= right,
            'lt': left < right,
            'lte': left <= right,
        }
        return ops[operator], ''

    if operator == 'ne':
        return _values_equal(actual, expected) is False, ''

    return _values_equal(actual, expected), ''


def _values_equal(actual, expected):
    left_num, right_num = _to_number(actual), _to_number(expected)
    if left_num is not None and right_num is not None:
        return left_num == right_num
    if actual is None and expected in (None, ''):
        return True
    return str(actual) == str(expected)


def evaluate_assertions(assertions, response, response_json, elapsed_ms):
    results = []
    for index, rule in enumerate(assertions or [], start=1):
        if not isinstance(rule, dict):
            continue
        raw_type = str(rule.get('type') or 'status_code')
        assert_type = ASSERTION_ALIASES.get(raw_type, 'status_code')
        operator = rule.get('operator') or DEFAULT_OPERATOR.get(assert_type, 'eq')
        expression = rule.get('expression') or rule.get('path') or ''
        expected = rule.get('expected', '')

        item = {
            'index': index,
            'name': rule.get('name') or f'断言 {index}',
            'type': assert_type,
            'type_label': {
                'status_code': '状态码',
                'jsonpath': 'JSON 字段',
                'response_text': '响应文本',
                'response_time': '响应耗时',
                'header': '响应头',
            }.get(assert_type, assert_type),
            'expression': expression,
            'operator': operator,
            'expected': expected,
            'actual': None,
            'passed': False,
            'message': '',
        }

        try:
            if assert_type == 'status_code':
                actual = response.status_code
            elif assert_type == 'response_time':
                actual = round(elapsed_ms)
            elif assert_type == 'response_text':
                actual = response.text
            elif assert_type == 'header':
                header_name = str(expression).strip().lower()
                actual = response.headers.get(header_name, '')
            else:
                if response_json is None:
                    raise ValueError('响应不是合法 JSON, 无法按 JSONPath 断言')
                actual = resolve_json_path(response_json, expression)

            item['actual'] = _truncate(actual)
            passed, note = compare_values(actual, operator, expected)
            item['passed'] = passed
            item['message'] = note or ('断言通过' if passed else '断言未通过')
        except KeyError as exc:
            item['actual'] = '字段缺失'
            item['message'] = f'取值失败: {exc.args[0] if exc.args else exc}'
        except ValueError as exc:
            item['actual'] = '无法取值'
            item['message'] = str(exc)
        except Exception as exc:  # noqa: BLE001
            item['actual'] = '异常'
            item['message'] = f'断言执行异常: {exc}'
        results.append(item)
    return results


# ---------------- 变量提取 ----------------
def extract_variables(extract_rules, response, response_json):
    """按规则从响应中提取变量, 返回 [{variable, value, success, message}]"""
    results = []
    for index, rule in enumerate(extract_rules or [], start=1):
        if not isinstance(rule, dict):
            continue
        variable = str(rule.get('variable') or '').strip()
        source = str(rule.get('source') or rule.get('type') or 'jsonpath').lower()
        expression = rule.get('expression') or rule.get('path') or ''
        item = {'variable': variable, 'value': '', 'success': False, 'message': ''}

        if not variable:
            item['message'] = '变量名不能为空'
            results.append(item)
            continue

        try:
            if source == 'header':
                value = response.headers.get(str(expression).strip().lower(), '')
                if value == '':
                    raise KeyError(f'响应头不存在: {expression}')
            elif source == 'status_code':
                value = response.status_code
            else:
                if response_json is None:
                    raise ValueError('响应不是合法 JSON')
                value = resolve_json_path(response_json, expression)

            if isinstance(value, (dict, list)):
                item['value'] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                item['value'] = ''
            else:
                item['value'] = str(value)
            item['success'] = True
            item['message'] = '提取成功'
        except (KeyError, ValueError) as exc:
            item['message'] = str(exc.args[0] if exc.args else exc)
        except Exception as exc:  # noqa: BLE001
            item['message'] = f'提取异常: {exc}'
        results.append(item)
    return results


# ---------------- 请求执行 ----------------
def _size_text(size):
    if size < 1024:
        return f'{size} B'
    if size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    return f'{size / (1024 * 1024):.2f} MB'


def _prepare_body(body_type, body, headers):
    """返回 (json_payload, data_payload, files_payload)"""
    body_type = (body_type or 'none').lower()
    if body_type == 'none' or body is None or body == '':
        return None, None, None

    if body_type == 'json':
        text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        try:
            return json.loads(text), None, None
        except (TypeError, ValueError):
            return None, text.encode('utf-8'), None

    items = _form_items(body)
    payload = {item['key']: item['value'] for item in items}
    if body_type == 'form-data':
        return None, payload, None
    return None, payload, None


def execute_debug(config, environment=None):
    """执行一次调试请求, 返回结构化结果"""
    unresolved = []
    variables = dict((environment.variables or {})) if environment else {}
    base_url = (environment.base_url or '') if environment else ''

    method = str(config.get('method') or 'GET').upper()
    raw_url = str(config.get('url') or '').strip()

    resolved_url = join_url(render_template(raw_url, variables, unresolved), base_url)
    headers_in = _kv_items(render_structure(config.get('headers') or [], variables, unresolved))
    params_in = _kv_items(render_structure(config.get('params') or [], variables, unresolved))

    body_type = str(config.get('body_type') or 'none').lower()
    body_raw = render_structure(config.get('body'), variables, unresolved) \
        if isinstance(config.get('body'), (dict, list)) \
        else render_template(config.get('body') or '', variables, unresolved)
    if body_type == 'none':
        body_raw = None

    request_snapshot = {
        'method': method,
        'url': resolved_url,
        'base_url': base_url,
        'headers': headers_in,
        'params': params_in,
        'body_type': body_type,
        'body': body_raw if isinstance(body_raw, str) else json.dumps(
            body_raw, ensure_ascii=False) if body_raw is not None else '',
        'unresolved_variables': unresolved,
    }

    if not resolved_url:
        return {
            'success': False,
            'error': '请求 URL 不能为空',
            'request': request_snapshot,
        }
    if not re.match(r'^https?://', resolved_url, re.I):
        return {
            'success': False,
            'error': 'URL 必须以 http:// 或 https:// 开头, 或先在环境中选择域名',
            'request': request_snapshot,
        }

    headers = {item['key']: item['value'] for item in headers_in}
    params = {item['key']: item['value'] for item in params_in}
    json_payload, data_payload, files_payload = _prepare_body(body_type, body_raw, headers)

    if body_type == 'json' and 'Content-Type' not in headers and 'content-type' not in headers:
        headers['Content-Type'] = 'application/json'
    if body_type == 'urlencoded' and 'Content-Type' not in headers and 'content-type' not in headers:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

    started = datetime.now()
    try:
        response = requests.request(
            method=method,
            url=resolved_url,
            headers=headers,
            params=params or None,
            json=json_payload,
            data=data_payload,
            files=files_payload,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': f'请求超时: 超过 {REQUEST_TIMEOUT} 秒未收到响应',
            'request': request_snapshot,
        }
    except requests.exceptions.SSLError as exc:
        return {
            'success': False,
            'error': f'SSL 证书校验失败: {exc}',
            'request': request_snapshot,
        }
    except requests.exceptions.MissingSchema:
        return {
            'success': False,
            'error': 'URL 缺少 http:// 或 https:// 协议前缀',
            'request': request_snapshot,
        }
    except requests.exceptions.ConnectionError as exc:
        host = urlsplit(resolved_url).hostname or resolved_url
        return {
            'success': False,
            'error': f'无法连接目标服务 {host}, 请检查域名、端口、网络或服务是否启动',
            'error_detail': str(exc)[:300],
            'request': request_snapshot,
        }
    except requests.exceptions.InvalidURL:
        return {
            'success': False,
            'error': 'URL 格式不正确, 请检查变量替换后的地址',
            'request': request_snapshot,
        }
    except requests.exceptions.RequestException as exc:
        return {
            'success': False,
            'error': f'请求发送失败: {exc}',
            'request': request_snapshot,
        }

    elapsed_ms = (datetime.now() - started).total_seconds() * 1000
    size = len(response.content or b'')

    response_json = None
    try:
        response_json = response.json()
    except ValueError:
        response_json = None

    body_text = response.text
    content_type = response.headers.get('Content-Type', '')

    assertions = evaluate_assertions(
        config.get('assertions') or [], response, response_json, elapsed_ms)
    extracts = extract_variables(
        config.get('extract_rules') or [], response, response_json)

    updated_variables = {}
    if config.get('sync_variables') and environment is not None:
        merged = dict(environment.variables or {})
        for item in extracts:
            if item['success'] and item['variable']:
                merged[item['variable']] = item['value']
                updated_variables[item['variable']] = item['value']
        if updated_variables:
            environment.variables = merged
            environment.save(update_fields=['variables', 'updated_at'])

    return {
        'success': True,
        'request': request_snapshot,
        'response': {
            'status_code': response.status_code,
            'reason': response.reason or '',
            'elapsed_ms': round(elapsed_ms, 2),
            'size_bytes': size,
            'size_text': _size_text(size),
            'content_type': content_type,
            'headers': dict(response.headers),
            'body': body_text,
            'json': response_json,
            'is_json': response_json is not None,
        },
        'assertions': assertions,
        'assertions_passed': all(item['passed'] for item in assertions) if assertions else True,
        'assertions_total': len(assertions),
        'assertions_failed': sum(1 for item in assertions if not item['passed']),
        'extracts': extracts,
        'updated_variables': updated_variables,
    }


# ---------------- cURL 解析 ----------------
CURL_VALUE_FLAGS = {
    '-X', '--request', '-H', '--header', '-d', '--data', '--data-raw',
    '--data-binary', '--data-ascii', '--data-urlencode', '-F', '--form',
    '-b', '--cookie', '-u', '--user', '--url', '-A', '--user-agent',
    '-e', '--referer', '-o', '--output', '-x', '--proxy', '--connect-timeout',
    '-m', '--max-time', '--cert', '--key', '--cacert',
}
CURL_BOOL_FLAGS = {
    '-k', '--insecure', '-L', '--location', '-s', '--silent', '-i',
    '--include', '-v', '--verbose', '-g', '--globoff', '--compressed',
    '--http1.1', '--http2',
}


def _tokenize_curl(command):
    text = (command or '').replace('\r', '')
    text = re.sub(r'\\\n', ' ', text)
    text = re.sub(r'\^\n', ' ', text)
    text = text.strip()
    if text.lower().startswith('curl'):
        text = text[4:].strip()
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        # 引号不闭合等异常时退回按空白切分
        return [token.strip('\'"') for token in text.split()]


def _is_flag(token, flags):
    """短参数区分大小写 (-H / -F), 长参数忽略大小写"""
    return token in flags or (token.startswith('--') and token.lower() in flags)


def parse_curl(command):
    """解析 bash 风格的 cURL 命令"""
    if not (command or '').strip():
        raise ValueError('cURL 内容不能为空')

    tokens = _tokenize_curl(command)
    if not tokens:
        raise ValueError('未解析到 cURL 参数')

    method = ''
    url = ''
    headers = []
    data_parts = []
    forms = []
    cookies = []
    auth = ''
    warnings = []

    index = 0
    while index < len(tokens):
        token = tokens[index]

        if _is_flag(token, CURL_VALUE_FLAGS):
            if index + 1 >= len(tokens):
                break
            value = tokens[index + 1]
            lower = token.lower()
            if token == '-X' or lower == '--request':
                method = value.upper()
            elif token == '-H' or lower == '--header':
                headers.append(value)
            elif token in ('-d', '--data', '--data-raw', '--data-binary', '--data-ascii') \
                    or lower == '--data-urlencode':
                data_parts.append(value)
            elif token == '-F' or lower == '--form':
                forms.append(value)
            elif token == '-b' or lower == '--cookie':
                cookies.append(value)
            elif token == '-u' or lower == '--user':
                auth = value
            elif lower == '--url':
                url = value
            elif token == '-A' or lower == '--user-agent':
                headers.append(f'User-Agent: {value}')
            elif token == '-e' or lower == '--referer':
                headers.append(f'Referer: {value}')
            index += 2
            continue

        if _is_flag(token, CURL_BOOL_FLAGS):
            index += 1
            continue

        if token.startswith('-'):
            # 未知参数, 跳过可能的值
            if index + 1 < len(tokens) and not tokens[index + 1].startswith('-'):
                index += 2
            else:
                index += 1
            continue

        if not url:
            url = token
        index += 1

    if not url:
        raise ValueError('未在 cURL 中找到请求 URL')

    if cookies:
        headers.append(f'Cookie: {"; ".join(cookies)}')
    if auth:
        import base64
        encoded = base64.b64encode(auth.encode('utf-8')).decode('ascii')
        headers.append(f'Authorization: Basic {encoded}')

    # URL 拆分查询参数
    parts = urlsplit(url)
    params = [
        {'key': key, 'value': value, 'enabled': True}
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    clean_url = parts._replace(query='', fragment='').geturl()

    # 请求头
    header_items = []
    content_type = ''
    for raw in headers:
        if ':' not in raw:
            warnings.append(f'已忽略无法解析的请求头: {raw}')
            continue
        key, value = raw.split(':', 1)
        key = key.strip()
        value = value.strip()
        header_items.append({'key': key, 'value': value, 'enabled': True})
        if key.lower() == 'content-type':
            content_type = value.lower()

    # 请求体
    body_type = 'none'
    body = ''
    form_items = []

    if forms:
        body_type = 'form-data'
        for raw in forms:
            if '=' in raw:
                key, value = raw.split('=', 1)
                form_items.append({'key': key.strip(), 'value': value.strip(), 'enabled': True})
    elif data_parts:
        raw_body = '&'.join(data_parts)
        if 'application/x-www-form-urlencoded' in content_type and '=' in raw_body:
            body_type = 'urlencoded'
            form_items = [
                {'key': key, 'value': value, 'enabled': True}
                for key, value in parse_qsl(raw_body, keep_blank_values=True)
            ]
        else:
            body_type = 'json'
            body = raw_body
            if not content_type:
                header_items.append(
                    {'key': 'Content-Type', 'value': 'application/json', 'enabled': True})
    elif 'application/x-www-form-urlencoded' in content_type:
        body_type = 'urlencoded'

    if not method:
        method = 'POST' if (data_parts or forms) else 'GET'

    if method not in HTTP_METHODS:
        warnings.append(f'未知请求方法 {method}, 已回退为 GET')
        method = 'GET'

    return {
        'method': method,
        'url': clean_url,
        'headers': header_items,
        'params': params,
        'body_type': body_type,
        'body': body,
        'form_body': form_items,
        'warnings': warnings,
    }
