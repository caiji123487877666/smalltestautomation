default_app_config = ''

# Celery app initialization
from .celery import app as celery_app

__all__ = ('celery_app',)
