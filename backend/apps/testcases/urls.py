"""
TestCases app URL routing
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TestCaseViewSet
from .debug_views import DebugApiView, ParseCurlView

router = DefaultRouter()
router.register(r'cases', TestCaseViewSet, basename='testcase')

urlpatterns = [
    # 单接口在线调试
    path('debug-api/', DebugApiView.as_view(), name='debug-api'),
    # cURL 导入解析
    path('parse-curl/', ParseCurlView.as_view(), name='parse-curl'),
    path('', include(router.urls)),
]
