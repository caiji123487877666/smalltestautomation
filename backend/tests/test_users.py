"""用户认证、限流与密码重置测试"""
import pytest
from django.contrib.auth import authenticate, get_user_model

from utils.throttles import LoginRateThrottle

User = get_user_model()
LOGIN_URL = '/api/users/login/'
REGISTER_URL = '/api/users/register/'
ADMIN_USERS_URL = '/api/users/admin/users/'


def test_login_success(api_client, user):
    resp = api_client.post(LOGIN_URL, {'username': 'tester1', 'password': 'TestPass123'}, format='json')
    assert resp.status_code == 200
    assert resp.data['access']
    assert resp.data['refresh']


def test_login_wrong_password(api_client, user):
    resp = api_client.post(LOGIN_URL, {'username': 'tester1', 'password': 'wrong-pass'}, format='json')
    assert resp.status_code == 400


def test_login_is_throttled(api_client, user, monkeypatch):
    monkeypatch.setitem(LoginRateThrottle.THROTTLE_RATES, 'login', '2/min')
    payload = {'username': 'tester1', 'password': 'wrong-pass'}
    assert api_client.post(LOGIN_URL, payload, format='json').status_code == 400
    assert api_client.post(LOGIN_URL, payload, format='json').status_code == 400
    assert api_client.post(LOGIN_URL, payload, format='json').status_code == 429


def test_register_creates_user(api_client, db):
    resp = api_client.post(
        REGISTER_URL,
        {'username': 'newbie', 'password': 'Str0ngPass!2026', 'email': 'n@example.com'},
        format='json',
    )
    assert resp.status_code == 201
    assert User.objects.filter(username='newbie').exists()


def test_register_rejects_short_password(api_client, db):
    resp = api_client.post(REGISTER_URL, {'username': 'shorty', 'password': '123'}, format='json')
    assert resp.status_code == 400


def test_reset_password_requires_admin(auth_client, user):
    resp = auth_client.post(f'{ADMIN_USERS_URL}{user.id}/reset-password/',
                            {'password': 'Str0ngPass!2026'}, format='json')
    assert resp.status_code == 403


def test_reset_password_requires_password(admin_client, user):
    resp = admin_client.post(f'{ADMIN_USERS_URL}{user.id}/reset-password/', {}, format='json')
    assert resp.status_code == 400


@pytest.mark.parametrize('weak', ['', '12345678', 'password'])
def test_reset_password_rejects_weak(admin_client, user, weak):
    resp = admin_client.post(f'{ADMIN_USERS_URL}{user.id}/reset-password/',
                             {'password': weak}, format='json')
    assert resp.status_code == 400


def test_reset_password_success(admin_client, user):
    new_password = 'Str0ngPass!2026'
    resp = admin_client.post(f'{ADMIN_USERS_URL}{user.id}/reset-password/',
                             {'password': new_password}, format='json')
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.check_password(new_password)
    assert authenticate(username='tester1', password=new_password) is not None


def test_non_admin_cannot_list_users(auth_client):
    assert auth_client.get(ADMIN_USERS_URL).status_code == 403
