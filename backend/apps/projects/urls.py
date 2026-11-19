"""
Projects app URL routing
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProjectViewSet, TestModuleViewSet, ModuleTreeView,
    ProjectMemberListView, ProjectEnvironmentViewSet,
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'modules', TestModuleViewSet, basename='module')
router.register(r'environments', ProjectEnvironmentViewSet, basename='environment')

urlpatterns = [
    # 项目模块树: /api/projects/{project_id}/modules/tree/
    path('<int:project_id>/modules/tree/', ModuleTreeView.as_view(), name='module-tree'),
    # 项目成员: /api/projects/{project_id}/members/
    path('<int:project_id>/members/', ProjectMemberListView.as_view(), name='project-members'),
    path('', include(router.urls)),
]
