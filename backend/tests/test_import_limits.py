"""导入上限: 文件大小与行数"""
import io

from openpyxl import Workbook

from apps.testcases.excel_io import (
    MAX_IMPORT_FILE_SIZE,
    MAX_IMPORT_ROWS,
    import_cases_from_excel,
    import_cases_from_swagger,
)


class FakeUpload:
    def __init__(self, size, content=b'{}'):
        self.size = size
        self._content = content

    def read(self, *args, **kwargs):
        return self._content


def test_excel_file_too_large(project, user):
    result = import_cases_from_excel(FakeUpload(MAX_IMPORT_FILE_SIZE + 1), project, user)
    assert result['success'] == 0
    assert '10MB' in result['errors'][0]['msg']


def test_swagger_file_too_large(project, user):
    result = import_cases_from_swagger(FakeUpload(MAX_IMPORT_FILE_SIZE + 1), project, user)
    assert result['success'] == 0
    assert '10MB' in result['errors'][0]['msg']


def test_excel_row_limit(project, user, db):
    wb = Workbook()
    ws = wb.active
    for row in range(MAX_IMPORT_ROWS + 2):
        ws.cell(row=row + 1, column=2, value=f'用例{row + 1}')
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    result = import_cases_from_excel(buf, project, user)
    assert result['success'] == 0
    assert '最多导入' in result['errors'][0]['msg']
