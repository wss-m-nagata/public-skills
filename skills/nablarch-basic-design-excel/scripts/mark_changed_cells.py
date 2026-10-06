# -*- coding: utf-8 -*-
"""
変更箇所を赤字(FF0000)で示す。版を上げるときは、前の版の赤字を黒(自動の色)に戻す。

赤字は「最新の版で変えた箇所」だけを指すようにする(記入要領_共通シート.md の
「版を上げたときの変更箇所の示し方」)。そのため、既存の設計書の版を上げるときは、次の順で使う。

    1. 値を書く前に、--reset-all で前の版の赤字をすべて黒に戻す
    2. 値を書いたあとに、今回変えたセルを赤字にする(シート名とセル座標を指定する)

外部インタフェース設計書(JSON)では、電文定義JSON側の各項目に "changed": true を
付けると build_external_if_json.py が自動で赤字にするが、テーブル定義書や一覧系のように
xlsxを直接編集して更新するテンプレートには、その自動化の仕組みが無い。
本スクリプトはその赤字の処理(xlsx_common.mark_font_red)を切り出し、
どのテンプレート・どのシートに対しても使えるようにしたもの。

apply_mapping.pyは値のみを書き換える方針(フォント等の書式は一切変更しない)だが、
レビュー時に変更箇所を一目で分かるようにするため、本スクリプトに限りこの用途の
文字色の変更だけを例外的に許可する。文字色以外のフォント属性(フォント名・サイズ・
太字等)は元のまま維持する。値が空欄のセルはマークしても見えないため対象外とする。

結合セルの場合は、範囲内のどのセル座標を指定しても自動的に書き込み可能な左上の
アンカーセルへマークする。

使い方:
    # 今回変えたセルを赤字にする
    python mark_changed_cells.py <対象xlsx> <シート名> <セル座標...> [--output <出力先>]

    # 前の版の赤字を、すべてのシートで黒(自動の色)に戻す
    python mark_changed_cells.py <対象xlsx> --reset-all [--output <出力先>]

例(テーブル定義書のスタッフマスタシート、入社日・退職日の項目定義2セルをマーク):
    python mark_changed_cells.py テーブル定義書_CM_共通基盤.xlsx スタッフマスタ AE19 AE20

--output を省略すると同じパスへ上書きする(呼び出し側で控えを取っている前提)。

文字色を変えるため、verify_layout.py は「フォント色が変化したセル」を差分として報告する。
値の反映(apply_mapping.py)の検証とは分け、本スクリプトの前後では、差分が文字色だけであることを確かめる。
"""

import argparse
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio, mark_font_red, save_with_shapes  # noqa: E402

# 変更箇所を示す赤(mark_font_red が付ける色)
RED = "FFFF0000"


def mark_changed_cells(path, sheet_name, coordinates, output=None):
    """指定したセルの文字色を赤にする。

    Args:
        path (str): 対象のxlsxのパス。
        sheet_name (str): シート名。
        coordinates (list[str]): セル座標の一覧。
        output (str | None): 出力先。省略時は path へ上書きする。

    Returns:
        tuple[list[str], list[str]]: 赤にしたアンカー座標と、空欄のためマークしなかった座標。
    """
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


def reset_all_red(path, output=None):
    """すべてのシートの赤字(FFFF0000)を、自動の色(黒)に戻す。

    文字色以外のフォント属性(フォント名・サイズ・太字など)は元のまま維持する。
    テーマの色やほかの赤系の色は、変更箇所の赤字ではないため対象にしない。

    Args:
        path (str): 対象のxlsxのパス。
        output (str | None): 出力先。省略時は path へ上書きする。

    Returns:
        list[str]: 黒に戻したセル（「シート名!座標」）の一覧。
    """
    output = output or path
    wb = openpyxl.load_workbook(path)
    reset = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                font = cell.font
                if font is None or font.color is None or font.color.rgb != RED:
                    continue
                # 色だけを外し、ほかの属性は引き継ぐ
                cell.font = Font(
                    name=font.name,
                    size=font.size,
                    bold=font.bold,
                    italic=font.italic,
                    vertAlign=font.vertAlign,
                    underline=font.underline,
                    strike=font.strike,
                )
                reset.append(f"{ws.title}!{cell.coordinate}")

    save_with_shapes(wb, path, output)
    return reset


def main():
    ensure_utf8_stdio()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("path")
    ap.add_argument("sheet", nargs="?")
    ap.add_argument("coordinates", nargs="*")
    ap.add_argument(
        "--reset-all", action="store_true", help="すべてのシートの赤字を黒に戻す"
    )
    ap.add_argument("--output")
    a = ap.parse_args()

    # 赤字を黒に戻す
    if a.reset_all:
        if a.sheet or a.coordinates:
            ap.error("--reset-all のときは、シート名とセル座標を指定しない")
        reset = reset_all_red(a.path, a.output)
        print(f"黒に戻したセル: {len(reset)} 件")
        for item in reset:
            print(f"  {item}")
        return

    # 今回変えたセルを赤字にする
    if not a.sheet or not a.coordinates:
        ap.error("シート名とセル座標を指定する（前の版の赤字を戻すときは --reset-all）")
    marked, skipped = mark_changed_cells(a.path, a.sheet, a.coordinates, a.output)
    if marked:
        print("marked:", ", ".join(marked))
    if skipped:
        print("skipped(空欄のためマークせず):", ", ".join(skipped), file=sys.stderr)


if __name__ == "__main__":
    main()
