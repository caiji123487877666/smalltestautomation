"""
Users & RBAC models
User - 扩展用户
Role - 角色
MenuPermission - 菜单与按钮权限树
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    """自定义 User Manager，支持手机号/邮箱登录"""

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError('用户名不能为空')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('超级用户必须 is_superuser=True')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('超级用户必须 is_staff=True')
        return self._create_user(username, password, **extra_fields)


class User(AbstractUser):
    """扩展用户模型"""
    GENDER_CHOICES = (
        ('male', '男'),
        ('female', '女'),
        ('unknown', '未知'),
    )

    # 覆盖继承字段，允许为空（注册时可能不需要全部填）
    email = models.EmailField(max_length=128, blank=True, null=True, verbose_name='邮箱')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unknown', verbose_name='性别')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    department = models.CharField(max_length=64, blank=True, null=True, verbose_name='部门')
    real_name = models.CharField(max_length=64, blank=True, null=True, verbose_name='真实姓名')
    # 消息通知预留 (飞书 / 钉钉)
    feishu_id = models.CharField(max_length=64, blank=True, null=True, verbose_name='飞书 OpenID')
    dingtalk_id = models.CharField(max_length=64, blank=True, null=True, verbose_name='钉钉 UserID')

    # 多对多: 用户可以拥有多个角色
    roles = models.ManyToManyField('Role', related_name='users', blank=True, verbose_name='角色')

    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    objects = UserManager()

    class Meta:
        db_table = 'auth_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-date_joined']

    @property
    def is_admin(self):
        """判断是否拥有 admin 角色"""
        return self.roles.filter(code='admin').exists() or self.is_superuser

    def get_all_permissions(self):
        """
        获取用户所有权限码（去重）。

        注意: 超级管理员 / admin 角色返回空集, 调用方必须先判断管理员身份,
        不能把空集当作"拥有全部权限", 否则无任何权限配置的普通用户会被误放行。
        """
        if self.is_superuser or self.is_admin:
            return set()
        perms = set()
        for role in self.roles.all():
            for p in role.permissions.filter(permission_code__isnull=False).exclude(permission_code=''):
                perms.add(p.permission_code)
        return perms

    def get_menus(self):
        """获取用户可见的菜单树（只返回菜单类型，不含按钮）"""
        if self.is_superuser or self.is_admin:
            return MenuPermission.objects.filter(menu_type__in=['menu', 'directory']).order_by('sort_order')
        return MenuPermission.objects.filter(
            roles__in=self.roles.all(),
            menu_type__in=['menu', 'directory']
        ).distinct().order_by('sort_order')


class Role(models.Model):
    """角色"""
    code = models.CharField(max_length=32, unique=True, verbose_name='角色编码')
    name = models.CharField(max_length=64, verbose_name='角色名称')
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name='描述')
    is_builtin = models.BooleanField(default=False, verbose_name='内置角色(不可删除)')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    # 多对多: 角色拥有的菜单/按钮权限
    permissions = models.ManyToManyField('MenuPermission', related_name='roles', blank=True, verbose_name='权限')

    class Meta:
        db_table = 'rbac_role'
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.name}({self.code})'


class MenuPermission(models.Model):
    """
    菜单与按钮权限树
    menu_type: directory=目录, menu=菜单, button=按钮
    """
    MENU_TYPE_CHOICES = (
        ('directory', '目录'),
        ('menu', '菜单'),
        ('button', '按钮'),
    )

    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,
                               related_name='children', verbose_name='父级')
    name = models.CharField(max_length=64, verbose_name='名称')
    menu_type = models.CharField(max_length=16, choices=MENU_TYPE_CHOICES, verbose_name='类型')
    # 前端路由 path (菜单/目录用)
    path = models.CharField(max_length=255, blank=True, null=True, verbose_name='路由路径')
    # 前端组件 component (菜单用, 如 views/system/user/index)
    component = models.CharField(max_length=255, blank=True, null=True, verbose_name='组件路径')
    # 前端图标
    icon = models.CharField(max_length=64, blank=True, null=True, verbose_name='图标')
    # 权限码 (按钮必须有, 菜单可选)
    permission_code = models.CharField(max_length=64, blank=True, null=True, verbose_name='权限码')
    # 是否可见 (前端侧边栏)
    is_visible = models.BooleanField(default=True, verbose_name='是否可见')
    # 是否缓存 (前端 keep-alive)
    is_cached = models.BooleanField(default=False, verbose_name='是否缓存')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'rbac_menu_permission'
        verbose_name = '菜单/权限'
        verbose_name_plural = '菜单/权限'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['parent']),
            models.Index(fields=['permission_code']),
        ]

    def __str__(self):
        return f'[{self.get_menu_type_display()}] {self.name}'
