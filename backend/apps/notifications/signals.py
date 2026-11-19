"""
消息通知信号与预留钩子

当前版本: 仅记录日志, 便于后续无缝接入邮件 / 飞书 / 钉钉异步推送。
后续接入方式:
  - send_bug_notification 内部改为 Celery 任务 (send_mail / requests.post webhook)
  - 用户 feishu_id / dingtalk_id 已预留, 项目 notify_webhook 已预留
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

logger = logging.getLogger('notifications')

# 缺陷状态流转自定义信号
bug_status_changed = Signal()


def send_bug_notification(bug, event_type, operator=None, **extra):
    """
    缺陷通知统一钩子 (预留)

    :param bug: Bug 实例
    :param event_type: created / status_changed
    :param operator: 操作人 User
    :param extra: 额外上下文 (from_status / to_status / comment 等)
    """
    try:
        operator_name = (
            getattr(operator, 'username', None)
            or getattr(getattr(bug, 'creator', None), 'username', None)
            or '-'
        )
        project = getattr(bug, 'project', None)
        logger.info(
            '[BUG NOTIFY] event=%s bug=%s title=%s project=%s operator=%s extra=%s',
            event_type, bug.bug_no, bug.title,
            getattr(project, 'name', '-'), operator_name, extra or {},
        )
        webhook = getattr(project, 'notify_webhook', None)
        if webhook:
            # TODO: 后续接入飞书/钉钉群机器人异步推送
            logger.info('[BUG NOTIFY] webhook configured, pending integration: %s', webhook)
    except Exception:  # 通知失败不影响业务主流程
        logger.exception('[BUG NOTIFY] failed to send notification')


@receiver(post_save, sender='bugs.Bug')
def on_bug_created(sender, instance, created, **kwargs):
    """缺陷创建事件"""
    if created:
        send_bug_notification(instance, 'created', instance.creator)


@receiver(bug_status_changed)
def on_bug_status_changed(sender, bug=None, operator=None, from_status='',
                          to_status='', comment='', **kwargs):
    """缺陷状态流转事件"""
    if bug is None:
        return
    send_bug_notification(
        bug, 'status_changed', operator,
        from_status=from_status, to_status=to_status, comment=comment,
    )
