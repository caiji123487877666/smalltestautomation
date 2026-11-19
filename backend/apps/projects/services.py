"""项目级数据可见范围 (统一权限口径)"""
from django.db.models import Q

from .models import Project


def accessible_projects(user):
    """当前用户可见的项目 (admin 全部, 其他按成员/创建者)"""
    if user.is_superuser or getattr(user, 'is_admin', False):
        return Project.objects.all()
    return Project.objects.filter(Q(members=user) | Q(creator=user)).distinct()
