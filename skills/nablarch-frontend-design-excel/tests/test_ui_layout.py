# 修正履歴
# 2026/11/10: 画像枠と要素ID注釈の検証を追加。
"""画像枠の行数、要素IDとExcel図形の保持を検証する。"""

import importlib.util
import io
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
extract_images = _load('extract_ui_layout_images')
batch_annotation = _load('batch_annotate_ui_layout')


class LayoutTest(unittest.TestCase):
    """枠の寸法と注釈の入力を検証する。"""

    def test_multiple_objects_and_function_details(self):
        """複数オブジェクトと公開関数の詳細を別シートに出力する。"""
        content = builder._example()
        content['objects'] = [
            {'name': '項目', 'prop': 'items', 'fields': [['term', 'string', '必須', '―', '項目名']]},
            {'name': '設定', 'prop': 'options', 'fields': [['color', 'string', '任意', '―', '色']]},
        ]
        content['public_functions'] = [['validate()', 'なし', 'boolean', '入力を検査する。']]
        content['related_functions'] = [['notify(text)', 'string', 'void', '通知を表示する。']]
        content['details'] = [{'title': 'M-01　validate()', 'values': {'概要': '入力を検査する。'}}]
        content['meta']['version'] = '第1.1版'
        content['meta']['history'] = [
            {'version': '第1.0版', 'date': '2026-11-10', 'kind': '新規', 'sections': '-', 'description': '新規作成', 'author': '担当者'},
            {'version': '第1.1版', 'date': '2026-11-11', 'kind': '変更', 'sections': '1. 概要\n4. 入力属性\n5. オブジェクト定義', 'description': '定義を追加。', 'author': '担当者'},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'design.xlsx'
            builder.build(output, content)
            workbook = load_workbook(output)
            self.assertEqual(workbook.sheetnames[-4:], ['4. 入力属性', '5. オブジェクト定義', '6. 関数定義', '7. 関数詳細'])
            self.assertEqual(workbook.active.title, '表紙')
            self.assertEqual(workbook['表紙'].sheet_view.selection[0].activeCell, 'A1')
            for sheet in workbook:
                self.assertFalse(sheet.sheet_view.showGridLines)
            self.assertEqual(workbook['7. 関数詳細'].sheet_format.defaultColWidth, workbook['6. 関数定義'].sheet_format.defaultColWidth)
            def values(sheet):
                return [cell.value for row in workbook[sheet] for cell in row if cell.value is not None]
            objects = values('5. オブジェクト定義')
            self.assertTrue(any('items' in str(value) for value in objects))
            self.assertTrue(any('options' in str(value) for value in objects))
            self.assertIn('validate()', values('6. 関数定義'))
            self.assertIn('notify(text)', values('6. 関数定義'))
            self.assertIn('2. 利用する関連関数', values('6. 関数定義'))
            self.assertIn('M-01　validate()', values('7. 関数詳細'))
            self.assertEqual(workbook['変更履歴']['B9'].value, '第1.1版')
            self.assertGreaterEqual(workbook['変更履歴'].row_dimensions[9].height, 45)
            workbook.close()

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

    def test_layout_with_no_repeated_annotations(self):
        """先の例で説明した要素は、後の画像で赤枠を省略できる。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (200, 60), 'white').save(root / 'sample.png')
            result = annotation._validate_definition({'layouts': [{'frame_cell': 'C8', 'image': 'sample.png', 'elements': []}]}, root)
            self.assertEqual(result[0][4], [])

    def test_extract_embedded_images_by_frame(self):
        """枠に対応する埋め込み画像を取り出し、JSONと一緒に出力する。"""
        from openpyxl.drawing.image import Image as ExcelImage
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image_path = root / 'example.png'
            Image.new('RGB', (20, 10), 'white').save(image_path)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = '2. 画面レイアウト'
            sheet.merge_cells('C8:AI21')
            sheet.add_image(ExcelImage(io.BytesIO(image_path.read_bytes())), 'C8')
            workbook_path = root / 'source.xlsx'
            workbook.save(workbook_path)
            workbook.close()
            definition = root / 'layout.json'
            definition.write_text(json.dumps({'layouts': [{'frame_cell': 'C8', 'image': 'example.png', 'elements': []}]}), encoding='utf-8')
            destination = root / 'extracted'
            extract_images.extract(workbook_path, definition, destination)
            self.assertEqual((destination / 'example.png').read_bytes(), image_path.read_bytes())
            self.assertTrue((destination / '画像配置.json').exists())
            with self.assertRaises(ValueError):
                extract_images.extract(workbook_path, definition, destination)

    def test_batch_rejects_duplicate_outputs_before_excel(self):
        """一括処理は重複した出力をExcel起動前に拒否する。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source.xlsx').touch()
            (root / 'layout.json').touch()
            job = {'source': 'source.xlsx', 'definition': 'layout.json', 'output': 'output.xlsx'}
            manifest = root / 'jobs.json'
            manifest.write_text(json.dumps({'jobs': [job, job]}), encoding='utf-8')
            with self.assertRaises(ValueError):
                batch_annotation._jobs(manifest)

    @unittest.skipUnless(os.environ.get('RUN_EXCEL_INTEGRATION') == '1', 'Excel連携は明示指定で実行する')
    def test_batch_two_workbooks_preserves_images(self):
        """一回のExcel起動で複数の作業版に画像と要素IDを配置する。"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (200, 60), 'white').save(root / 'sample.png')
            jobs = []
            for index in range(2):
                source = root / f'source{index}.xlsx'
                content = builder._example()
                content['layout']['patterns'] = ['通常']
                builder.build(source, content)
                definition = root / f'layout{index}.json'
                definition.write_text(json.dumps({'layouts': [{'frame_cell': 'C8', 'image': 'sample.png', 'elements': [{'id': 'E-01', 'x': 0.1, 'y': 0.1, 'width': 0.5, 'height': 0.5}]}]}), encoding='utf-8')
                jobs.append({'source': source.name, 'definition': definition.name, 'output': f'output{index}.xlsx'})
            manifest = root / 'jobs.json'
            manifest.write_text(json.dumps({'jobs': jobs}), encoding='utf-8')
            batch_annotation.run(manifest)
            for job in jobs:
                book = load_workbook(root / job['output'])
                self.assertEqual(len(book['2. 画面レイアウト']._images), 1)
                book.close()

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
