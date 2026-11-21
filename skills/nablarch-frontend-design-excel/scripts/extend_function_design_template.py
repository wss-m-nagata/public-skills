# -*- coding: utf-8 -*-
"""
システム機能設計書(画面)のテンプレートの、内部設計情報の列を足す。

Nablarch の原本は、『2. 画面ID(画面名)』の画面項目定義に、内部設計情報の列を
『画面項目名（物理）』(AL〜AO を結合)の1列だけ持つ。
このスキルでは、画面とコードの両方から項目を探せるように、同じ書式・結合の列を右へ2つ足す。

    AL〜AO : 画面項目名（物理）  入力項目の name 属性（変数名と同じ値）。原本のまま
    AP〜AS : 画面項目ID          項目に付ける id 属性
    AT〜AW : 備考                id を付けられない項目の特定方法など

足した列は、印刷範囲（A〜AI）の外にある。

使い方:
    python extend_function_design_template.py <入力xlsx> <出力xlsx>

    入力は、原本、または build_formats.py が作ったテンプレート。
    すでに列がある場合は、何も足さずに、そのままコピーする。
    build_formats.py も、このスクリプトの extend_internal_columns() を使う。
"""

import sys
import warnings
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio, save_with_shapes  # noqa: E402

warnings.filterwarnings("ignore")

SCREEN_TEMPLATE_SHEET = "2. 画面ID(画面名)"
# 内部設計情報の列（それぞれ4列を結合）。1つ目が原本の列で、右の2つを足す
INTERNAL_COL_BLOCKS = (("AL", "AO"), ("AP", "AS"), ("AT", "AW"))
INTERNAL_HEADERS = {"AP": "画面項目ID", "AT": "備考"}  # 足す列の見出し（見出しの左上のセル）
INTERNAL_HEADER_ROWS = (53, 54)  # 見出し（2行を結合）
INTERNAL_ITEM_ROWS = (55, 65)  # 領域名の行(55)と項目の行(56〜65)。1行ずつ結合
INTERNAL_TITLE_CELL = "AK51"  # 「【内部設計情報】」の見出し
INTERNAL_TITLE = "【内部設計情報】 画面項目"


def _col(letter):
    return column_index_from_string(letter)


def has_extended_columns(ws):
    """内部設計情報の列が、すでに足されているか。"""
    return all(ws["%s%d" % (c, INTERNAL_HEADER_ROWS[0])].value == t for c, t in INTERNAL_HEADERS.items())


def extend_internal_columns(ws):
    """画面シートの内部設計情報へ、『画面項目ID』『備考』の列を足す（足してあれば、何もしない）。

    Args:
        ws: テンプレートの『2. 画面ID(画面名)』シート。
    Raises:
        AssertionError: 原本の結合セルが想定と違うとき（行や列の位置がずれたまま足さないため）。
    """
    if has_extended_columns(ws):
        return
    src_first, src_last = (_col(c) for c in INTERNAL_COL_BLOCKS[0])
    head_first = INTERNAL_HEADER_ROWS[0]
    item_first, item_last = INTERNAL_ITEM_ROWS
    merges = {
        (m.min_row, m.max_row)
        for m in ws.merged_cells.ranges
        if m.min_col == src_first and m.max_col == src_last
    }
    expect = {INTERNAL_HEADER_ROWS} | {(r, r) for r in range(item_first, item_last + 1)}
    if merges != expect:
        raise AssertionError(
            "内部設計情報の結合セルが想定と違います（原本が変わった可能性）: %s" % sorted(merges)
        )
    for first, _last in INTERNAL_COL_BLOCKS[1:]:
        offset = _col(first) - src_first
        # 書式
        for r in range(head_first, item_last + 1):
            for c in range(src_first, src_last + 1):
                ws.cell(row=r, column=c + offset)._style = copy(ws.cell(row=r, column=c)._style)
        # 結合
        for r1, r2 in sorted(merges):
            ws.merge_cells(
                start_row=r1,
                start_column=src_first + offset,
                end_row=r2,
                end_column=src_last + offset,
            )
    for letter, text in INTERNAL_HEADERS.items():
        ws["%s%d" % (letter, head_first)].value = text
    ws[INTERNAL_TITLE_CELL].value = INTERNAL_TITLE


def main():
    ensure_utf8_stdio()
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    src, out = sys.argv[1:3]
    wb = openpyxl.load_workbook(src)
    ws = wb[SCREEN_TEMPLATE_SHEET]
    if has_extended_columns(ws):
        print("列は、すでに足してあります。何もしません: %s" % src)
        return
    extend_internal_columns(ws)
    save_with_shapes(wb, src, out)
    print("足した: 画面項目ID（AP〜AS）、備考（AT〜AW）→ %s" % out)


if __name__ == "__main__":
    main()
