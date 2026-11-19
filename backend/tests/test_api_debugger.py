"""调试引擎纯函数测试"""
from apps.testcases.api_debugger import (
    parse_curl,
    render_template,
    resolve_json_path,
)


def test_render_template_with_variables_and_dynamic_functions():
    unresolved = []
    rendered = render_template('{{host}}/api/{{$uuid}}/{{missing}}', {'host': 'https://demo'}, unresolved)
    assert rendered.startswith('https://demo/api/')
    assert '{{missing}}' in rendered
    assert unresolved == ['missing']


def test_resolve_json_path():
    payload = {'data': {'list': [{'id': 7}]}}
    assert resolve_json_path(payload, '$.data.list[0].id') == 7


def test_parse_curl():
    command = (
        "curl 'https://api.demo.com/users?page=2' "
        "-X POST -H 'Content-Type: application/json' "
        "-d '{\"name\":\"tom\"}'"
    )
    parsed = parse_curl(command)
    assert parsed['method'] == 'POST'
    assert parsed['url'] == 'https://api.demo.com/users'
    assert parsed['params'] == [{'key': 'page', 'value': '2', 'enabled': True}]
    assert parsed['body_type'] == 'json'
