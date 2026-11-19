"""
Users app URL routing
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    login_view, register_view, CustomTokenRefreshView, LogoutView, get_my_info,
    UserAdminViewSet, RoleViewSet, MenuPermissionViewSet,
)

router = DefaultRouter()
router.register(r'admin/users', UserAdminViewSet, basename='admin-user')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'menu-permissions', MenuPermissionViewSet, basename='menu-permission')

urlpatterns = [
    # Auth
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    # 当前用户
    path('me/', get_my_info, name='my-info'),
    # Admin 管理
    path('', include(router.urls)),
]
