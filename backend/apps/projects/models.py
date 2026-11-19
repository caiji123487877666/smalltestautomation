"""
Projects app models
Project - 项目 (含成员关联, 项目级数据隔离)
TestModule - 测试模块 (树形结构)
"""
from django.db import models
from apps.users.models import User


class Project(models.Model):
    """项目"""
    STATUS_CHOICES = (
        ('active', '进行中'),
        ('paused', '暂停'),
        ('archived', '已归档'),
    )

    name = models.CharField(max_length=128, verbose_name='项目名称')
    code = models.CharField(max_length=64, unique=True, verbose_name='项目编码')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    # 创建者
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_projects',
                                verbose_name='创建者')
    # 项目成员 (M2M)
    members = models.ManyToManyField(User, related_name='projects', blank=True, verbose_name='项目成员')
    # 项目负责人
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='owned_projects', verbose_name='负责人')
    # 消息通知预留 (飞书/钉钉群机器人 Webhook)
    notify_webhook = models.URLField(max_length=500, blank=True, null=True, verbose_name='通知 Webhook')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'test_project'
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}({self.code})'

    def is_member(self, user):
        return self.members.filter(pk=user.pk).exists() or self.creator_id == user.pk


class TestModule(models.Model):
    """测试模块 (树形结构, 最多三级)"""
    LEVEL_CHOICES = (
        (1, '一级模块'),
        (2, '二级模块'),
        (3, '三级模块'),
    )

    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,
                               related_name='children', verbose_name='父模块')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_modules',
                                verbose_name='所属项目')
    name = models.CharField(max_length=128, verbose_name='模块名称')
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name='描述')
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES, default=1, verbose_name='层级')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'test_module'
        verbose_name = '测试模块'
        verbose_name_plural = '测试模块'
        ordering = ['sort_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'parent', 'name'],
                name='uniq_module_name_per_parent',
            ),
        ]
        indexes = [
            models.Index(fields=['project', 'parent']),
        ]

    def __str__(self):
        return self.name

    def get_full_path(self):
        """返回模块完整路径, 如 用户中心 / 登录管理 / 短信验证码"""
        parts = []
        node = self
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return ' / '.join(reversed(parts))


class ProjectEnvironment(models.Model):
    """项目环境 (测试/预发/生产等), 供缺陷记录发现环境"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                related_name='environments', verbose_name='所属项目')
    name = models.CharField(max_length=64, verbose_name='环境名称')
    base_url = models.URLField(max_length=500, blank=True, default='', verbose_name='访问地址')
    # 环境变量字典, 供接口调试 {{变量名}} 替换
    variables = models.JSONField(default=dict, blank=True, verbose_name='环境变量')
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name='描述')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'project_environment'
        verbose_name = '项目环境'
        verbose_name_plural = '项目环境'
        ordering = ['sort_order', 'id']
        unique_together = (('project', 'name'),)

    def __str__(self):
        return f'{self.project_id}-{self.name}'

