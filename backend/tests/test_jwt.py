"""JWT 注销与改密后 token 失效"""
LOGIN_URL = '/api/users/login/'
LOGOUT_URL = '/api/users/logout/'
REFRESH_URL = '/api/users/token/refresh/'


def _login(api_client, username='tester1', password='TestPass123'):
    resp = api_client.post(LOGIN_URL, {'username': username, 'password': password}, format='json')
    assert resp.status_code == 200
    return resp.data


def test_logout_blacklists_refresh_token(api_client, user):
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    assert api_client.post(LOGOUT_URL, {'refresh': tokens['refresh']}, format='json').status_code == 200
    # 已注销的 refresh token 不能再换发 access token
    assert api_client.post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json').status_code == 401


def test_refresh_rotates_and_blacklists_old_token(api_client, user):
    tokens = _login(api_client)

    first = api_client.post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json')
    assert first.status_code == 200
    assert first.data.get('refresh') and first.data['refresh'] != tokens['refresh']

    # 旧 refresh token 已随轮换进入黑名单
    assert api_client.post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json').status_code == 401


def test_logout_requires_refresh_token(api_client, user):
    tokens = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api_client.post(LOGOUT_URL, {}, format='json').status_code == 400


def test_reset_password_blacklists_existing_refresh_token(admin_client, user):
    tokens = _login(admin_client)

    resp = admin_client.post(
        f'/api/users/admin/users/{user.id}/reset-password/',
        {'password': 'Str0ngPass!2026'},
        format='json',
    )
    assert resp.status_code == 200
    assert admin_client.post(REFRESH_URL, {'refresh': tokens['refresh']}, format='json').status_code == 401
