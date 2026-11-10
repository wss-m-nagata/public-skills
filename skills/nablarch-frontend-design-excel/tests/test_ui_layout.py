# 修正履歴
# 2026/11/10: 画像枠と要素ID注釈の検証を追加。
"""画像枠の行数、要素IDとExcel図形の保持を検証する。"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from openpyxl import Workbook, load_workbook
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def _load(name):
    """対象スクリプトをテスト用に読み込む。"""
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load('build_ui_component_design')
annotation = _load('annotate_ui_layout')


class LayoutTest(unittest.TestCase):
    """枠の寸法と注釈の入力を検証する。"""

    def test_frame_rows_default_and_maximum(self):
        """従来形式は14行、指定された最大値は30行とする。"""
        sheet = Workbook().active
        builder._fill_layout(sheet, {'layout': {'patterns': ['通常', {'title': '拡張', 'height_rows': 30}], 'elements': []}})
        frames = sorted((r for r in sheet.merged_cells.ranges if r.min_col == 3 and r.max_col == 35 and r.max_row > r.min_row), key=lambda x: x.min_row)
        self.assertEqual([frame.max_row - frame.min_row + 1 for frame in frames], [14, 30])
        self.assertEqual(sum(sheet.row_dimensions[row].height for row in range(frames[-1].min_row, frames[-1].max_row + 1)), 360)
        self.assertEqual([item.id for item in sheet.row_breaks.brk], [frames[-1].min_row - 2])

    def test_frame_rows_outside_range(self):
        """範囲外の行数や真偽値を受け付けない。"""
        for rows in (13, 31, True):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                builder._fill_layout(Workbook().active, {'layout': {'patterns': [{'title': '例', 'height_rows': rows}], 'elements': []}})

    def test_element_id_and_coordinates(self):
        """存在しないIDと画像外の矩形を拒否する。"""
        valid = {'id': 'E-01', 'x': 0.1, 'y': 0.2, 'width': 0.5, 'height': 0.4}
        annotation._validate_region(valid, {'E-01'})
        for value in ({**valid, 'id': 'E-02'}, {**valid, 'width': 0.95}):
            with self.assertRaises(ValueError):
                annotation._validate_region(value, {'E-01'})

    def test_project_metadata_and_classification_are_input_values(self):
        """異なるシステムと分類を定義から指定したとおりに出力する。"""
        with tempfile.TemporaryDirectory() as directory:
            for number, category in enumerate(('分類A', '別組織の分類')):
                content = builder._example()
                content['meta']['project'] = f'別プロジェクト{number}'
                content['overview']['category'] = category
                output = Path(directory) / f'{number}.xlsx'
                builder.build(output, content)
                workbook = load_workbook(output)
                self.assertEqual(workbook['変更履歴']['E1'].value, f'別プロジェクト{number}')
                self.assertEqual(workbook['1. 概要']['G8'].value, category)
                workbook.close()

    @unittest.skipUnless(os.environ.get('RUN_EXCEL_INTEGRATION') == '1', 'Excel連携は明示指定で実行する')
    def test_excel_shapes_survive_a_second_edit(self):
        """別枠への再編集で既存の画像・赤枠・IDが失われない。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = builder._example()
            content['layout']['patterns'] = ['通常', {'title': '拡張', 'height_rows': 30}]
            source, first, second = (root / name for name in ('source.xlsx', 'first.xlsx', 'second.xlsx'))
            builder.build(source, content)
            Image.new('RGB', (200, 60), 'white').save(root / 'sample.png')
            definition = root / 'layout.json'
            layout = {'frame_cell': 'C8', 'image': 'sample.png', 'elements': [{'id': 'E-01', 'x': 0.1, 'y': 0.1, 'width': 0.5, 'height': 0.5}]}
            definition.write_text(json.dumps({'layouts': [layout]}), encoding='utf-8')
            annotation.annotate(source, definition, first)
            definition.write_text(json.dumps({'layouts': [{**layout, 'frame_cell': 'C24'}]}), encoding='utf-8')
            annotation.annotate(first, definition, second)
            with zipfile.ZipFile(second) as archive:
                drawings = [ET.fromstring(archive.read(name)) for name in archive.namelist() if re_drawing(name)]
            namespace = '{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}'
            self.assertGreaterEqual(sum(len(root.findall(f'.//{namespace}pic')) for root in drawings), 2)
            self.assertGreaterEqual(sum(len(root.findall(f'.//{namespace}sp')) for root in drawings), 4)


def re_drawing(name):
    """DrawingMLの本体だけを選ぶ。"""
    return name.startswith('xl/drawings/drawing') and name.endswith('.xml')


if __name__ == '__main__':
    unittest.main()
