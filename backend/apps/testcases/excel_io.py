"""
Excel 导入导出 & Swagger 导入
"""
import io
import json

from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from apps.projects.models import TestModule
from .models import TestCase
from .services import generate_case_no
from .serializers import normalize_api_steps, normalize_web_steps

TEMPLATE_HEADERS = [
    '用例编号(留空自动生成)',
    '用例标题*',
    '模块名称',
    '用例类型(API/WEB)',
    '优先级(P0-P3)',
    '状态(草稿/可用/已废弃)',
    '前置条件',
    '标签(逗号分隔)',
    '步骤(JSON)',
]

STATUS_MAP = {
    '草稿': 'DRAFT', 'DRAFT': 'DRAFT',
    '可用': 'ACTIVE', 'ACTIVE': 'ACTIVE',
    '已废弃': 'DEPRECATED', 'DEPRECATED': 'DEPRECATED',
}

STATUS_LABEL = {'DRAFT': '草稿', 'ACTIVE': '可用', 'DEPRECATED': '已废弃'}

API_STEP_SAMPLE = {
    'method': 'GET',
    'url': 'https://api.example.com/v1/users',
    'headers': [{'key': 'Authorization', 'value': 'Bearer {{token}}'}],
    'params': [{'key': 'page', 'value': '1'}],
    'body_type': 'none',
    'body': '',
    'assertions': [{'type': 'status_code', 'expression': '', 'expected': '200'}],
}

WEB_STEP_SAMPLE = [
    {'action': 'goto', 'selector': '', 'value': 'https://example.com/login',
     'element_desc': '打开登录页', 'ai_healed_selector': ''},
    {'action': 'fill', 'selector': '#username', 'value': 'admin',
     'element_desc': '用户名输入框', 'ai_healed_selector': ''},
    {'action': 'click', 'selector': 'button[type=submit]', 'value': '',
     'element_desc': '登录按钮', 'ai_healed_selector': ''},
    {'action': 'assert_text', 'selector': '.welcome', 'value': '欢迎',
     'element_desc': '欢迎语', 'ai_healed_selector': ''},
]


def _style_header(ws, headers):
    for col, name in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=name)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='409EFF')
        cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[cell.column_letter].width = 22
    ws.freeze_panes = 'A2'


def build_import_template():
    """构建导入模板 (数据页 + 说明页)"""
    wb = Workbook()
    ws = wb.active
    ws.title = '用例数据'
    _style_header(ws, TEMPLATE_HEADERS)

    # 示例行: API
    sample_steps = json.dumps(API_STEP_SAMPLE, ensure_ascii=False)
    ws.append([
        '', '示例-用户列表接口', '用户模块', 'API', 'P1', '草稿',
        '已登录获取 token', '冒烟,核心链路', sample_steps,
    ])
    # 示例行: WEB
    ws.append([
        '', '示例-登录流程', '登录模块', 'WEB', 'P0', '草稿',
        '', '冒烟',
        json.dumps(WEB_STEP_SAMPLE, ensure_ascii=False),
    ])

    guide = wb.create_sheet('填写说明')
    guide_rows = [
        ('字段', '说明'),
        ('用例编号', '可留空, 系统按项目自动生成 TC-0001 递增编号'),
        ('用例标题', '必填, 最大 255 字符'),
        ('模块名称', '可选, 不存在时自动在项目下创建一级模块'),
        ('用例类型', 'API 或 WEB (默认 API)'),
        ('优先级', 'P0 / P1 / P2 / P3 (默认 P1)'),
        ('状态', '草稿 / 可用 / 已废弃 (默认 草稿)'),
        ('前置条件', '可选, 文本'),
        ('标签', '多个标签用英文或中文逗号分隔, 如: 冒烟,核心链路'),
        ('步骤', 'JSON 字符串。API 类型为对象(method/url/headers/params/body_type/body/assertions); '
                 'WEB 类型为步骤数组(action/selector/value/element_desc/ai_healed_selector)'),
        ('提示', '请勿修改表头及表名 "用例数据", 单次建议不超过 500 行'),
    ]
    for row in guide_rows:
        guide.append(list(row))
    guide.column_dimensions['A'].width = 16
    guide.column_dimensions['B'].width = 90
    for cell in guide[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='67C23A')

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def export_cases_to_workbook(cases):
    """导出用例为 Excel"""
    wb = Workbook()
    ws = wb.active
    ws.title = '测试用例'
    _style_header(ws, TEMPLATE_HEADERS)

    for case in cases:
        steps = case.steps
        if case.case_type == 'WEB':
            steps_json = json.dumps(steps or [], ensure_ascii=False)
        else:
            steps_json = json.dumps(steps or {}, ensure_ascii=False)
        ws.append([
            case.case_no,
            case.title,
            case.module.name if case.module else '',
            case.case_type,
            case.priority,
            STATUS_LABEL.get(case.status, case.status),
            case.precondition or '',
            ','.join(case.tags or []),
            steps_json,
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _get_or_create_module(project, module_name):
    if not module_name:
        return None
    module = TestModule.objects.filter(project=project, name=module_name, parent__isnull=True).first()
    if module:
        return module
    return TestModule.objects.create(project=project, name=module_name)


def import_cases_from_excel(file_obj, project, user):
    """解析 Excel 批量入库, 返回成功/失败明细"""
    try:
        wb = load_workbook(file_obj, data_only=True)
    except Exception as exc:  # noqa: BLE001
        return {'success': 0, 'failed': 1, 'errors': [{'row': 0, 'msg': f'文件解析失败: {exc}'}]}

    ws = wb['用例数据'] if '用例数据' in wb.sheetnames else wb.active

    success, errors = 0, []
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for idx, row in enumerate(rows, start=2):
        if row is None or all(cell is None or str(cell).strip() == '' for cell in row):
            continue
        row = list(row) + [None] * (9 - len(row))
        case_no_raw, title, module_name, case_type, priority, status, precondition, tags_raw, steps_raw = row[:9]

        title = (str(title).strip() if title else '')
        if not title:
            errors.append({'row': idx, 'msg': '用例标题不能为空'})
            continue

        case_type = (str(case_type).strip().upper() if case_type else 'API')
        if case_type not in ('API', 'WEB'):
            errors.append({'row': idx, 'msg': f'用例类型 "{case_type}" 非法, 只能是 API/WEB'})
            continue

        priority = (str(priority).strip().upper() if priority else 'P1')
        if priority not in ('P0', 'P1', 'P2', 'P3'):
            errors.append({'row': idx, 'msg': f'优先级 "{priority}" 非法, 只能是 P0-P3'})
            continue

        status_raw = (str(status).strip() if status else '草稿')
        status = STATUS_MAP.get(status_raw)
        if not status:
            errors.append({'row': idx, 'msg': f'状态 "{status_raw}" 非法, 只能是 草稿/可用/已废弃'})
            continue

        tags = []
        if tags_raw:
            raw = str(tags_raw).replace('，', ',')
            tags = [t.strip() for t in raw.split(',') if t.strip()]

        # 解析步骤
        steps_value = {} if case_type == 'API' else []
        if steps_raw and str(steps_raw).strip():
            try:
                parsed = json.loads(str(steps_raw))
            except json.JSONDecodeError as exc:
                errors.append({'row': idx, 'msg': f'步骤 JSON 解析失败: {exc}'})
                continue
            steps_value = normalize_web_steps(parsed) if case_type == 'WEB' else normalize_api_steps(parsed)
        else:
            steps_value = normalize_api_steps({}) if case_type == 'API' else []

        try:
            with transaction.atomic():
                module = _get_or_create_module(project, str(module_name).strip() if module_name else '')
                case_no = (str(case_no_raw).strip() if case_no_raw else '')
                if not case_no or TestCase.objects.filter(project=project, case_no=case_no).exists():
                    case_no = generate_case_no(project)
                TestCase.objects.create(
                    project=project,
                    module=module,
                    case_no=case_no,
                    title=title[:255],
                    case_type=case_type,
                    priority=priority,
                    status=status,
                    precondition=(str(precondition).strip() if precondition else ''),
                    tags=tags,
                    steps=steps_value,
                    creator=user,
                    updater=user,
                )
            success += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({'row': idx, 'msg': f'入库失败: {exc}'})

    return {'success': success, 'failed': len(errors), 'errors': errors}


def import_cases_from_swagger(file_obj, project, user):
    """解析 Swagger/OpenAPI JSON, 生成 API 类型用例"""
    try:
        raw = file_obj.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8-sig')
        spec = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return {'success': 0, 'failed': 1, 'errors': [{'row': 0, 'msg': f'Swagger 解析失败: {exc}'}]}

    paths = spec.get('paths')
    if not isinstance(paths, dict):
        return {'success': 0, 'failed': 1, 'errors': [{'row': 0, 'msg': '文件不是合法的 Swagger/OpenAPI 文档(缺少 paths)'}]}

    base_url = ''
    servers = spec.get('servers')
    if isinstance(servers, list) and servers:
        base_url = (servers[0] or {}).get('url', '') or ''
    else:
        host = spec.get('host') or ''
        base_path = spec.get('basePath') or ''
        schemes = spec.get('schemes') or []
        if host:
            base_url = f'{schemes[0] if schemes else "http"}://{host}{base_path}'

    success, errors = 0, []
    row = 0
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method in ('get', 'post', 'put', 'delete', 'patch'):
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            row += 1
            title = op.get('summary') or op.get('operationId') or f'{method.upper()} {path}'
            headers, params = [], []
            for p in (op.get('parameters') or []) + (item.get('parameters') or []):
                if not isinstance(p, dict):
                    continue
                name = p.get('name')
                if not name:
                    continue
                location = p.get('in')
                example = ''
                if isinstance(p.get('example'), (str, int, float)):
                    example = str(p.get('example'))
                elif isinstance(p.get('default'), (str, int, float)):
                    example = str(p.get('default'))
                if location == 'header':
                    headers.append({'key': name, 'value': example})
                elif location == 'query':
                    params.append({'key': name, 'value': example})

            body_type, body = 'none', ''
            request_body = op.get('requestBody')
            if isinstance(request_body, dict):
                body_type = 'json'
                content = (request_body.get('content') or {})
                if 'application/json' in content:
                    body = json.dumps(
                        (content['application/json'].get('schema') or {}), ensure_ascii=False)
                elif 'application/x-www-form-urlencoded' in content:
                    body_type = 'form'

            steps = normalize_api_steps({
                'method': method.upper(),
                'url': f'{base_url}{path}' if base_url else path,
                'headers': headers,
                'params': params,
                'body_type': body_type,
                'body': body,
                'assertions': [{'type': 'status_code', 'expression': '', 'expected': '200'}],
            })

            try:
                with transaction.atomic():
                    TestCase.objects.create(
                        project=project,
                        case_no=generate_case_no(project),
                        title=str(title)[:255],
                        case_type='API',
                        priority='P2',
                        status='DRAFT',
                        precondition='',
                        tags=[t for t in (op.get('tags') or []) if isinstance(t, str)],
                        steps=steps,
                        creator=user,
                        updater=user,
                    )
                success += 1
            except Exception as exc:  # noqa: BLE001
                errors.append({'row': row, 'msg': f'{method.upper()} {path}: {exc}'})

    if row == 0:
        return {'success': 0, 'failed': 0, 'errors': [{'row': 0, 'msg': '未在文件中找到任何接口定义'}]}
    return {'success': success, 'failed': len(errors), 'errors': errors}
