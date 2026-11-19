"""
TestCases 通用服务函数
"""
from apps.projects.models import TestModule
from .models import TestCase

CASE_NO_PREFIX = 'TC-'


def generate_case_no(project):
    """按项目递增生成用例编号 如 TC-0001"""
    max_num = 0
    existing = TestCase.objects.filter(
        project=project, case_no__startswith=CASE_NO_PREFIX
    ).values_list('case_no', flat=True)
    for no in existing:
        suffix = no[len(CASE_NO_PREFIX):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f'{CASE_NO_PREFIX}{max_num + 1:04d}'


def get_descendant_module_ids(module_id, max_depth=2):
    """获取模块及其子孙模块 ID (最多往下找 max_depth 层, 纯 ORM)"""
    ids = [module_id]
    frontier = [module_id]
    for _ in range(max_depth):
        children = list(
            TestModule.objects.filter(parent_id__in=frontier).values_list('id', flat=True)
        )
        children = [c for c in children if c not in ids]
        if not children:
            break
        ids.extend(children)
        frontier = children
    return ids
