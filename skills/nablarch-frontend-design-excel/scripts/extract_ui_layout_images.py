# 修正履歴
# 2026/11/11: 設計書に埋め込まれた画像を注釈定義から抽出する。
"""Excelの各レイアウト枠内にある画像を、一時作業用に抽出する。"""
import argparse
import json
import re
import shutil
from pathlib import Path

import openpyxl


def extract(workbook_path, definition_path, output_dir):
    """枠ごとに画像が一つだけ存在することを確認してから出力する。"""
    definition_path = Path(definition_path)
    definition = json.loads(definition_path.read_text(encoding='utf-8'))
    layouts = definition.get('layouts')
    if not isinstance(layouts, list) or not layouts:
        raise ValueError('layoutsに1件以上指定してください。')
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('出力先には空のフォルダを指定してください。')
    workbook = openpyxl.load_workbook(workbook_path)
    try:
        sheet = workbook['2. 画面レイアウト']
        images = []
        names = set()
        for layout in layouts:
            cell = layout['frame_cell']
            name = layout['image']
            if not isinstance(cell, str) or not re.fullmatch(r'C[1-9]\d*', cell):
                raise ValueError(f'枠セルが不正です: {cell}')
            if not isinstance(name, str) or Path(name).name != name or name in names:
                raise ValueError(f'画像名が不正または重複しています: {name}')
            names.add(name)
            coordinate = sheet[cell]
            frame = next((r for r in sheet.merged_cells.ranges if r.min_row == coordinate.row and r.min_col == coordinate.column), None)
            if frame is None:
                raise ValueError(f'{cell}: 結合された画像枠が見つかりません。')
            matches = [image for image in sheet._images if frame.min_col <= image.anchor._from.col + 1 <= frame.max_col and frame.min_row <= image.anchor._from.row + 1 <= frame.max_row]
            if len(matches) != 1:
                raise ValueError(f'{cell}: 枠内の画像は1枚必要です（{len(matches)}枚）。')
            images.append((name, matches[0]._data()))
        destination.mkdir(parents=True, exist_ok=True)
        for name, content in images:
            (destination / name).write_bytes(content)
        shutil.copyfile(definition_path, destination / '画像配置.json')
    finally:
        workbook.close()


def main():
    """設計書、画像配置JSON、一時出力先を受け取る。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook')
    parser.add_argument('definition')
    parser.add_argument('output_dir')
    args = parser.parse_args()
    extract(args.workbook, args.definition, args.output_dir)
    print(f'画像を抽出しました: {args.output_dir}')


if __name__ == '__main__':
    main()
