"""
TestCases app views
"""
import json
from datetime import datetime
from urllib.parse import quote

from django.db.models import CharField, Count, Q
from django.db.models.functions import Cast
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.projects.models import Project, TestModule
from .models import TestCase
from .serializers import (
    TestCaseListSerializer, TestCaseSerializer, TestCaseBatchActionSerializer,
)
from .services import generate_case_no, get_descendant_module_ids
from . import excel_io

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def accessible_projects(user):
    """当前用户可见的项目 (admin 全部)"""
    if user.is_superuser or getattr(user, 'is_admin', False):
        return Project.objects.all()
    return Project.objects.filter(Q(members=user) | Q(creator=user)).distinct()


class TestCaseViewSet(viewsets.ModelViewSet):
    """测试用例 CRUD / 复制 / 批量操作 / 导入导出"""
    queryset = TestCase.objects.select_related(
        'project', 'module__parent__parent', 'creator', 'updater'
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return TestCaseListSerializer
        return TestCaseSerializer

    def list(self, request, *args, **kwargs):
        """用例列表必须指定 project_id, 避免跨项目数据泄露"""
        if not request.query_params.get('project_id'):
            raise ValidationError({'project_id': '必须提供 project_id'})
        return super().list(request, *args, **kwargs)

    # ---------- 查询与数据隔离 ----------
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # 关联缺陷统计: 列表/详情 annotate, 避免 N+1
        if self.action in ('list', 'retrieve'):
            qs = qs.annotate(
                open_bug_count=Count('bugs', filter=~Q(bugs__status='CLOSED'))
            )

        # 项目级数据隔离
        if not (user.is_superuser or getattr(user, 'is_admin', False)):
            qs = qs.filter(Q(project__members=user) | Q(project__creator=user)).distinct()

        params = self.request.query_params
        project_id = params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)

        # 模块 (含子模块递归)
        module_id = params.get('module_id')
        if module_id and module_id != 'all':
            if module_id == 'unassigned':
                qs = qs.filter(module__isnull=True)
            elif str(module_id).isdigit():
                qs = qs.filter(module_id__in=get_descendant_module_ids(int(module_id)))

        # 关键字: 标题/编号
        keyword = params.get('keyword')
        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(case_no__icontains=keyword))

        # 枚举过滤
        for field in ('case_type', 'priority', 'status'):
            value = params.get(field)
            if value:
                qs = qs.filter(**{field: value})

        # 标签过滤 (JSON 转文本后模糊匹配, 兼容 SQLite / MySQL)
        tag = params.get('tag')
        if tag:
            escaped = json.dumps(tag, ensure_ascii=True)[1:-1]
            qs = qs.annotate(
                _tags_text=Cast('tags', output_field=CharField())
            ).filter(Q(_tags_text__icontains=tag) | Q(_tags_text__icontains=escaped))

        return qs

    # ---------- 创建 / 更新 ----------
    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        user = self.request.user
        if not accessible_projects(user).filter(pk=project.pk).exists():
            raise PermissionDenied('无权在该项目下创建用例')
        serializer.save(
            case_no=generate_case_no(project),
            creator=user,
            updater=user,
        )

    def perform_update(self, serializer):
        project = serializer.validated_data.get('project', serializer.instance.project)
        user = self.request.user
        if not accessible_projects(user).filter(pk=project.pk).exists():
            raise PermissionDenied('无权操作该项目下的用例')
        serializer.save(updater=user)

    # ---------- 复制用例 ----------
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        case = self.get_object()
        new_title = f'{case.title} - 副本'
        clone = TestCase.objects.create(
            project=case.project,
            module=case.module,
            case_no=generate_case_no(case.project),
            title=new_title[:255],
            case_type=case.case_type,
            priority=case.priority,
            status=case.status,
            precondition=case.precondition,
            tags=list(case.tags or []),
            steps=case.steps,
            creator=request.user,
            updater=request.user,
        )
        return Response(TestCaseSerializer(clone).data, status=status.HTTP_201_CREATED)

    # ---------- 批量操作 ----------
    @action(detail=False, methods=['post'], url_path='batch-action')
    def batch_action(self, request):
        serializer = TestCaseBatchActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = self.get_queryset().filter(id__in=data['ids'])
        action_name = data['action']

        if action_name == 'delete':
            affected, _ = qs.delete()
            return Response({'affected': affected})

        if action_name == 'update_priority':
            affected = qs.update(priority=data['priority'], updater=request.user,
                                 updated_at=timezone.now())
            return Response({'affected': affected})

        if action_name == 'update_status':
            affected = qs.update(status=data['status'], updater=request.user,
                                 updated_at=timezone.now())
            return Response({'affected': affected})

        # move_module
        module_id = data.get('module_id')
        module = None
        if module_id is not None:
            module = TestModule.objects.filter(pk=module_id).first()
            if not module:
                raise ValidationError({'module_id': '目标模块不存在'})
        if module and qs.exclude(project_id=module.project_id).exists():
            raise ValidationError({'module_id': '所选用例与目标模块不属于同一项目'})
        affected = qs.update(module=module, updater=request.user, updated_at=timezone.now())
        return Response({'affected': affected})

    # ---------- Excel 模板 ----------
    @action(detail=False, methods=['get'], url_path='import-template')
    def import_template(self, request):
        buf = excel_io.build_import_template()
        response = HttpResponse(buf.read(), content_type=XLSX_CONTENT_TYPE)
        filename = quote('测试用例导入模板.xlsx')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}"
        return response

    # ---------- Excel 导入 ----------
    @action(detail=False, methods=['post'], url_path='import-excel')
    def import_excel(self, request):
        upload = request.FILES.get('file')
        project_id = request.data.get('project_id')
        if not upload:
            return Response({'msg': '请上传 Excel 文件'}, status=status.HTTP_400_BAD_REQUEST)
        if not project_id:
            return Response({'msg': '缺少 project_id'}, status=status.HTTP_400_BAD_REQUEST)
        project = Project.objects.filter(pk=project_id).first()
        if not project:
            return Response({'msg': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not accessible_projects(request.user).filter(pk=project.pk).exists():
            raise PermissionDenied('无权在该项目下导入用例')

        result = excel_io.import_cases_from_excel(upload, project, request.user)
        return Response(result)

    # ---------- Excel 导出 ----------
    @action(detail=False, methods=['get'], url_path='export-excel')
    def export_excel(self, request):
        ids = request.query_params.get('ids')
        if ids:
            id_list = [int(i) for i in ids.split(',') if i.strip().isdigit()]
            qs = self.get_queryset().filter(id__in=id_list)
        else:
            qs = self.get_queryset()
        cases = list(qs.order_by('case_no'))

        buf = excel_io.export_cases_to_workbook(cases)
        response = HttpResponse(buf.read(), content_type=XLSX_CONTENT_TYPE)
        filename = quote(f'测试用例_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}"
        return response

    # ---------- Swagger 导入 ----------
    @action(detail=False, methods=['post'], url_path='import-swagger')
    def import_swagger(self, request):
        upload = request.FILES.get('file')
        project_id = request.data.get('project_id')
        if not upload:
            return Response({'msg': '请上传 Swagger/OpenAPI JSON 文件'}, status=status.HTTP_400_BAD_REQUEST)
        if not project_id:
            return Response({'msg': '缺少 project_id'}, status=status.HTTP_400_BAD_REQUEST)
        project = Project.objects.filter(pk=project_id).first()
        if not project:
            return Response({'msg': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
        if not accessible_projects(request.user).filter(pk=project.pk).exists():
            raise PermissionDenied('无权在该项目下导入用例')

        result = excel_io.import_cases_from_swagger(upload, project, request.user)
        return Response(result)
