"""
Bugs app views
"""
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.projects.models import Project
from apps.testcases.services import get_descendant_module_ids
from apps.users.models import User
from .models import Bug, BugHistory
from .serializers import (
    BugListSerializer, BugSerializer, BugHistorySerializer,
    BugTransitionSerializer, project_member_ids,
)
from .services import generate_bug_no

ALLOWED_TRANSITIONS = {
    'NEW': {'ASSIGNED', 'IN_PROGRESS', 'CLOSED'},
    'ASSIGNED': {'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'},
    'IN_PROGRESS': {'ASSIGNED', 'RESOLVED', 'CLOSED'},
    'RESOLVED': {'CLOSED', 'REOPENED'},
    'CLOSED': {'REOPENED'},
    'REOPENED': {'ASSIGNED', 'IN_PROGRESS', 'RESOLVED'},
}

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def accessible_projects(user):
    """当前用户可见的项目 (admin 全部)"""
    if user.is_superuser or getattr(user, 'is_admin', False):
        return Project.objects.all()
    return Project.objects.filter(Q(members=user) | Q(creator=user)).distinct()


class BugPermission(BasePermission):
    """缺陷操作权限码校验"""
    ACTION_PERMISSIONS = {
        'list': 'bug:view',
        'retrieve': 'bug:view',
        'histories': 'bug:view',
        'create': 'bug:create',
        'update': 'bug:edit',
        'partial_update': 'bug:edit',
        'destroy': 'bug:delete',
        'transition': 'bug:transition',
        'comment': 'bug:edit',
        'upload_image': 'bug:create',
        'available_assignees': 'bug:view',
    }

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or getattr(user, 'is_admin', False):
            return True
        code = self.ACTION_PERMISSIONS.get(getattr(view, 'action', None))
        if not code:
            return True
        perms = user.get_all_permissions()
        if not perms:  # 空集合代表拥有全部权限
            return True
        return code in perms


class BugViewSet(viewsets.ModelViewSet):
    """缺陷 CRUD / 筛选 / 状态流转 / 截图上传"""
    queryset = Bug.objects.select_related(
        'project', 'module__parent__parent', 'testcase', 'environment', 'creator',
    ).prefetch_related('assignees')
    permission_classes = [IsAuthenticated, BugPermission]

    def get_serializer_class(self):
        if self.action == 'list':
            return BugListSerializer
        if self.action == 'histories':
            return BugHistorySerializer
        return BugSerializer

    # ---------- 查询与数据隔离 ----------
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not (user.is_superuser or getattr(user, 'is_admin', False)):
            qs = qs.filter(
                Q(project__in=accessible_projects(user)) | Q(project__isnull=True)
            ).distinct()

        params = self.request.query_params
        project_param = params.get('project_id')
        if project_param == 'unassigned':
            qs = qs.filter(project__isnull=True)
        elif project_param:
            qs = qs.filter(project_id=project_param)

        status_value = params.get('status')
        if status_value:
            if status_value == 'OPEN':
                qs = qs.exclude(status='CLOSED')
            else:
                qs = qs.filter(status=status_value)
        if params.get('unclosed') in ('1', 'true', 'True'):
            qs = qs.exclude(status='CLOSED')

        for field in ('severity', 'priority', 'reproducibility'):
            value = params.get(field)
            if value:
                qs = qs.filter(**{field: value})

        assignee_id = params.get('assignee_id')
        if assignee_id:
            qs = qs.filter(assignees__id=assignee_id)
        creator_id = params.get('creator_id')
        if creator_id:
            qs = qs.filter(creator_id=creator_id)
        environment_id = params.get('environment_id')
        if environment_id:
            qs = qs.filter(environment_id=environment_id)
        testcase_id = params.get('testcase_id')
        if testcase_id:
            qs = qs.filter(testcase_id=testcase_id)

        module_id = params.get('module_id')
        if module_id and module_id != 'all':
            if module_id == 'unassigned':
                qs = qs.filter(module__isnull=True)
            elif str(module_id).isdigit():
                qs = qs.filter(module_id__in=get_descendant_module_ids(int(module_id)))

        keyword = params.get('keyword')
        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(bug_no__icontains=keyword))

        return qs.distinct()

    def list(self, request, *args, **kwargs):
        # 不传 project_id 时返回当前用户有权限的全部缺陷 (含未关联项目的公共缺陷)
        return super().list(request, *args, **kwargs)

    # ---------- 创建 / 更新 ----------
    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        user = self.request.user
        if project and not accessible_projects(user).filter(pk=project.pk).exists():
            raise PermissionDenied('无权在该项目下创建缺陷')
        serializer.save(bug_no=generate_bug_no(), creator=user)
        bug = serializer.instance
        BugHistory.objects.create(
            bug=bug, operator=user, action='CREATE', to_status=bug.status,
            comment='创建缺陷',
        )

    def perform_update(self, serializer):
        user = self.request.user
        project = serializer.instance.project
        if project and not accessible_projects(user).filter(pk=project.pk).exists():
            raise PermissionDenied('无权操作该缺陷')
        serializer.save()
        BugHistory.objects.create(
            bug=serializer.instance, operator=user, action='UPDATE',
            from_status=serializer.instance.status, to_status=serializer.instance.status,
            comment='更新缺陷信息',
        )

    # ---------- 状态流转 ----------
    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        bug = self.get_object()
        serializer = BugTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_status = data['target_status']
        current_status = bug.status

        allowed = ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise ValidationError({'target_status': '当前状态不允许直接流转至目标状态'})

        comment = (data.get('comment') or '').strip()
        resolution = data.get('resolution') or ''
        assignee_ids = data.get('assignee_ids')

        # 指派 / 转派: 必须至少一名处理人
        if target_status == 'ASSIGNED' and not assignee_ids:
            raise ValidationError({'assignee_ids': '指派处理人时必须选择至少一名处理人'})

        # 处理人更新 (不限角色, 需为项目成员或系统激活用户)
        assignee_names = []
        if 'assignee_ids' in data:
            valid_ids = project_member_ids(bug.project)
            invalid = [uid for uid in data['assignee_ids'] if uid not in valid_ids]
            if invalid:
                raise ValidationError({'assignee_ids': '处理人必须是有效用户或当前项目成员'})
            assignees = list(User.objects.filter(pk__in=data['assignee_ids']))
            bug.assignees.set(assignees)
            assignee_names = [u.real_name or u.username for u in assignees]

        # 强制字段校验
        if target_status == 'CLOSED' and not resolution:
            raise ValidationError({'resolution': '关闭缺陷时必须选择解决结果'})
        if target_status == 'REOPENED' and not comment:
            raise ValidationError({'comment': '重新打开必须填写打回/重开原因'})

        now = timezone.now()
        from_status = current_status
        bug.status = target_status
        history_resolution = ''

        if target_status == 'ASSIGNED':
            verb = '转派给' if current_status == 'ASSIGNED' else '指派给'
            action_label = f'{verb} [{", ".join(assignee_names)}]'
            bug.resolved_at = None
            bug.closed_at = None
        elif target_status == 'IN_PROGRESS':
            action_label = '开始处理'
            bug.resolved_at = None
            bug.closed_at = None
        elif target_status == 'RESOLVED':
            action_label = '标记已解决'
            bug.resolved_at = now
        elif target_status == 'CLOSED':
            action_label = (
                f'验证通过关闭（解决结果：{dict(Bug.RESOLUTION_CHOICES)[resolution]}）'
                if current_status == 'RESOLVED'
                else f'直接关闭（解决结果：{dict(Bug.RESOLUTION_CHOICES)[resolution]}）'
            )
            bug.resolution = resolution
            bug.closed_at = now
            history_resolution = resolution
        else:  # REOPENED
            action_label = '打回重新打开' if current_status == 'RESOLVED' else '重新打开'
            bug.resolution = ''
            bug.resolved_at = None
            bug.closed_at = None
        bug.save()

        history = BugHistory.objects.create(
            bug=bug, operator=request.user, action='TRANSITION',
            action_label=action_label,
            from_status=from_status, to_status=target_status,
            resolution=history_resolution, comment=comment,
        )

        # 触发通知钩子
        from apps.notifications.signals import bug_status_changed
        bug_status_changed.send(
            sender=Bug, bug=bug, operator=request.user,
            from_status=from_status, to_status=target_status,
            comment=history.comment,
        )

        return Response(BugSerializer(bug, context={'request': request}).data)

    # ---------- 评论 ----------
    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        bug = self.get_object()
        text = (request.data.get('comment') or '').strip()
        if not text:
            raise ValidationError({'comment': '评论内容不能为空'})
        history = BugHistory.objects.create(
            bug=bug, operator=request.user, action='COMMENT',
            action_label='发表评论', from_status=bug.status, to_status=bug.status,
            comment=text,
        )
        return Response(
            BugHistorySerializer(history).data, status=status.HTTP_201_CREATED)

    # ---------- 历史记录 ----------
    @action(detail=True, methods=['get'])
    def histories(self, request, pk=None):
        bug = self.get_object()
        qs = bug.histories.select_related('operator').all()
        return Response(BugHistorySerializer(qs, many=True).data)

    # ---------- 可选处理人 ----------
    @action(detail=False, methods=['get'], url_path='available-assignees')
    def available_assignees(self, request):
        """
        传 project_id: 返回该项目成员;
        不传: 返回系统内全部激活用户 (用于未关联项目的 Bug)
        """
        project_id = request.query_params.get('project_id')
        if project_id and project_id != 'unassigned':
            project = Project.objects.filter(pk=project_id).first()
            if not project:
                return Response({'msg': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
            if not accessible_projects(request.user).filter(pk=project.pk).exists():
                raise PermissionDenied('无权访问该项目')
            users = list(project.members.all().prefetch_related('roles'))
            if project.creator_id and all(u.pk != project.creator_id for u in users):
                users.append(project.creator)
        else:
            users = list(User.objects.filter(is_active=True).prefetch_related('roles'))

        data = [{
            'id': u.id,
            'username': u.username,
            'real_name': u.real_name or u.username,
            'email': u.email or '',
            'roles': [{'code': r.code, 'name': r.name} for r in u.roles.all()],
        } for u in users]
        return Response(data)

    # ---------- 截图上传 ----------
    @action(detail=False, methods=['post'], url_path='upload-image',
            parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'msg': '请选择图片文件'}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in IMAGE_EXTS:
            return Response({'msg': '仅支持 png/jpg/jpeg/gif/webp/bmp 图片'},
                            status=status.HTTP_400_BAD_REQUEST)
        if upload.size > MAX_IMAGE_SIZE:
            return Response({'msg': '图片不能超过 5MB'}, status=status.HTTP_400_BAD_REQUEST)

        filename = f'bugs/{uuid.uuid4().hex}{ext}'
        saved_name = default_storage.save(filename, upload)
        url = f'{settings.MEDIA_URL}{saved_name}'
        return Response({'url': url, 'name': upload.name}, status=status.HTTP_201_CREATED)
