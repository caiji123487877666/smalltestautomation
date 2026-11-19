"""安全相关测试: SSRF 防护与配置约束"""
import pytest
from django.test import override_settings

from apps.testcases.api_debugger import (
    UnsafeUrlError,
    execute_debug,
    validate_outbound_url,
)


@pytest.mark.parametrize('url', [
    'http://127.0.0.1:8000/api/secret',
    'http://localhost/admin',
    'http://10.0.0.5/internal',
    'http://192.168.1.1/',
    'http://169.254.169.254/latest/meta-data/',
    'http://[::1]/',
])
def test_private_network_is_blocked(url):
    with pytest.raises(UnsafeUrlError):
        validate_outbound_url(url, allow_private=False)


@pytest.mark.parametrize('url', [
    'file:///etc/passwd',
    'ftp://example.com/file',
    'gopher://example.com/',
    'http:///no-host',
])
def test_invalid_scheme_is_blocked(url):
    with pytest.raises(UnsafeUrlError):
        validate_outbound_url(url, allow_private=False)


def test_public_ip_is_allowed():
    # IP 字面量无需 DNS 解析, 不依赖外网
    assert validate_outbound_url('http://93.184.216.34/path', allow_private=False) is True


def test_allow_private_explicitly():
    assert validate_outbound_url('http://127.0.0.1:8000', allow_private=True) is True


@override_settings(API_DEBUG_ALLOW_PRIVATE_NETWORK=False)
def test_execute_debug_blocks_private_target_without_sending_request():
    result = execute_debug({'method': 'GET', 'url': 'http://127.0.0.1:8000/health'})
    assert result['success'] is False
    assert '安全策略拦截' in result['error']
    assert result['request']['url'] == 'http://127.0.0.1:8000/health'


def test_execute_debug_requires_http_scheme():
    result = execute_debug({'method': 'GET', 'url': 'example.com/api'})
    assert result['success'] is False
    assert 'http' in result['error']


@override_settings(API_DEBUG_ALLOW_PRIVATE_NETWORK=True)
def test_execute_debug_allows_private_when_enabled(monkeypatch):
    """开启开关后应放行内网地址 (用假请求避免真实网络)"""
    calls = {}

    class FakeResponse:
        status_code = 200
        reason = 'OK'
        headers = {'Content-Type': 'application/json'}
        content = b'{}'
        text = '{}'

        def json(self):
            return {}

        @property
        def is_redirect(self):
            return False

    def fake_request(method, url, **kwargs):
        calls['url'] = url
        return FakeResponse()

    monkeypatch.setattr('apps.testcases.api_debugger.requests.request', fake_request)
    result = execute_debug({'method': 'GET', 'url': 'http://127.0.0.1:8000/health'})
    assert result['success'] is True
    assert calls['url'] == 'http://127.0.0.1:8000/health'


@override_settings(API_DEBUG_ALLOW_PRIVATE_NETWORK=False)
def test_redirect_to_private_network_is_blocked(monkeypatch):
    """302 跳转到内网地址必须被拦截, 防止绕过"""
    redirect_response = type('R', (), {
        'status_code': 302,
        'headers': {'Location': 'http://169.254.169.254/latest/meta-data/'},
        'is_redirect': True,
    })()

    monkeypatch.setattr(
        'apps.testcases.api_debugger.requests.request',
        lambda *args, **kwargs: redirect_response,
    )
    result = execute_debug({'method': 'GET', 'url': 'http://93.184.216.34/start'})
    assert result['success'] is False
    assert '安全策略拦截' in result['error']
