"""
Bugs app models
Bug - 缺陷 (项目级数据隔离, 关联模块/用例/环境, 多处理人)
BugHistory - 缺陷流转历史
"""
from django.db import models

from apps.users.models import User
from apps.projects.models import Project, TestModule, ProjectEnvironment
from apps.testcases.models import TestCase


class Bug(models.Model):
    """缺陷"""
    SEVERITY_CHOICES = (
        ('BLOCKER', '阻塞'),
        ('ERROR', '严重'),
        ('NORMAL', '一般'),
        ('OTHER', '其他'),
    )
    PRIORITY_CHOICES = (
        ('P0', 'P0'),
        ('P1', 'P1'),
        ('P2', 'P2'),
        ('P3', 'P3'),
    )
    REPRODUCIBILITY_CHOICES = (
        ('ALWAYS', '必现'),
        ('OFTEN', '大概率'),
        ('SOMETIMES', '偶现'),
    )
    STATUS_CHOICES = (
        ('NEW', '新建'),
        ('ASSIGNED', '已指派'),
        ('IN_PROGRESS', '处理中'),
        ('RESOLVED', '已解决/待验证'),
        ('CLOSED', '已关闭'),
        ('REOPENED', '重新打开'),
    )
    RESOLUTION_CHOICES = (
        ('FIXED', '已修复'),
        ('BY_DESIGN', '设计如此'),
        ('CANNOT_REPRODUCE', '无法复现'),
        ('DUPLICATE', '重复缺陷'),
        ('WONT_FIX', '暂不修复'),
    )

    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='bugs', verbose_name='所属项目')
    module = models.ForeignKey(TestModule, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='bugs', verbose_name='所属模块')
    testcase = models.ForeignKey(TestCase, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='bugs', verbose_name='关联用例')
    environment = models.ForeignKey(ProjectEnvironment, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='bugs',
                                    verbose_name='发现环境')
    bug_no = models.CharField(max_length=32, unique=True, verbose_name='缺陷编号')
    title = models.CharField(max_length=255, verbose_name='缺陷标题')
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES,
                                default='NORMAL', verbose_name='严重程度')
    priority = models.CharField(max_length=4, choices=PRIORITY_CHOICES,
                                default='P1', verbose_name='优先级')
    reproducibility = models.CharField(max_length=16, choices=REPRODUCIBILITY_CHOICES,
                                       default='ALWAYS', verbose_name='复现概率')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default='NEW', verbose_name='状态')
    resolution = models.CharField(max_length=32, choices=RESOLUTION_CHOICES,
                                  blank=True, default='', verbose_name='解决结果')
    description = models.TextField(blank=True, default='', verbose_name='详细描述')
    attachments = models.JSONField(default=list, blank=True, verbose_name='附件截图')
    creator = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='created_bugs', verbose_name='创建人')
    assignees = models.ManyToManyField(User, related_name='assigned_bugs',
                                       blank=True, verbose_name='处理人')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='解决时间')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='关闭时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'test_bug'
        verbose_name = '缺陷'
        verbose_name_plural = '缺陷'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'severity']),
            models.Index(fields=['project', 'testcase']),
            models.Index(fields=['project', 'module']),
        ]

    def __str__(self):
        return f'{self.bug_no} {self.title}'


class BugHistory(models.Model):
    """缺陷流转历史"""
    ACTION_CHOICES = (
        ('CREATE', '创建'),
        ('UPDATE', '更新'),
        ('TRANSITION', '状态流转'),
        ('COMMENT', '评论'),
        ('ASSIGN', '指派'),
    )

    bug = models.ForeignKey(Bug, on_delete=models.CASCADE,
                            related_name='histories', verbose_name='缺陷')
    operator = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='bug_histories', verbose_name='操作人')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, verbose_name='操作类型')
    action_label = models.CharField(max_length=128, blank=True, default='', verbose_name='动作名称')
    from_status = models.CharField(max_length=16, blank=True, default='', verbose_name='原状态')
    to_status = models.CharField(max_length=16, blank=True, default='', verbose_name='新状态')
    resolution = models.CharField(max_length=32, blank=True, default='', verbose_name='解决结果')
    comment = models.TextField(blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'test_bug_history'
        verbose_name = '缺陷历史'
        verbose_name_plural = '缺陷历史'
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=['bug', 'created_at']),
        ]

    def __str__(self):
        return f'{self.bug_id}-{self.action}'
