"""数据库并发重试工具"""
from django.db import IntegrityError, transaction


def retry_on_integrity_error(func, attempts=3):
    """执行 func, 遇到唯一约束冲突时重试 (每次尝试使用独立事务)"""
    for attempt in range(attempts):
        try:
            with transaction.atomic():
                return func()
        except IntegrityError:
            if attempt == attempts - 1:
                raise
