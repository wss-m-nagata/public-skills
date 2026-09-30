# -*- coding: utf-8 -*-
"""
指定したセルの文字色だけを赤(FF0000)にし、変更箇所であることを示す。

外部インタフェース設計書(JSON)では、電文定義JSON側の各項目に "changed": true を
付けると build_external_if_json.py が自動でこの処理を行うが、テーブル定義書のように
xlsxを直接編集して更新するテンプレートには、その自動化の仕組みが無い。
本スクリプトはその赤字マーキング処理(xlsx_common.mark_font_red)だけを切り出し、
どのテンプレート・どのシートに対しても使えるようにしたもの。

apply_mapping.pyは値のみを書き換える方針(フォント等の書式は一切変更しない)だが、
レビュー時に変更箇所を一目で分かるようにするため、本スクリプトに限りこの用途の
赤字マーキングだけを例外的に許可する。文字色以外のフォント属性(フォント名・サイズ・
太字等)は元のまま維持する。値が空欄のセルはマークしても見えないため対象外とする。

結合セルの場合は、範囲内のどのセル座標を指定しても自動的に書き込み可能な左上の
アンカーセルへマークする。

使い方:
    python mark_changed_cells.py <対象xlsx> <シート名> <セル座標...> [--output <出力先>]

例(テーブル定義書のスタッフマスタシート、入社日・退職日の項目定義2セルをマーク):
    python mark_changed_cells.py テーブル定義書_CM_共通基盤.xlsx スタッフマスタ AE19 AE20

--output を省略すると同じパスへ上書きする(呼び出し側で控えを取っている前提)。
"""

import argparse
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio, mark_font_red, save_with_shapes  # noqa: E402


def mark_changed_cells(path, sheet_name, coordinates, output=None):
    output = output or path
    wb = openpyxl.load_workbook(path)
    if sheet_name not in wb.sheetnames:
        raise SystemExit(
            "シートが見つかりません: %r（存在するシート: %s）"
            % (sheet_name, ", ".join(wb.sheetnames))
        )
    ws = wb[sheet_name]

    marked, skipped = [], []
    for coordinate in coordinates:
        anchor = mark_font_red(ws, coordinate)
        if anchor is None:
            skipped.append(coordinate)
        else:
            marked.append(anchor)

    save_with_shapes(wb, path, output)
    return marked, skipped


def main():
    ensure_utf8_stdio()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("path")
    ap.add_argument("sheet")
    ap.add_argument("coordinates", nargs="+")
    ap.add_argument("--output")
    a = ap.parse_args()

    marked, skipped = mark_changed_cells(a.path, a.sheet, a.coordinates, a.output)
    if marked:
        print("marked:", ", ".join(marked))
    if skipped:
        print("skipped(空欄のためマークせず):", ", ".join(skipped), file=sys.stderr)


if __name__ == "__main__":
    main()
