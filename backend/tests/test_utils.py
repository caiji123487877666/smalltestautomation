"""数据库重试工具"""
import pytest
from django.db import IntegrityError

from utils.db import retry_on_integrity_error


def test_retry_succeeds_after_conflict(db):
    state = {'n': 0}

    def flaky():
        state['n'] += 1
        if state['n'] < 2:
            raise IntegrityError('duplicate key')
        return 'ok'

    assert retry_on_integrity_error(flaky) == 'ok'
    assert state['n'] == 2


def test_retry_raises_after_attempts(db):
    def always_conflict():
        raise IntegrityError('duplicate key')

    with pytest.raises(IntegrityError):
        retry_on_integrity_error(always_conflict, attempts=2)
