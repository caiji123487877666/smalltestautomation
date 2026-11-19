"""
TestCases app serializers
"""
from rest_framework import serializers

from apps.projects.models import Project, TestModule
from .models import TestCase

API_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')
WEB_ACTIONS = ('goto', 'click', 'fill', 'select', 'wait', 'assert_text', 'assert_url')
BODY_TYPES = ('none', 'json', 'form')


def normalize_api_steps(steps):
    """规范化 API 类型 steps 结构"""
    if not isinstance(steps, dict):
        steps = {}
    return {
        'method': (steps.get('method') or 'GET').upper(),
        'url': steps.get('url') or '',
        'headers': steps.get('headers') or [],
        'params': steps.get('params') or [],
        'body_type': steps.get('body_type') or 'none',
        'body': steps.get('body') or '',
        'assertions': steps.get('assertions') or [],
    }


def normalize_web_steps(steps):
    """规范化 WEB 类型 steps 结构, 补齐 ai_healed_selector"""
    if not isinstance(steps, list):
        return []
    result = []
    for item in steps:
        if not isinstance(item, dict):
            continue
        result.append({
            'action': item.get('action') or 'click',
            'selector': item.get('selector') or '',
            'value': item.get('value') or '',
            'element_desc': item.get('element_desc') or '',
            'ai_healed_selector': item.get('ai_healed_selector') or '',
        })
    return result


class ModulePathMixin(serializers.Serializer):
    """补充模块完整路径字段"""
    module_path = serializers.SerializerMethodField()

    def get_module_path(self, obj):
        module = getattr(obj, 'module', None)
        if module is None:
            return '未规划模块'
        parts = []
        node = module
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return ' / '.join(reversed(parts))


class OpenBugCountMixin(serializers.Serializer):
    """未关闭缺陷数 (依赖 queryset annotate, 避免 N+1)"""
    open_bug_count = serializers.SerializerMethodField()

    def get_open_bug_count(self, obj):
        value = getattr(obj, 'open_bug_count', None)
        if value is None:
            return obj.bugs.exclude(status='CLOSED').count()
        return value


class TestCaseListSerializer(OpenBugCountMixin, ModulePathMixin, serializers.ModelSerializer):
    """列表序列化 (不含 steps, 减小体积)"""
    module_name = serializers.CharField(source='module.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True)
    creator_name = serializers.CharField(source='creator.username', read_only=True, default='')
    updater_name = serializers.CharField(source='updater.username', read_only=True, default='')

    class Meta:
        model = TestCase
        fields = (
            'id', 'project', 'project_name', 'module', 'module_name', 'module_path',
            'case_no', 'title', 'case_type', 'priority', 'status', 'tags',
            'precondition', 'open_bug_count', 'creator_name', 'updater_name',
            'created_at', 'updated_at',
        )


class TestCaseSerializer(OpenBugCountMixin, ModulePathMixin, serializers.ModelSerializer):
    """详情/创建/更新序列化 (含 steps)"""
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        error_messages={
            'does_not_exist': '所属项目不存在或已被删除，请刷新页面后重新选择项目',
            'incorrect_type': '项目 ID 格式不正确',
            'required': '请先选择所属项目',
            'null': '请先选择所属项目',
        },
    )
    module_name = serializers.CharField(source='module.name', read_only=True, default='')
    project_name = serializers.CharField(source='project.name', read_only=True)
    creator_name = serializers.CharField(source='creator.username', read_only=True, default='')
    updater_name = serializers.CharField(source='updater.username', read_only=True, default='')

    class Meta:
        model = TestCase
        fields = (
            'id', 'project', 'project_name', 'module', 'module_name', 'module_path',
            'case_no', 'title', 'case_type', 'priority', 'status',
            'precondition', 'tags', 'steps', 'open_bug_count',
            'creator_name', 'updater_name', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'case_no', 'created_at', 'updated_at')
        extra_kwargs = {
            'title': {'required': True},
        }

    def validate_tags(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('标签必须是数组')
        return [str(t).strip() for t in value if str(t).strip()]

    def validate_steps(self, value):
        case_type = self.initial_data.get('case_type', getattr(self.instance, 'case_type', 'API'))
        if case_type == 'WEB':
            if not isinstance(value, list):
                raise serializers.ValidationError('WEB 用例 steps 必须是步骤数组')
            for idx, item in enumerate(value, start=1):
                if not isinstance(item, dict):
                    raise serializers.ValidationError(f'第 {idx} 步格式错误')
                if item.get('action') not in WEB_ACTIONS:
                    raise serializers.ValidationError(
                        f'第 {idx} 步 action 必须是 {",".join(WEB_ACTIONS)}')
            return normalize_web_steps(value)
        # API
        if not isinstance(value, dict):
            raise serializers.ValidationError('API 用例 steps 必须是对象')
        method = (value.get('method') or 'GET').upper()
        if method not in API_METHODS:
            raise serializers.ValidationError(f'method 必须是 {",".join(API_METHODS)}')
        body_type = value.get('body_type') or 'none'
        if body_type not in BODY_TYPES:
            raise serializers.ValidationError('body_type 必须是 none/json/form')
        return normalize_api_steps(value)

    def validate(self, attrs):
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        module = attrs.get('module', getattr(self.instance, 'module', None))
        if module and project and module.project_id != project.id:
            raise serializers.ValidationError({'module': '模块不属于所选项目'})
        return attrs


class TestCaseBatchActionSerializer(serializers.Serializer):
    """批量操作入参"""
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    action = serializers.ChoiceField(choices=(
        'delete', 'update_priority', 'update_status', 'move_module',
    ))
    priority = serializers.ChoiceField(choices=('P0', 'P1', 'P2', 'P3'), required=False)
    status = serializers.ChoiceField(choices=('DRAFT', 'ACTIVE', 'DEPRECATED'), required=False)
    module_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        action = attrs['action']
        if action == 'update_priority' and not attrs.get('priority'):
            raise serializers.ValidationError('批量修改优先级需提供 priority')
        if action == 'update_status' and not attrs.get('status'):
            raise serializers.ValidationError('批量修改状态需提供 status')
        if action == 'move_module' and 'module_id' not in attrs:
            raise serializers.ValidationError('批量移动需提供 module_id')
        return attrs
