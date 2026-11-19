"""
Users app views - Auth, User, Role, MenuPermission CRUD
"""
from rest_framework import viewsets, generics, status, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView
from django.db.models import Q

from .models import User, Role, MenuPermission
from .serializers import (
    LoginSerializer, RegisterSerializer, UserMeSerializer,
    UserAdminSerializer, RoleSerializer, MenuPermissionSerializer,
)
from .permissions import IsAdminRole


# ============== Auth (公开) ==============
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """JWT 登录"""
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.validated_data)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """用户注册 (默认分配 tester 角色)"""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response({
        'id': user.id,
        'username': user.username,
        'msg': '注册成功, 请登录',
    }, status=status.HTTP_201_CREATED)


class CustomTokenRefreshView(TokenRefreshView):
    """刷新 JWT"""
    pass


# ============== 当前用户 ==============
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_info(request):
    """获取当前用户完整信息(角色+权限码+菜单树)"""
    serializer = UserMeSerializer(request.user)
    return Response(serializer.data)


# ============== User Admin CRUD ==============
class UserAdminViewSet(viewsets.ModelViewSet):
    """管理员对用户的 CRUD (仅 admin/超级管理员可访问)"""
    queryset = User.objects.all()
    serializer_class = UserAdminSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    search_fields = ['username', 'real_name', 'email']
    ordering_fields = ['date_joined', 'username']

    def get_queryset(self):
        qs = super().get_queryset()
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(username__icontains=keyword) |
                Q(real_name__icontains=keyword) |
                Q(email__icontains=keyword)
            )
        role_id = self.request.query_params.get('role_id')
        if role_id:
            qs = qs.filter(roles__id=role_id)
        return qs.distinct()

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """重置密码"""
        user = self.get_object()
        new_pwd = request.data.get('password', 'default123')
        user.set_password(new_pwd)
        user.save()
        return Response({'msg': f'密码已重置为: {new_pwd}'})

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        """启用/禁用用户"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({'is_active': user.is_active})


# ============== Role CRUD ==============
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    pagination_class = None
    search_fields = ['code', 'name']

    def get_queryset(self):
        qs = super().get_queryset()
        keyword = self.request.query_params.get('keyword')
        if keyword:
            qs = qs.filter(Q(code__icontains=keyword) | Q(name__icontains=keyword))
        return qs

    def destroy(self, request, *args, **kwargs):
        role = self.get_object()
        if role.is_builtin:
            return Response({'msg': '内置角色不可删除'}, status=status.HTTP_400_BAD_REQUEST)
        # 解除用户绑定
        role.users.clear()
        role.permissions.clear()
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='permissions')
    def get_permission_ids(self, request, pk=None):
        """获取角色已分配的权限ID列表"""
        role = self.get_object()
        return Response(
            list(role.permissions.values_list('id', flat=True))
        )


# ============== MenuPermission CRUD ==============
class MenuPermissionViewSet(viewsets.ModelViewSet):
    """菜单/按钮权限管理"""
    queryset = MenuPermission.objects.all()
    serializer_class = MenuPermissionSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def list(self, request, *args, **kwargs):
        """返回树形结构"""
        all_items = list(self.get_queryset().order_by('sort_order', 'id'))
        # 顶层
        roots = [m for m in all_items if m.parent_id is None]
        tree = self._build_tree(roots, all_items)
        return Response(tree)

    def _build_tree(self, parents, all_items):
        result = []
        for m in parents:
            serializer = self.get_serializer(m)
            node = serializer.data
            children = [c for c in all_items if c.parent_id == m.id]
            if children:
                node['children'] = self._build_tree(children, all_items)
            else:
                node['children'] = []
            result.append(node)
        return result
