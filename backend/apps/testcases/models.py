"""
TestCases app models
TestCase - 测试用例 (API / WEB 两种类型, steps 使用 JSONField)
"""
from django.db import models

from apps.users.models import User
from apps.projects.models import Project, TestModule


class TestCase(models.Model):
    """测试用例"""
    CASE_TYPE_CHOICES = (
        ('API', 'API'),
        ('WEB', 'WEB'),
    )
    PRIORITY_CHOICES = (
        ('P0', 'P0'),
        ('P1', 'P1'),
        ('P2', 'P2'),
        ('P3', 'P3'),
    )
    STATUS_CHOICES = (
        ('DRAFT', '草稿'),
        ('ACTIVE', '可用'),
        ('DEPRECATED', '已废弃'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                related_name='testcases', verbose_name='所属项目')
    module = models.ForeignKey(TestModule, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='testcases', verbose_name='所属模块')
    case_no = models.CharField(max_length=32, verbose_name='用例编号')
    title = models.CharField(max_length=255, verbose_name='用例标题')
    case_type = models.CharField(max_length=8, choices=CASE_TYPE_CHOICES,
                                 default='API', verbose_name='用例类型')
    priority = models.CharField(max_length=4, choices=PRIORITY_CHOICES,
                                default='P1', verbose_name='优先级')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                              default='DRAFT', verbose_name='状态')
    precondition = models.TextField(blank=True, default='', verbose_name='前置条件')
    tags = models.JSONField(default=list, blank=True, verbose_name='标签')
    # API 类型存对象; WEB 类型存步骤数组
    steps = models.JSONField(default=dict, blank=True, verbose_name='步骤/请求定义')
    creator = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='created_testcases', verbose_name='创建人')
    updater = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='updated_testcases', verbose_name='最后修改人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'test_case'
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-updated_at', '-id']
        unique_together = (('project', 'case_no'),)
        indexes = [
            models.Index(fields=['project', 'module']),
            models.Index(fields=['project', 'case_type']),
            models.Index(fields=['project', 'status']),
        ]

    def __str__(self):
        return f'{self.case_no} {self.title}'
