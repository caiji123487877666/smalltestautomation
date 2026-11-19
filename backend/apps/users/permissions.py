from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    """管理员全部权限, 普通用户只读"""

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_admin or request.user.is_superuser))


class IsAdminRole(BasePermission):
    """仅超级管理员或拥有 admin 角色的用户可访问 (含读操作)"""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and
                    (user.is_superuser or user.is_admin))


class HasRolePermission(BasePermission):
    """检查用户是否拥有指定 permission_code"""

    def __init__(self, permission_codes=None):
        self.permission_codes = permission_codes or []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 超级管理员 / admin 角色直接放行
        if request.user.is_superuser or request.user.is_admin:
            return True
        # 从 view 上取 permission_code
        code = getattr(view, 'required_permission', None)
        if code:
            self.permission_codes = [code]
        if not self.permission_codes:
            return True  # 无权限要求则放行
        user_perms = request.user.get_all_permissions()
        return any(c in user_perms for c in self.permission_codes)
