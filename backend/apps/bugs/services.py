"""Bugs 通用服务函数"""
from .models import Bug

BUG_NO_PREFIX = 'BUG-'


def generate_bug_no():
    """全局递增生成缺陷编号, 如 BUG-0001 (不依赖项目)"""
    max_num = 0
    existing = Bug.objects.filter(
        bug_no__startswith=BUG_NO_PREFIX
    ).values_list('bug_no', flat=True)
    for no in existing:
        suffix = no[len(BUG_NO_PREFIX):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f'{BUG_NO_PREFIX}{max_num + 1:04d}'
