"""
Users app serializers
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Role, MenuPermission


# ============== Auth ==============
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('用户名或密码错误')
        if not user.is_active:
            raise serializers.ValidationError('账号已被禁用')
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserMeSerializer(user).data,
        }


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, max_length=32)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'real_name')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        # 默认分配 tester 角色
        try:
            tester_role = Role.objects.get(code='tester')
            user.roles.add(tester_role)
        except Role.DoesNotExist:
            pass
        return user


# ============== User ==============
class UserSimpleSerializer(serializers.ModelSerializer):
    """简要用户信息"""

    class Meta:
        model = User
        fields = ('id', 'username', 'real_name', 'email', 'avatar')


class UserMeSerializer(serializers.ModelSerializer):
    """当前用户完整信息(含角色、权限码、菜单树)"""
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    menus = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'real_name', 'email', 'phone', 'department',
            'gender', 'avatar', 'is_active', 'is_staff', 'is_superuser',
            'roles', 'permissions', 'menus', 'date_joined',
        )

    def get_roles(self, obj):
        return [{'code': r.code, 'name': r.name} for r in obj.roles.all()]

    def get_permissions(self, obj):
        perms = obj.get_all_permissions()
        # 空表示全部权限
        if not perms and (obj.is_superuser or obj.is_admin):
            return 'all'
        return sorted(perms)

    def get_menus(self, obj):
        """递归构建菜单树"""
        menus = list(obj.get_menus())
        root_menus = [m for m in menus if m.parent_id is None]
        return self._build_tree(root_menus, menus)

    def _build_tree(self, parents, all_menus):
        result = []
        for m in parents:
            node = {
                'id': m.id,
                'name': m.name,
                'type': m.menu_type,
                'path': m.path or '',
                'component': m.component or '',
                'icon': m.icon or '',
                'permission_code': m.permission_code or '',
                'sort_order': m.sort_order,
                'is_visible': m.is_visible,
            }
            children = [c for c in all_menus if c.parent_id == m.id]
            if children:
                node['children'] = self._build_tree(children, all_menus)
            else:
                node['children'] = []
            result.append(node)
        return result


class RoleBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'code', 'name')


class UserAdminSerializer(serializers.ModelSerializer):
    """管理员 CRUD 用户"""
    role_ids = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)
    roles = RoleBriefSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'password', 'real_name', 'email', 'phone',
            'gender', 'department', 'avatar', 'is_active', 'is_staff',
            'role_ids', 'roles', 'date_joined',
        )
        extra_kwargs = {
            'password': {'write_only': True, 'required': False, 'allow_blank': True},
        }
        read_only_fields = ('id', 'date_joined')

    def create(self, validated_data):
        role_ids = validated_data.pop('role_ids', [])
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_password('default123')  # 默认密码
        user.save()
        if role_ids:
            user.roles.set(role_ids)
        return user

    def update(self, instance, validated_data):
        role_ids = validated_data.pop('role_ids', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if role_ids is not None:
            instance.roles.set(role_ids)
        return instance


# ============== Role ==============
class RoleSerializer(serializers.ModelSerializer):
    permission_ids = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)

    class Meta:
        model = Role
        fields = ('id', 'code', 'name', 'description', 'is_builtin', 'sort_order',
                  'permission_ids', 'created_at', 'updated_at')
        read_only_fields = ('id', 'is_builtin', 'created_at', 'updated_at')

    def create(self, validated_data):
        perm_ids = validated_data.pop('permission_ids', [])
        role = Role.objects.create(**validated_data)
        if perm_ids:
            role.permissions.set(perm_ids)
        return role

    def update(self, instance, validated_data):
        perm_ids = validated_data.pop('permission_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if perm_ids is not None:
            instance.permissions.set(perm_ids)
        return instance


# ============== MenuPermission ==============
class MenuPermissionSerializer(serializers.ModelSerializer):
    """带 children 的递归菜单序列化"""

    class Meta:
        model = MenuPermission
        fields = (
            'id', 'parent', 'name', 'menu_type', 'path', 'component',
            'icon', 'permission_code', 'is_visible', 'is_cached',
            'sort_order', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class MenuTreeSerializer(serializers.Serializer):
    """仅返回树结构(前端动态菜单用)"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()
    path = serializers.CharField(allow_blank=True)
    component = serializers.CharField(allow_blank=True)
    icon = serializers.CharField(allow_blank=True)
    permission_code = serializers.CharField(allow_blank=True)
    children = serializers.ListField(required=False)
