"""
Projects app views - Project & TestModule CRUD
"""
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q

from .models import Project, TestModule, ProjectEnvironment
from .serializers import (
    ProjectSerializer, ProjectSimpleSerializer, TestModuleSerializer,
    ProjectEnvironmentSerializer,
)


def can_access_project(user, project):
    """判断用户是否有权访问项目"""
    if user.is_superuser or getattr(user, 'is_admin', False):
        return True
    return project.is_member(user)


class ProjectViewSet(viewsets.ModelViewSet):
    """项目 CRUD"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    search_fields = ['name', 'code']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # 普通用户只看自己参与的项目 (admin 看全部)
        if not (user.is_superuser or user.is_admin):
            qs = qs.filter(Q(members=user) | Q(creator=user))
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(Q(name__icontains=keyword) | Q(code__icontains=keyword))
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectSimpleSerializer
        return ProjectSerializer

    @action(detail=False, methods=['get'], url_path='my-projects')
    def my_projects(self, request):
        """获取当前用户参与的项目"""
        user = request.user
        qs = Project.objects.filter(Q(members=user) | Q(creator=user)).distinct()
        serializer = ProjectSimpleSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='modules')
    def get_modules(self, request, pk=None):
        """获取项目下的测试模块树"""
        project = self.get_object()
        modules = TestModule.objects.filter(project=project, parent__isnull=True).order_by('sort_order', 'id')
        serializer = TestModuleSerializer(modules, many=True, context={'request': request, 'build_tree': True})
        return Response(serializer.data)


class TestModuleViewSet(viewsets.ModelViewSet):
    """测试模块 CRUD (按项目隔离)"""
    queryset = TestModule.objects.select_related('project', 'parent')
    serializer_class = TestModuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not (user.is_superuser or getattr(user, 'is_admin', False)):
            qs = qs.filter(Q(project__members=user) | Q(project__creator=user)).distinct()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def list(self, request, *args, **kwargs):
        """树形结构列表"""
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({'msg': '必须提供 project_id'}, status=status.HTTP_400_BAD_REQUEST)
        modules = self.get_queryset().filter(
            parent__isnull=True
        ).order_by('sort_order', 'id')
        serializer = self.get_serializer(modules, many=True, context={'request': request, 'build_tree': True})
        return Response(serializer.data)


class ModuleTreeView(APIView):
    """项目模块树 (最多三级), 节点含 case_count (含子孙模块用例数)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        from apps.testcases.models import TestCase

        project = Project.objects.filter(pk=project_id).first()
        if not project:
            return Response({'msg': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not can_access_project(request.user, project):
            raise PermissionDenied('无权访问该项目')

        modules = list(
            TestModule.objects.filter(project=project).order_by('sort_order', 'id')
        )
        count_rows = (
            TestCase.objects.filter(project=project, module__isnull=False)
            .values('module_id')
            .annotate(c=Count('id'))
        )
        direct_counts = {row['module_id']: row['c'] for row in count_rows}

        nodes = {}
        for m in modules:
            nodes[m.id] = {
                'id': m.id,
                'parent': m.parent_id,
                'project': m.project_id,
                'name': m.name,
                'level': m.level,
                'sort_order': m.sort_order,
                'case_count': direct_counts.get(m.id, 0),
                'children': [],
            }

        roots = []
        for m in modules:
            node = nodes[m.id]
            if m.parent_id and m.parent_id in nodes:
                nodes[m.parent_id]['children'].append(node)
            else:
                roots.append(node)

        # 自底向上汇总用例数 (按层级从深到浅, 每个节点只向上累加一次)
        for m in sorted(modules, key=lambda x: x.level, reverse=True):
            if m.parent_id in nodes:
                nodes[m.parent_id]['case_count'] += nodes[m.id]['case_count']

        all_cases = TestCase.objects.filter(project=project)
        return Response({
            'tree': roots,
            'total_count': all_cases.count(),
            'unassigned_count': all_cases.filter(module__isnull=True).count(),
        })


class ProjectMemberListView(APIView):
    """项目成员列表 (不限角色, 供缺陷处理人多选)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = Project.objects.filter(pk=project_id).first()
        if not project:
            return Response({'msg': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not can_access_project(request.user, project):
            raise PermissionDenied('无权访问该项目')

        users = list(project.members.all().prefetch_related('roles'))
        if project.creator_id and all(u.pk != project.creator_id for u in users):
            users.append(project.creator)

        data = []
        for u in users:
            data.append({
                'id': u.id,
                'username': u.username,
                'real_name': u.real_name or u.username,
                'email': u.email or '',
                'avatar': u.avatar.url if u.avatar else '',
                'roles': [{'code': r.code, 'name': r.name} for r in u.roles.all()],
            })
        return Response(data)


class ProjectEnvironmentViewSet(viewsets.ModelViewSet):
    """项目环境 CRUD (按项目隔离)"""
    queryset = ProjectEnvironment.objects.select_related('project')
    serializer_class = ProjectEnvironmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not (user.is_superuser or getattr(user, 'is_admin', False)):
            qs = qs.filter(Q(project__members=user) | Q(project__creator=user)).distinct()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def list(self, request, *args, **kwargs):
        if not request.query_params.get('project_id'):
            return Response({'msg': '必须提供 project_id'}, status=status.HTTP_400_BAD_REQUEST)
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        if not can_access_project(self.request.user, project):
            raise PermissionDenied('无权在该项目下创建环境')
        serializer.save()

    def perform_update(self, serializer):
        project = serializer.instance.project
        if not can_access_project(self.request.user, project):
            raise PermissionDenied('无权操作该项目环境')
        serializer.save()
