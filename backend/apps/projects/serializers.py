"""
Projects app serializers
"""
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import Project, TestModule, ProjectEnvironment
from apps.users.serializers import UserSimpleSerializer


class ProjectSerializer(serializers.ModelSerializer):
    creator = UserSimpleSerializer(read_only=True)
    member_ids = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)
    member_count = serializers.SerializerMethodField()
    code = serializers.CharField(
        max_length=64,
        validators=[UniqueValidator(
            queryset=Project.objects.all(),
            message='该项目编码已存在, 请更换其他编码',
        )],
    )

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'code', 'description', 'status', 'notify_webhook',
            'creator', 'owner', 'member_ids', 'member_count',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'creator', 'created_at', 'updated_at')

    def get_member_count(self, obj):
        return obj.members.count()

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids', [])
        user = self.context['request'].user
        validated_data['creator'] = user
        project = Project.objects.create(**validated_data)
        # 创建者自动成为成员 + 负责人
        if not validated_data.get('owner'):
            project.owner = user
            project.save()
        project.members.add(user)
        if member_ids:
            project.members.add(*member_ids)
        # 默认环境, 方便缺陷记录"发现环境"
        if not project.environments.exists():
            ProjectEnvironment.objects.create(
                project=project, name='测试环境', is_default=True, sort_order=1)
        return project

    def update(self, instance, validated_data):
        member_ids = validated_data.pop('member_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if member_ids is not None:
            # 确保创建者始终在成员中
            ids = list(set(member_ids + [instance.creator_id]))
            instance.members.set(ids)
        return instance


class ProjectSimpleSerializer(serializers.ModelSerializer):
    """简要项目信息"""
    class Meta:
        model = Project
        fields = ('id', 'name', 'code', 'status')


class TestModuleSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    level = serializers.IntegerField(read_only=True)

    class Meta:
        model = TestModule
        fields = (
            'id', 'parent', 'project', 'project_name', 'name', 'level',
            'description', 'sort_order', 'children', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'level', 'created_at', 'updated_at')
        # 关闭自动 UniqueTogetherValidator, 改用 validate 中的中文提示
        validators = []

    def get_children(self, obj):
        # 列表时才构建 children, 详情时不嵌套
        if self.context.get('build_tree', False):
            all_children = list(TestModule.objects.filter(
                parent=obj, project=obj.project
            ).order_by('sort_order', 'id'))
            if all_children:
                child_serializer = TestModuleSerializer(
                    all_children, many=True, context={**self.context, 'build_tree': True})
                return child_serializer.data
            return []
        return None

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('模块名称不能为空')
        return name

    def _is_descendant(self, node):
        """判断 node 是否为当前模块的后代 (防止移动成环)"""
        while node is not None:
            if node.pk == self.instance.pk:
                return True
            node = node.parent
        return False

    def validate(self, attrs):
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        parent = attrs['parent'] if 'parent' in attrs else getattr(self.instance, 'parent', None)

        if parent is not None:
            if project and parent.project_id != project.id:
                raise serializers.ValidationError({'parent': '父模块不属于该项目'})
            if self.instance is not None and self._is_descendant(parent):
                raise serializers.ValidationError({'parent': '不能将模块移动到自己的子模块下'})
            if parent.level >= 3:
                raise serializers.ValidationError({'parent': '最多只支持创建三级模块'})
            level = parent.level + 1
        else:
            level = 1

        name = attrs.get('name') or getattr(self.instance, 'name', None)
        if project and name:
            siblings = TestModule.objects.filter(project=project, parent=parent, name=name)
            if self.instance is not None:
                siblings = siblings.exclude(pk=self.instance.pk)
            if siblings.exists():
                raise serializers.ValidationError({'name': '同一父级下已存在同名模块'})

        attrs['level'] = level
        return attrs


class ProjectEnvironmentSerializer(serializers.ModelSerializer):
    """项目环境"""

    class Meta:
        model = ProjectEnvironment
        fields = (
            'id', 'project', 'name', 'base_url', 'variables', 'description',
            'is_default', 'sort_order', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('环境名称不能为空')
        return name

    def validate_variables(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('环境变量必须是键值对象')
        cleaned = {}
        for key, val in value.items():
            name = str(key).strip()
            if not name:
                continue
            cleaned[name] = '' if val is None else str(val)
        return cleaned

    def validate(self, attrs):
        project = attrs.get('project') or getattr(self.instance, 'project', None)
        name = attrs.get('name') or getattr(self.instance, 'name', None)
        if project and name:
            qs = ProjectEnvironment.objects.filter(project=project, name=name)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'name': '同一项目下已存在同名环境'})
        if attrs.get('is_default') and project:
            ProjectEnvironment.objects.filter(project=project).exclude(
                pk=getattr(self.instance, 'pk', None)).update(is_default=False)
        return attrs
