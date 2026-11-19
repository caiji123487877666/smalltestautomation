# MySQL 驱动兼容: 项目依赖 PyMySQL, 需注册为 MySQLdb 供 Django 使用
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:  # 未安装 PyMySQL 时忽略, 开发环境使用 SQLite 不受影响
    pass

# Celery app initialization
from .celery import app as celery_app  # noqa: E402

__all__ = ('celery_app',)
