"""
单接口在线调试 / cURL 导入 接口
"""
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import Project, ProjectEnvironment
from .api_debugger import execute_debug, parse_curl, HTTP_METHODS
from .views import accessible_projects


class DebugApiSerializer(serializers.Serializer):
    """即时调试入参"""
    project_id = serializers.IntegerField(required=False, allow_null=True)
    environment_id = serializers.IntegerField(required=False, allow_null=True)
    method = serializers.CharField(required=False, default='GET')
    url = serializers.CharField(required=False, allow_blank=True, default='')
    headers = serializers.JSONField(required=False, default=list)
    params = serializers.JSONField(required=False, default=list)
    body_type = serializers.ChoiceField(
        choices=['none', 'json', 'form-data', 'urlencoded'],
        required=False, default='none')
    body = serializers.JSONField(required=False, allow_null=True)
    assertions = serializers.JSONField(required=False, default=list)
    extract_rules = serializers.JSONField(required=False, default=list)
    sync_variables = serializers.BooleanField(required=False, default=False)

    def validate_method(self, value):
        method = (value or 'GET').upper()
        if method not in HTTP_METHODS:
            raise serializers.ValidationError(f'不支持的请求方法: {value}')
        return method

    def validate(self, attrs):
        for key in ('headers', 'params', 'assertions', 'extract_rules'):
            value = attrs.get(key)
            if value is not None and not isinstance(value, (list, dict)):
                raise serializers.ValidationError({key: '必须是数组或对象'})
        for key in ('headers', 'params', 'assertions', 'extract_rules'):
            if attrs.get(key) is None:
                attrs[key] = []
        return attrs


class ParseCurlSerializer(serializers.Serializer):
    curl = serializers.CharField()


class DebugApiView(APIView):
    """单接口即时调试: 变量替换 + 真实请求 + 断言 + 变量提取"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DebugApiSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = None
        if data.get('project_id'):
            project = Project.objects.filter(pk=data['project_id']).first()
            if not project:
                raise ValidationError({'project_id': '项目不存在'})
            if not accessible_projects(request.user).filter(pk=project.pk).exists():
                raise PermissionDenied('无权访问该项目')

        environment = None
        if data.get('environment_id'):
            environment = ProjectEnvironment.objects.select_related('project').filter(
                pk=data['environment_id']).first()
            if not environment:
                raise ValidationError({'environment_id': '环境不存在'})
            if project and environment.project_id != project.pk:
                raise ValidationError({'environment_id': '环境不属于所选项目'})
            if not accessible_projects(request.user).filter(pk=environment.project_id).exists():
                raise PermissionDenied('无权访问该环境')

        result = execute_debug(data, environment)
        return Response(result)


class ParseCurlView(APIView):
    """解析浏览器复制的 cURL (bash) 命令"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ParseCurlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            parsed = parse_curl(serializer.validated_data['curl'])
        except ValueError as exc:
            raise ValidationError({'curl': str(exc)})
        return Response(parsed, status=status.HTTP_200_OK)
