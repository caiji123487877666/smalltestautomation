"""
Bugs app serializers
"""
from rest_framework import serializers

from apps.users.models import User
from apps.users.serializers import UserSimpleSerializer
from .models import Bug, BugHistory


def module_full_path(module):
    if module is None:
        return '未规划模块'
    parts = []
    node = module
    while node is not None:
        parts.append(node.name)
        node = node.parent
    return ' / '.join(reversed(parts))


def project_member_ids(project):
    """项目成员 ID 集合 (含创建者), 用于处理人校验"""
    if project is None:
        return set(User.objects.filter(is_active=True).values_list('pk', flat=True))
    ids = set(project.members.values_list('pk', flat=True))
    if project.creator_id:
        ids.add(project.creator_id)
    return ids


class BugHistorySerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.username', read_only=True, default='')
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    from_status_display = serializers.SerializerMethodField()
    to_status_display = serializers.SerializerMethodField()
    resolution_display = serializers.CharField(source='get_resolution_display', read_only=True)

    class Meta:
        model = BugHistory
        fields = (
            'id', 'bug', 'operator', 'operator_name', 'action', 'action_display',
            'action_label', 'from_status', 'from_status_display',
            'to_status', 'to_status_display', 'resolution', 'resolution_display',
            'comment', 'created_at',
        )

    def get_from_status_display(self, obj):
        return dict(Bug.STATUS_CHOICES).get(obj.from_status, obj.from_status)

    def get_to_status_display(self, obj):
        return dict(Bug.STATUS_CHOICES).get(obj.to_status, obj.to_status)


class BugBaseMixin(serializers.Serializer):
    """公共只读字段"""
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    module_path = serializers.SerializerMethodField()
    environment_name = serializers.CharField(source='environment.name', read_only=True, default='')
    testcase_no = serializers.CharField(source='testcase.case_no', read_only=True, default='')
    testcase_title = serializers.CharField(source='testcase.title', read_only=True, default='')
    creator_name = serializers.CharField(source='creator.username', read_only=True, default='')
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    reproducibility_display = serializers.CharField(
        source='get_reproducibility_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    resolution_display = serializers.CharField(source='get_resolution_display', read_only=True)

    def get_module_path(self, obj):
        return module_full_path(obj.module)


class BugListSerializer(BugBaseMixin, serializers.ModelSerializer):
    assignees = UserSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Bug
        fields = (
            'id', 'project', 'project_name', 'module', 'module_path',
            'testcase', 'testcase_no', 'testcase_title',
            'environment', 'environment_name', 'bug_no', 'title',
            'severity', 'severity_display', 'priority', 'priority_display',
            'reproducibility', 'reproducibility_display',
            'status', 'status_display', 'resolution', 'resolution_display',
            'creator', 'creator_name', 'assignees',
            'resolved_at', 'closed_at', 'created_at', 'updated_at',
        )


class BugSerializer(BugBaseMixin, serializers.ModelSerializer):
    """详情 / 创建 / 更新"""
    assignees = UserSimpleSerializer(many=True, read_only=True)
    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True)

    class Meta:
        model = Bug
        fields = (
            'id', 'project', 'project_name', 'module', 'module_path',
            'testcase', 'testcase_no', 'testcase_title',
            'environment', 'environment_name', 'bug_no', 'title',
            'severity', 'severity_display', 'priority', 'priority_display',
            'reproducibility', 'reproducibility_display',
            'status', 'status_display', 'resolution', 'resolution_display',
            'description', 'attachments',
            'creator', 'creator_name', 'assignees', 'assignee_ids',
            'resolved_at', 'closed_at', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'bug_no', 'creator', 'status', 'resolution',
            'resolved_at', 'closed_at', 'created_at', 'updated_at',
        )
        extra_kwargs = {
            'project': {'required': False, 'allow_null': True},
            'title': {'required': True},
        }

    # ---------- 校验 ----------
    def validate_title(self, value):
        title = (value or '').strip()
        if not title:
            raise serializers.ValidationError('缺陷标题不能为空')
        return title

    def validate_attachments(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('附件必须是 URL 数组')
        return [str(v) for v in value if str(v).strip()]

    def validate(self, attrs):
        # 未选择项目时, 若关联了模块/用例/环境, 自动回填项目
        if attrs.get('project') is None:
            for key in ('testcase', 'module', 'environment'):
                obj = attrs.get(key)
                if obj is not None:
                    attrs['project'] = obj.project
                    break

        project = attrs.get('project', getattr(self.instance, 'project', None))

        module = attrs.get('module', getattr(self.instance, 'module', None))
        testcase = attrs.get('testcase', getattr(self.instance, 'testcase', None))
        environment = attrs.get('environment', getattr(self.instance, 'environment', None))

        if project is not None:
            if module and module.project_id != project.pk:
                raise serializers.ValidationError({'module': '模块不属于所选项目'})
            if testcase and testcase.project_id != project.pk:
                raise serializers.ValidationError({'testcase': '关联用例不属于所选项目'})
            if environment and environment.project_id != project.pk:
                raise serializers.ValidationError({'environment': '环境不属于所选项目'})

        if 'assignee_ids' in attrs:
            valid_ids = project_member_ids(project)
            invalid = [uid for uid in attrs['assignee_ids'] if uid not in valid_ids]
            if invalid:
                raise serializers.ValidationError(
                    {'assignee_ids': '处理人必须是有效用户或当前项目成员'})
        return attrs

    # ---------- 写入 ----------
    def create(self, validated_data):
        assignee_ids = validated_data.pop('assignee_ids', [])
        bug = Bug.objects.create(**validated_data)
        if assignee_ids:
            bug.assignees.set(User.objects.filter(pk__in=assignee_ids))
        return bug

    def update(self, instance, validated_data):
        assignee_ids = validated_data.pop('assignee_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # 未关联项目时, 模块/用例/环境必须一并清空
        if instance.project_id is None:
            for key in ('module', 'testcase', 'environment'):
                if key not in validated_data:
                    setattr(instance, key, None)
        instance.save()
        if assignee_ids is not None:
            instance.assignees.set(User.objects.filter(pk__in=assignee_ids))
        return instance


class BugTransitionSerializer(serializers.Serializer):
    """状态流转入参"""
    target_status = serializers.ChoiceField(choices=[c[0] for c in Bug.STATUS_CHOICES])
    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False)
    resolution = serializers.ChoiceField(
        choices=[c[0] for c in Bug.RESOLUTION_CHOICES], required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True, default='')
