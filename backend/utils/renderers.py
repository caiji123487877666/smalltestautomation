"""
统一返回格式渲染器: {"code": 200, "msg": "success", "data": ...}
"""
from rest_framework.renderers import JSONRenderer
from rest_framework import status


class CustomJSONRenderer(JSONRenderer):
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        status_code = response.status_code if response else status.HTTP_200_OK

        # 已经是标准格式的直接返回 (必须同时包含 code 与 msg, 避免与字段名 code 的校验错误混淆)
        if isinstance(data, dict) and 'code' in data and 'msg' in data:
            return super().render(data, accepted_media_type, renderer_context)

        # 错误响应
        if status_code >= 400:
            code = status_code
            msg = self._extract_error_msg(data)
            resp = {'code': code, 'msg': msg, 'data': None}
        else:
            # 正常响应
            code = 200
            msg = 'success'
            resp = {'code': code, 'msg': msg, 'data': data}

        return super().render(resp, accepted_media_type, renderer_context)

    @staticmethod
    def _extract_error_msg(data):
        if isinstance(data, dict):
            # DRF 验证错误
            if 'detail' in data:
                return str(data['detail'])
            # 字段级错误
            errors = []
            for k, v in data.items():
                if isinstance(v, list):
                    errors.append(f"{k}: {'; '.join(str(x) for x in v)}")
                else:
                    errors.append(f"{k}: {v}")
            return '; '.join(errors) if errors else 'error'
        return str(data) if data else 'error'
