"""登录 / 注册限流, 缓解暴力破解与批量注册"""
from rest_framework.throttling import SimpleRateThrottle


class _BaseAuthThrottle(SimpleRateThrottle):
    """以 客户端标识 + 用户名 为维度限流"""

    def get_cache_key(self, request, view):
        username = ''
        if isinstance(request.data, dict):
            username = str(request.data.get('username') or '')[:64]
        return self.cache_format % {
            'scope': self.scope,
            'ident': f'{self.get_ident(request)}:{username}',
        }


class LoginRateThrottle(_BaseAuthThrottle):
    """登录限流 (默认 10 次/分钟, 可通过 LOGIN_THROTTLE_RATE 覆盖)"""

    scope = 'login'


class RegisterRateThrottle(_BaseAuthThrottle):
    """注册限流 (默认 20 次/小时, 可通过 REGISTER_THROTTLE_RATE 覆盖)"""

    scope = 'register'
