"""权限边界: 无权限用户拒绝、孤儿缺陷隔离"""
from apps.bugs.models import Bug
from apps.users.models import MenuPermission, Role

BUGS_URL = '/api/bugs/'


def _grant(user, *codes):
    role, _ = Role.objects.get_or_create(code='tester', defaults={'name': '测试'})
    for code in codes:
        perm, _ = MenuPermission.objects.get_or_create(
            permission_code=code,
            defaults={'name': code, 'menu_type': 'button'},
        )
        role.permissions.add(perm)
    user.roles.add(role)


def test_user_without_permissions_cannot_access_bugs(auth_client, user, db):
    Role.objects.create(code='noop', name='无权限')
    user.roles.add(Role.objects.get(code='noop'))
    assert auth_client.get(BUGS_URL).status_code == 403


def test_admin_can_list_bugs(admin_client, db):
    assert admin_client.get(BUGS_URL).status_code == 200


def test_non_admin_cannot_create_orphan_bug(auth_client, user, db):
    _grant(user, 'bug:create')
    resp = auth_client.post(BUGS_URL, {'title': '孤儿缺陷'}, format='json')
    assert resp.status_code == 403


def test_orphan_bug_only_visible_to_creator(api_client, user, other_user, db):
    _grant(user, 'bug:view')
    _grant(other_user, 'bug:view')
    Bug.objects.create(bug_no='BUG-9001', title='公共缺陷', creator=user)

    api_client.force_authenticate(user=other_user)
    assert api_client.get(BUGS_URL).data['count'] == 0

    api_client.force_authenticate(user=user)
    assert api_client.get(BUGS_URL).data['count'] == 1
