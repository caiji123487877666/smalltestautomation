"""pytest 公共夹具"""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.projects.models import Project

User = get_user_model()

PASSWORD = 'TestPass123'


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """限流使用默认缓存, 每个用例前清空, 避免互相污染"""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='tester1', password=PASSWORD)


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username='tester2', password=PASSWORD)


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username='admin', password='AdminPass123')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def project(db, user):
    return Project.objects.create(name='演示项目', code='DEMO', creator=user)


def unwrap(response):
    """兼容 DRF 包装后的响应, 取出业务 data"""
    data = response.data
    if isinstance(data, dict) and 'code' in data and 'data' in data:
        return data['data']
    return data


@pytest.fixture
def api_data():
    return unwrap
