from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = '消息通知'

    def ready(self):
        # 注册缺陷相关信号
        from . import signals  # noqa: F401
