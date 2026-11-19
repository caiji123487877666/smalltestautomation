"""测试用例模块: 编号生成、项目隔离、批量操作"""
import pytest

from apps.testcases.models import TestCase as CaseModel
from apps.testcases.services import generate_case_no

CASES_URL = '/api/testcases/cases/'


def _create_case(client, project, title='登录接口测试'):
    return client.post(
        CASES_URL,
        {
            'project': project.id,
            'title': title,
            'case_type': 'API',
            'steps': {'method': 'GET', 'url': '/api/health'},
        },
        format='json',
    )


def test_case_no_increments(project, db):
    first = CaseModel.objects.create(project=project, case_no=generate_case_no(project), title='A')
    second = CaseModel.objects.create(project=project, case_no=generate_case_no(project), title='B')
    assert first.case_no == 'TC-0001'
    assert second.case_no == 'TC-0002'


def test_case_no_is_per_project(project, user, db):
    from apps.projects.models import Project
    other = Project.objects.create(name='另一个项目', code='OTHER', creator=user)
    CaseModel.objects.create(project=project, case_no=generate_case_no(project), title='A')
    assert generate_case_no(other) == 'TC-0001'


def test_list_requires_project_id(auth_client):
    resp = auth_client.get(CASES_URL)
    assert resp.status_code == 400


def test_create_case_assigns_case_no(auth_client, project):
    resp = _create_case(auth_client, project)
    assert resp.status_code == 201
    data = resp.data
    assert data['case_no'].startswith('TC-')
    assert data['creator_name'] == 'tester1'


def test_create_case_forbidden_for_non_member(api_client, other_user, project):
    api_client.force_authenticate(user=other_user)
    resp = _create_case(api_client, project)
    assert resp.status_code == 403


def test_list_is_isolated_by_project_membership(api_client, other_user, project):
    CaseModel.objects.create(project=project, case_no='TC-0001', title='A')
    api_client.force_authenticate(user=other_user)
    resp = api_client.get(f'{CASES_URL}?project_id={project.id}')
    assert resp.status_code == 200
    assert resp.data['count'] == 0


def test_duplicate_case(auth_client, project):
    created = _create_case(auth_client, project).data
    resp = auth_client.post(f"{CASES_URL}{created['id']}/duplicate/")
    assert resp.status_code == 201
    assert resp.data['case_no'] != created['case_no']
    assert resp.data['title'].endswith('副本')


def test_batch_update_priority(auth_client, project):
    ids = [_create_case(auth_client, project, title=f'用例{i}').data['id'] for i in range(2)]
    resp = auth_client.post(
        f'{CASES_URL}batch-action/',
        {'ids': ids, 'action': 'update_priority', 'priority': 'P0'},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['affected'] == 2
    assert set(CaseModel.objects.filter(id__in=ids).values_list('priority', flat=True)) == {'P0'}


def test_batch_action_validates_required_field(auth_client):
    resp = auth_client.post(
        f'{CASES_URL}batch-action/',
        {'ids': [1], 'action': 'update_status'},
        format='json',
    )
    assert resp.status_code == 400


def test_web_case_gets_list_steps_by_default(auth_client, project):
    resp = auth_client.post(
        CASES_URL,
        {'project': project.id, 'title': 'WEB 用例', 'case_type': 'WEB'},
        format='json',
    )
    assert resp.status_code == 201
    assert resp.data['steps'] == []


def test_api_case_gets_object_steps_by_default(auth_client, project):
    resp = auth_client.post(
        CASES_URL,
        {'project': project.id, 'title': 'API 用例', 'case_type': 'API'},
        format='json',
    )
    assert resp.status_code == 201
    assert isinstance(resp.data['steps'], dict)
    assert resp.data['steps']['method'] == 'GET'


@pytest.mark.parametrize('case_type,steps', [
    ('API', {'method': 'INVALID', 'url': '/'}),
    ('WEB', [{'action': 'unknown'}])
])
def test_invalid_steps_rejected(auth_client, project, case_type, steps):
    resp = auth_client.post(
        CASES_URL,
        {'project': project.id, 'title': '非法步骤', 'case_type': case_type, 'steps': steps},
        format='json',
    )
    assert resp.status_code == 400
