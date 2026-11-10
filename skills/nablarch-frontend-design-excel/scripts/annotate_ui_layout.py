# 修正履歴
# 2026/11/10: 画面共通部品設計書に画像と編集可能な要素IDの注釈を追加。
"""Excelの表示枠に画像と編集可能な赤枠・要素IDを追加する。

Windows、Microsoft Excel、pywin32、Pillowが必要。
使い方: python -X utf8 annotate_ui_layout.py 入力.xlsx 定義.json 出力.xlsx
定義例は記入要領_画面共通部品設計書.mdを参照する。
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image


def _validate_region(element, ids):
    """要素IDと、画像を基準とした0〜1の相対座標を検証する。"""
    element_id = element.get('id')
    if element_id not in ids:
        raise ValueError(f'構成要素一覧にない要素ID: {element_id}')
    values = [element.get(key) for key in ('x', 'y', 'width', 'height')]
    if any(type(value) not in (int, float) for value in values):
        raise ValueError(f'{element_id}: 座標は数値で指定してください')
    x, y, width, height = values
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError(f'{element_id}: 相対座標が画像の範囲外です')


def _validate_definition(definition, base):
    """画像ファイルと指定値を検証し、注釈情報を正規化する。"""
    layouts = definition.get('layouts')
    if not isinstance(layouts, list) or not layouts:
        raise ValueError('layoutsに1件以上指定してください')
    result = []
    used = set()
    for layout in layouts:
        cell = layout.get('frame_cell', '')
        if not isinstance(cell, str) or not re.fullmatch(r'C[1-9]\d*', cell) or cell in used:
            raise ValueError(f'frame_cellが不正または重複しています: {cell}')
        used.add(cell)
        path = (base / layout['image']).resolve()
        with Image.open(path) as image:
            width, height = image.size
        elements = layout.get('elements')
        if not isinstance(elements, list) or not elements:
            raise ValueError(f'{cell}: 要素IDと矩形を指定してください')
        min_scale = layout.get('min_scale', 0.8)
        if type(min_scale) not in (float, int) or not 0 < min_scale <= 1:
            raise ValueError(f'{cell}: min_scaleは0より大きく1以下にしてください')
        result.append((cell, path, width, height, elements, min_scale))
    return result


def annotate(source, definition_path, output):
    """Excel自身で画像と図形を追加し、元ファイルと他の図形を保つ。"""
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.exists():
        raise ValueError('入力と異なる、まだ存在しない出力ファイルを指定してください')
    definition_path = Path(definition_path).resolve()
    definition = json.loads(definition_path.read_text(encoding='utf-8'))
    layouts = _validate_definition(definition, definition_path.parent)
    import pythoncom
    import win32com.client

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(suffix='.xlsx', dir=output.parent)
    os.close(fd)
    shutil.copy2(source, temp_name)
    excel = workbook = None
    pythoncom.CoInitialize()
    try:
        excel = win32com.client.DispatchEx('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = 3
        workbook = excel.Workbooks.Open(temp_name, UpdateLinks=0)
        sheet = workbook.Worksheets('2. 画面レイアウト')
        ids = set()
        for row in range(1, sheet.UsedRange.Rows.Count + 1):
            value = sheet.Cells(row, 3).Value
            if isinstance(value, str) and re.fullmatch(r'E-\d+', value.strip()):
                ids.add(value.strip())
        prepared = []
        for cell, path, width, height, elements, min_scale in layouts:
            frame = sheet.Range(cell).MergeArea
            rows = frame.Rows.Count
            if frame.Row != sheet.Range(cell).Row or frame.Column != sheet.Range(cell).Column:
                raise ValueError(f'{cell}: 結合枠の左上セルを指定してください')
            if not 14 <= rows <= 30 or frame.Height > 360.01:
                raise ValueError(f'{cell}: 枠は14〜30行、最大360ptにしてください')
            # 画像や注釈の二重配置を防ぎ、既存の図形は削除・変更しない。
            for shape in sheet.Shapes:
                if (shape.Left < frame.Left + frame.Width and shape.Left + shape.Width > frame.Left
                        and shape.Top < frame.Top + frame.Height and shape.Top + shape.Height > frame.Top):
                    raise ValueError(f'{cell}: 既存の画像または図形があります。Excelで確認してください')
            for element in elements:
                _validate_region(element, ids)
            # Excelはpt、画像は96dpi相当のpxとして計算する。縮小しすぎる場合は中止する。
            available_width, available_height = frame.Width - 8, frame.Height - 8
            scale = min(available_width / (width * 0.75), available_height / (height * 0.75), 1)
            if scale < min_scale:
                raise ValueError(f'{cell}: 画像の縮小率 {scale:.2f} が指定値 {min_scale:.2f} 未満です。枠を最大30行まで広げるか画像を見直してください')
            left, top = frame.Left + 4, frame.Top + 4
            prepared.append((frame, path, left, top, width * 0.75 * scale, height * 0.75 * scale, elements))
        # すべての枠の検証後に追加し、失敗時は元ファイルに変更を残さない。
        for frame, path, left, top, width, height, elements in prepared:
            frame.Cells(1, 1).Value = None
            sheet.Shapes.AddPicture(str(path), False, True, left, top, width, height)
            for element in elements:
                x = left + element['x'] * width
                y = top + element['y'] * height
                rectangle = sheet.Shapes.AddShape(1, x, y, element['width'] * width, element['height'] * height)
                rectangle.Fill.Visible = False
                rectangle.Line.ForeColor.RGB = 255
                rectangle.Line.Weight = 1.5
                label = sheet.Shapes.AddTextbox(1, x, max(top, y - 15), 50, 15)
                label.TextFrame.Characters().Text = element['id']
                label.TextFrame.Characters().Font.Color = 255
                label.Fill.Visible = False
                label.Line.Visible = False
        workbook.Save()
        workbook.Close(SaveChanges=False)
        workbook = None
        excel.Quit()
        excel = None
        os.replace(temp_name, output)
    finally:
        if workbook is not None:
            workbook.Close(SaveChanges=False)
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main():
    """コマンドラインから入力・定義・出力を受け取る。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('definition')
    parser.add_argument('output')
    args = parser.parse_args()
    try:
        annotate(args.source, args.definition, args.output)
    except (ValueError, OSError, KeyError) as error:
        print(f'エラー: {error}', file=sys.stderr)
        return 1
    print(f'作成しました: {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
