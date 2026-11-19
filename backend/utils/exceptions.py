"""
自定义异常处理器 (可选, 配合 CustomJSONRenderer 已足够)
"""
from rest_framework.views import exception_handler
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        # 已经被 CustomJSONRenderer 包装
        return response
    # 未被 DRF 捕获的异常
    return {
        'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
        'msg': str(exc),
        'data': None,
    }
