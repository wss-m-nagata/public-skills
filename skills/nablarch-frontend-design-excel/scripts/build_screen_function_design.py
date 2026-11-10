# -*- coding: utf-8 -*-
"""
システム機能設計書(画面)を、定義ファイル(JSON)から組み立てるスクリプト。

テンプレートの『2. 画面ID(画面名)』は、1画面＝1シートで、画面項目定義・入出力一覧・画面イベント一覧・
画面イベント詳細・画面引継ぎ項目の行数が、画面ごとに違う。
行の複製・挿入・削除、シートの複製、目次の同期、画像の貼り付けを毎回手で行うと、結合セル・入力規則・
改ページ・印刷範囲がずれる。これらを本スクリプトへ寄せ、定義(JSON)から一括で組み立てる。

やること:
    1. 『1.1. 取引概要』へ、取引ID・取引名・取引概要・想定利用ユーザを書く（行が足りなければ広げる）。
    2. 画面の数だけ『2. 画面ID(画面名)』を複製し、名前を付け、シート内の章番号（2.1. など）を振り直す。
    3. 各画面のシートで、一覧表示・画面項目定義・入出力一覧・画面イベント一覧を、行数に合わせて広げる/縮める。
    4. 画面イベント詳細（自由記述の文・表）と、画面引継ぎ項目を、イベントごとに書く。
    5. 『目次』を、画面のシート名・章番号に同期する。
    6. 入力規則（プルダウン）を、広げた行にかけ直す。選択肢に無い値は警告する。
    7. 表紙・変更履歴を書く（apply_mapping.py と同じ書き込み）。
    8. 結合セルの長文が隠れないよう、行の高さを合わせる（fit_row_heights.py と同じ数え方）。
    9. 画面レイアウトの画像を、枠に収まる大きさにして、既存の図形を保ったまま貼る。
       画像は、シートの drawing の XML へ直接書き足す（openpyxl の add_image() は使わない。図形の復元と
       衝突するため）。位置は、左上・右下をセルで指定する twoCellAnchor にする（oneCellAnchor は、印刷の
       倍率で縮むセルに対して画像が縮まず、枠からはみ出した）。画像のパスが無い画面は、2.1 の枠に「（画像未添付）」の文字を入れる。

使い方:
    python build_screen_function_design.py <テンプレートxlsx> <定義json> <出力xlsx>

    テンプレートは、必ず assets/templates/フォーマット/ のシステム機能設計書(画面)を指定する
    （サンプルは人が編集した図形が残っているため、元ファイルにしない）。

定義JSONの形式（省略可のものに「省略可」と書いた。それ以外は必須。仕様に無い値は、補わずエラーにする）:
{
  "tx_id": "ORD01",                      # 取引ID。『1.1. 取引概要』と、成果物名の欄に入る
  "tx_name": "受注の一覧と詳細",         # 取引名
  "overview": ["受注の一覧を検索し、詳細を表示する。", ""],   # 取引概要。1要素=1行。""は空行。長い行は自動で折り返す
  "users": ["受注担当者"],                # 想定利用ユーザ。1要素=1行
  "header": {                            # 表紙・変更履歴
    "pj": "受注管理プロジェクト", "system": "受注管理システム", "subsystem": "受注管理サブシステム",
    "author": "山田太郎", "date": "2026-11-06",     # date は YYYY-MM-DD 形式
    "company": "株式会社サンプル", "dept": "開発部",
    "version": "第1.0版",                           # 省略可。省略時は「第1.0版」
    "history": [                                    # 省略可。省略時は、新規作成の1行だけを書く
      {"version": "第1.0版", "date": "2026-11-06", "kind": "新規",
       "where": "-", "what": "新規作成", "author": "山田太郎"}
    ]                                               # where / what は、文字列（改行は\\n）または1行ずつの配列
  },
  "screens": [
    {
      "id": "ORD0101", "name": "受注一覧画面",      # 画面ID・画面名。シート名は「2. ORD0101(受注一覧画面)」
      "sheet_name": "2. ORD0101(受注一覧)",         # 省略可。31文字を超えるときに指定する
      "layouts": [                                  # 2.1 画面レイアウト。省略可（省略すると、「（画像未添付）」の文字を入れる）
        {"image": "images/ord0101.png",             # 画像のパス（定義JSONのあるフォルダからの相対）。省略可
         "caption": "初期表示"}                      # 画像の見出し。省略可
      ],
      "list_areas": [                               # 2.2 一覧表示。一覧のある領域。無ければ []
        {"name": "検索結果", "paging": "有", "sort": "受注日の降順", "note": "-"}
      ],
      "regions": [                                  # 2.3 画面項目定義。領域ごとに1つ
        {"name": "検索条件",
         "items": [
           {"name": "顧客名", "type": "text",       # type はプルダウン（データシートの画面項目種類）
            "source": "-",                          # 情報取得元。APIの項目は「API名.項目名」で書く
            "edit": "＜入力チェック＞\\n全角50文字以内",    # 編集仕様。表示変換・入力チェック・表示条件
            "initial": "-", "required": "-",        # required は ○ か -
            "domain": "顧客名",                      # ドメイン名
            "phys": "searchForm.customerName",      # 画面項目名（物理）
            "cont": false,                          # 省略可。true なら、直前の項目の続き（番号を振らない）
            "changed": false}                       # 省略可。true にすると、その行の文字色を赤にする
         ]}
      ],
      "io": [                                       # 2.4 入出力一覧。画面 ⇄ API。無ければ []
        {"name": "受注検索API 応答", "kind": "電文", "io": "I",
         "c": "-", "r": "-", "u": "-", "d": "-", "lock": "-",   # 省略可。省略時は「-」
         "note": "受注検索APIの応答", "changed": false}
      ],
      "events": [                                   # 2.5 画面イベント一覧 / 2.6 画面イベント詳細
        {"name": "初期表示", "timing": "画面の表示時", "summary": "…", "next": "-",
         "server": "あり(非同期)",                   # プルダウン（データシートのサーバ通信有無）
         "changed": false,
         "detail": [                                # 2.6 のイベント詳細。省略可（省略すると「-」を書く）
           {"h1": "(1) 入力チェック"},               # 見出し。h1(E列) h2(F列) h3(G列)
           {"text": "全項目をクライアントで検査する。"},   # 文。長い文は自動で折り返す。indent 省略時は F列
           {"table": {"preset": "validation",       # 表。preset 省略時は columns を指定する
                      "rows": [["1", "必須", "顧客名が入力されていること。", "M001", "-", "継続する"]]}},
           {"table": {"columns": [{"title": "No.", "span": 1}, {"title": "項目", "span": 8}],
                      "rows": [["1", "…"]], "indent": 1}}
         ],
         "handover": [                              # 画面引継ぎ項目（内部設計情報）。省略可
           {"group": "検索条件", "prefix": "order",
            "items": [{"name": "顧客名", "store": "ルートのクエリ", "value": "検索条件の入力値",
                       "desc": "戻ったときの再検索に使う", "note": "-"}]}
         ]}
      ]
    }
  ]
}

表の preset（columns の span は、表の左端の列からの列数。合計は、indent 1（F列）で29列）:
    validation : No. / チェック名 / チェック内容 / メッセージID / 埋め込み文字列 / 後続チェックの続行判定
    parameter  : パラメータ / 設定値
    api_error  : HTTPステータス / エラーコード / メッセージID / 画面の動作

検証（verify_layout.py は、この出力には使わない）:
    シートの複製・改名、行の増減、目次の書き換え、入力規則の範囲の変更があるため、テンプレートとの比較は
    必ず NG になる。代わりに、次の3つで確かめる。
      1. 終了コードが 0 であること。
      2. 表示された警告を、すべて確かめること（プルダウンに無い値・画像未添付など）。
      3. export_sheet_preview.py で各シートを PDF にして目視すること（長文が隠れない・画像が枠に収まる・節が重ならない）。
    比べる必要が出たら、verify_layout.diff_sheet でシートごとに比べる。想定される差分は、次のとおり。
      - 画面のシート名の変更、シートの追加（複製）、目次の文字
      - 2.2〜2.5・画面項目定義の行数の増減による、結合セル・罫線・行高・入力規則の範囲の変化
      - 2.6 と画面引継ぎ項目の、行位置・結合セルの変化
      - 行の高さが広がった行（長文のため）、赤字（changed）のセル、変更履歴のS1の折り返し
    これ以外の差分（表紙・データシートの変化、ラベル・見出しの文字や背景色の変化、図形の消失など）は異常である。

終了コード: 0=成功。定義にエラーがあるときは、メッセージを表示して 1 で終わる（出力は作らない）。
"""

import argparse
import json
import math
import os
import re
import shutil
import sys
import tempfile
import zipfile
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.worksheet.cell_range import CellRange
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.pagebreak import Break, RowBreak
from PIL import Image as PILImage

sys.path.insert(0, str(Path(__file__).parent))
from apply_mapping import apply_mapping  # noqa: E402
from fit_change_history_rows import (  # noqa: E402
    _display_width,
    _merged_width,
    fit_rows as fit_history_rows,
)
from fit_row_heights import WORD, fit_sheet  # noqa: E402
from insert_rows import insert_rows_keep_layout  # noqa: E402
from normalize_change_history import normalize as normalize_history  # noqa: E402
from restore_shapes import (  # noqa: E402
    NS_R,
    _find_drawing_for_sheet,
    _sheet_name_to_target,
)
from xlsx_common import (  # noqa: E402
    ensure_utf8_stdio,
    mark_font_red,
    resolve_list_values,
    save_with_shapes,
)

# ---------------------------------------------------------------------------
# テンプレートの位置（assets/templates/フォーマット/ のテンプレートの、未編集の行番号）
# ---------------------------------------------------------------------------
OVERVIEW_SHEET = "1.1. 取引概要"
SCREEN_TEMPLATE_SHEET = "2. 画面ID(画面名)"
TOC_SHEET = "目次"
DATA_SHEET = "データ"
HISTORY_SHEET = "変更履歴"
COVER_SHEET = "表紙"
PRODUCT_NAME = "システム機能設計書(画面)"

# スタイルを取り込む最大の列（AU列。シートの使用範囲）
MAX_COL = 47

# 『1.1. 取引概要』: 取引概要の行（10〜29）、想定利用ユーザの行（30〜34）。値は G列から書く
OV_FIRST, OV_LAST = 10, 29
US_FIRST, US_LAST = 30, 34
OV_VALUE_COL = "G"
OV_LABEL_LAST_COL = "F"
OV_VALUE_LAST_COL = "AG"

# 『2. 画面ID(画面名)』
ROW_HEAD = 5  # B5: 「2. [画面ID]([画面名])」
ROW_H21 = 6  # C6: 2.1 画面レイアウト
LAYOUT_FIRST, LAYOUT_LAST = 8, 41  # 画像を置く行（42行目は次の見出しの前の空き）
ROW_H22 = 43
LIST_FIRST, LIST_LAST = 46, 47  # 2.2 一覧表示のデータ行
ROW_H23 = 50
ITEM_BLOCK_FIRST, ITEM_BLOCK_LAST = 55, 65  # 2.3: 領域名の行(55)＋項目の行(56〜65)
ROW_H24 = 71
IO_FIRST, IO_LAST = 75, 77  # 2.4 入出力一覧のデータ行
ROW_H25 = 80
EV_FIRST, EV_LAST = 83, 85  # 2.5 画面イベント一覧のデータ行
ROW_H26 = 88
DETAIL_FIRST, DETAIL_LAST = 89, 125  # 2.6: イベント見出し(89)＋自由記述(90〜125)
HAND_HEAD = 126  # 「【内部設計情報】 画面引継ぎ項目」
HAND_BLOCK_FIRST, HAND_BLOCK_LAST = (
    127,
    134,
)  # 画面引継ぎ項目の1イベント分（見出し・空き・表の見出し2行・グループ・項目×2）
# 元の改ページ（この行の下で改ページ）
PAGE_BREAK_ROWS = (41, 69, 86)
PRINT_LAST_COL = "AI"

# 画面項目定義の列（左端の列番号）
ITEM_COLS = {
    "no": "E",
    "name": "F",
    "type": "J",
    "source": "N",
    "edit": "V",
    "initial": "AA",
    "required": "AD",
    "domain": "AE",
    "phys": "AL",
}
# 一覧表示
LIST_COLS = {"no": "D", "name": "E", "paging": "N", "sort": "Q", "note": "V"}
# 入出力一覧
IO_COLS = {
    "no": "D",
    "name": "E",
    "kind": "K",
    "io": "O",
    "c": "P",
    "r": "Q",
    "u": "R",
    "d": "S",
    "lock": "T",
    "note": "V",
}
# 画面イベント一覧
EV_COLS = {
    "no": "D",
    "name": "E",
    "timing": "K",
    "summary": "R",
    "next": "Z",
    "server": "AE",
}
# 画面引継ぎ項目（項目の行）
HAND_ITEM_COLS = {
    "no": "C",
    "name": "D",
    "store": "L",
    "value": "P",
    "desc": "U",
    "note": "AB",
}

# 画面イベント詳細の表の preset。span は列数。F列(indent 1)から AH列までの29列に収める
PRESETS = {
    "validation": [
        ("No.", 1),
        ("チェック名", 6),
        ("チェック内容", 10),
        ("メッセージID", 3),
        ("埋め込み文字列", 4),
        ("後続チェックの続行判定", 5),
    ],
    "parameter": [("パラメータ", 7), ("設定値", 22)],
    "api_error": [
        ("HTTPステータス", 5),
        ("エラーコード", 6),
        ("メッセージID", 6),
        ("画面の動作", 12),
    ],
}
# 自由記述の文が収まる右端の列（この列まで。AI列は余白）
TEXT_LAST_COL = "AH"
# 文字数の見積もり（fit_row_heights.py と同じ、列幅の合計に対する割合）
CHARS_PER_WIDTH = 0.95
# 見出しの列（indent 0=E, 1=F, 2=G）
H_LEVEL_COL = {"h1": 5, "h2": 6, "h3": 7}
DEFAULT_TEXT_INDENT = 1

# 画像: 貼る左端の列(D列)と、収める最大の高さ(px)。
# 幅は、D〜AI列の列幅の合計から求める（既定の列幅4.83のとき1列29px、32列で約928px）。
# 高さは、2.1の枠（8〜41行目）に、見出しの1行と空き1行を残して収まる32行分（1行16px）までとする。
IMAGE_COL = 4
IMAGE_LAST_COL = 35
IMAGE_MAX_H = 512
ROW_PX = 16  # 行高12ポイント
EMU_PER_PIXEL = 9525
# 列幅(Excelの幅の単位)からpxへ。最大桁幅6px（MS 明朝9ポイント。Excelで確かめた値）の換算
MAX_DIGIT_PX = 6

# 「画面項目種別」などのプルダウンの種類 → 入力規則のかかる列範囲を決めるための名前
DV_KINDS = ("paging", "io_kind", "io_dir", "circle", "item_type")
# 元の入力規則の、先頭セル → 種類
DV_FIRST_CELL = {
    "N46": "paging",
    "K75": "io_kind",
    "O75": "io_dir",
    "P75": "circle",
    "J56": "item_type",
}

# シート名に使えない文字
SHEET_NAME_NG = "[" + re.escape("[]:*?/\\") + "]"

# 画面レイアウトの画像が無いときに、枠の中へ入れる文字
PLACEHOLDER_TEXT = "（画像未添付）"

# 変更履歴の行
HISTORY_FIRST_ROW = 8
HISTORY_LAST_ROW = 33


class DefinitionError(Exception):
    """定義JSONの誤り。メッセージをまとめて表示するために使う。"""


# ---------------------------------------------------------------------------
# 小さな部品
# ---------------------------------------------------------------------------
def _col(letter):
    """列の文字を列番号にする。"""
    return column_index_from_string(letter)


def _is_blank(v):
    """値が未指定か。"""
    return v is None or v == ""


def _mark(flag_cells, ws, row, cols):
    """赤字にするセルの座標を控える。"""
    for c in cols:
        flag_cells.append(
            (
                ws.title,
                "%s%d" % (get_column_letter(c) if isinstance(c, int) else c, row),
            )
        )


def _circle(v):
    """真偽値・文字列を、○/- の表記にする。"""
    if v is True:
        return "○"
    if v is False or _is_blank(v):
        return "-"
    return str(v)


def _dash(v):
    """未指定は「-」を書く（該当しない欄を空欄にしない）。"""
    return "-" if _is_blank(v) else v


def _column_width(ws, idx):
    """列幅。fit_change_history_rows.py と同じ探し方で、設定が無ければ既定の列幅。"""
    for dim in ws.column_dimensions.values():
        low = dim.min or column_index_from_string(dim.index)
        high = dim.max or low
        if low <= idx <= high and dim.width:
            return dim.width
    return ws.sheet_format.defaultColWidth or 8.43


def _capacity(ws, first_col, last_col):
    """first_col〜last_col に収まる、表示幅（半角1・全角2）の見積もり。"""
    total = sum(_column_width(ws, i) for i in range(first_col, last_col + 1))
    return total * CHARS_PER_WIDTH


def _split_lines(text, capacity):
    """文を、列幅に収まる長さの行に分ける（1行につき1セルに書くため）。

    セル内改行(\\n)で先に分ける。英数字の続きは、途中で切らない。
    「・」「※」で始まる文は、続きの行を全角スペースで字下げする。
    """
    out = []
    for part in str(text).split("\n"):
        hang = "　" if part[:1] in ("・", "※") else ""
        line, used, pos = "", 0, 0
        while pos < len(part):
            m = WORD.match(part, pos)
            token = m.group(0) if m else part[pos]
            w = _display_width(token)
            if used + w > capacity and line.strip():
                out.append(line)
                line = hang
                used = _display_width(hang)
            line += token
            used += w
            pos += len(token)
        out.append(line)
    return out


def _put(ws, row, col, value):
    """セルへ値を書く。数式のセル・結合の途中のセルへは書かない（位置の誤りを早く見つけるため）。"""
    cell = ws.cell(row=row, column=col)
    if isinstance(cell, MergedCell):
        raise AssertionError(
            "結合セルの途中へ書こうとしました: %s!%s" % (ws.title, cell.coordinate)
        )
    if cell.data_type == "f":
        raise AssertionError(
            "数式のセルへ書こうとしました: %s!%s" % (ws.title, cell.coordinate)
        )
    cell.value = value


def _put_text(ws, row, col, text):
    """自由記述の文を書く。折り返さず、右の空きセルへはみ出して表示する（1行につき1セル）。"""
    _put(ws, row, col, text)
    ws.cell(row=row, column=col).alignment = Alignment(
        horizontal="left", vertical="top", wrap_text=False
    )


# --- 行のひな形（書式・結合・行高）を取り込んで、別の行へ写す ---------------------
def _capture_block(ws, first, last):
    """first〜last行の書式・結合・行高・値を取り込む。"""
    rows = range(first, last + 1)
    return {
        "styles": [
            [copy(ws.cell(row=r, column=c)._style) for c in range(1, MAX_COL + 1)]
            for r in rows
        ],
        "values": [
            [ws.cell(row=r, column=c).value for c in range(1, MAX_COL + 1)]
            for r in rows
        ],
        "heights": [ws.row_dimensions[r].height for r in rows],
        "merges": [
            (m.min_row - first, m.min_col, m.max_row - first, m.max_col)
            for m in ws.merged_cells.ranges
            if first <= m.min_row and m.max_row <= last
        ],
    }


def _stamp_block(ws, top, blk, keep_values=False):
    """取り込んだひな形を、top行から写す。値は消す（keep_values なら、ひな形の値も写す）。"""
    n = len(blk["styles"])
    for m in [
        m
        for m in ws.merged_cells.ranges
        if m.max_row >= top and m.min_row <= top + n - 1
    ]:
        ws.unmerge_cells(str(m))
    for i in range(n):
        ws.row_dimensions[top + i].height = blk["heights"][i]
        for c in range(1, MAX_COL + 1):
            cell = ws.cell(row=top + i, column=c)
            cell._style = copy(blk["styles"][i][c - 1])
            cell.value = blk["values"][i][c - 1] if keep_values else None
    for r1, c1, r2, c2 in blk["merges"]:
        ws.merge_cells(
            start_row=top + r1, start_column=c1, end_row=top + r2, end_column=c2
        )


def _clear_block_values(ws, first, last):
    """first〜last行の、結合の左上以外の値を消す（結合の途中のセルは対象外）。"""
    for r in range(first, last + 1):
        for c in range(1, MAX_COL + 1):
            cell = ws.cell(row=r, column=c)
            if not isinstance(cell, MergedCell):
                cell.value = None


def _delete_rows_keep_layout(ws, at_row, count, max_col=MAX_COL):
    """at_row から count 行を削除し、下の結合セル・行高を上へずらす（insert_rows_keep_layout の逆）。"""
    if count <= 0:
        return
    merges = [CellRange(str(m)) for m in list(ws.merged_cells.ranges)]
    for m in merges:
        ws.unmerge_cells(m.coord)
    heights = {
        r: d.height for r, d in ws.row_dimensions.items() if d.height is not None
    }
    last = at_row + count - 1
    ws.delete_rows(at_row, count)
    for m in merges:
        if m.max_row < at_row:
            pass
        elif m.min_row > last:
            m.shift(row_shift=-count)
        else:
            if not (at_row <= m.min_row and m.max_row <= last):
                raise AssertionError(
                    "削除する行にまたがる結合セルがあります: %s" % m.coord
                )
            continue
        ws.merge_cells(m.coord)
    for r in sorted(heights):
        if r >= at_row:
            ws.row_dimensions[r].height = None
    for r, h in heights.items():
        if r > last:
            ws.row_dimensions[r - count].height = h


def _resize_rows(ws, first, have, need):
    """first行から have 行ある表の行数を、need 行にする。増やすときは末尾へ、減らすときは末尾から。

    Returns:
        int: 増減した行数（増やすと正）。
    """
    if need > have:
        insert_rows_keep_layout(
            ws, first + have, need - have, first + have - 1, max_col=MAX_COL
        )
    elif need < have:
        _delete_rows_keep_layout(ws, first + need, have - need)
    return need - have


# ---------------------------------------------------------------------------
# 定義JSONの検査
# ---------------------------------------------------------------------------
def _sheet_name(num, sc):
    """画面のシート名。sheet_name の指定があればそれ、無ければ「N. 画面ID(画面名)」。"""
    return sc.get("sheet_name") or "%d. %s(%s)" % (num, sc["id"], sc["name"])


def _validate(d, base_dir):
    """定義を検査し、誤りの一覧を返す。仕様に無い値は補わない。"""
    errs = []

    def need(obj, key, where, kinds=(str,)):
        if (
            key not in obj
            or obj[key] is None
            or (isinstance(obj[key], str) and obj[key] == "")
        ):
            errs.append("%s: 「%s」がありません。" % (where, key))
            return None
        if not isinstance(obj[key], kinds):
            errs.append("%s: 「%s」の型が違います。" % (where, key))
            return None
        return obj[key]

    for key in ("tx_id", "tx_name"):
        need(d, key, "定義")
    for key in ("overview", "users", "screens"):
        need(d, key, "定義", (list,))
    h = need(d, "header", "定義", (dict,))
    if h:
        for key in ("pj", "system", "subsystem", "author", "date", "company", "dept"):
            need(h, key, "header")
    if not d.get("screens"):
        errs.append("定義: 「screens」が空です。画面を1つ以上書いてください。")
    seen_ids = set()
    for i, s in enumerate(d.get("screens") or []):
        w = "screens[%d]" % i
        if not isinstance(s, dict):
            errs.append("%s: 画面の定義がオブジェクトではありません。" % w)
            continue
        sid = need(s, "id", w)
        sname = need(s, "name", w)
        if sid and sname:
            sheet = _sheet_name(i + 2, s)
            if len(sheet) > 31 or re.search(SHEET_NAME_NG, sheet):
                errs.append(
                    "%s: シート名「%s」は、31文字以内で、[ ] : * ? / バックスラッシュ を含めない名前にしてください"
                    "（sheet_name で指定できます）。" % (w, sheet)
                )
        if sid in seen_ids:
            errs.append("%s: 画面ID「%s」が重複しています。" % (w, sid))
        seen_ids.add(sid)
        w = "%s(%s)" % (w, sid)
        for key in ("list_areas", "regions", "io", "events"):
            need(s, key, w, (list,))
        if not s.get("regions"):
            errs.append("%s: 「regions」が空です。領域を1つ以上書いてください。" % w)
        if not s.get("events"):
            errs.append(
                "%s: 「events」が空です。画面イベントを1つ以上書いてください。" % w
            )
        for j, a in enumerate(s.get("list_areas") or []):
            need(a, "name", "%s.list_areas[%d]" % (w, j))
        for j, r in enumerate(s.get("regions") or []):
            rw = "%s.regions[%d]" % (w, j)
            need(r, "name", rw)
            need(r, "items", rw, (list,))
            if not r.get("items"):
                errs.append(
                    "%s: 「items」が空です。項目を1つ以上書いてください（項目の無い領域は書かない）。"
                    % rw
                )
            for k, it in enumerate(r.get("items") or []):
                iw = "%s.items[%d]" % (rw, k)
                if not it.get("cont"):
                    need(it, "name", iw)
                need(it, "type", iw)
        for j, o in enumerate(s.get("io") or []):
            ow = "%s.io[%d]" % (w, j)
            for key in ("name", "kind", "io"):
                need(o, key, ow)
        for j, e in enumerate(s.get("events") or []):
            ew = "%s.events[%d]" % (w, j)
            for key in ("name", "timing", "summary", "next", "server"):
                need(e, key, ew)
            for k, b in enumerate(e.get("detail") or []):
                bw = "%s.detail[%d]" % (ew, k)
                keys = [x for x in ("h1", "h2", "h3", "text", "table") if x in b]
                if len(keys) != 1:
                    errs.append(
                        "%s: h1/h2/h3/text/table のうち、ちょうど1つを書いてください。"
                        % bw
                    )
                elif keys[0] == "table":
                    t = b["table"]
                    if "preset" in t and t["preset"] not in PRESETS:
                        errs.append(
                            "%s: preset「%s」はありません（%s）。"
                            % (bw, t["preset"], ", ".join(PRESETS))
                        )
                    cols = (
                        _table_columns(t) if ("preset" in t or "columns" in t) else None
                    )
                    if cols is None:
                        errs.append(
                            "%s: table には preset か columns が要ります。" % bw
                        )
                    else:
                        for row in t.get("rows") or []:
                            if len(row) != len(cols):
                                errs.append(
                                    "%s: 表の行の列数(%d)が、見出しの列数(%d)と違います: %s"
                                    % (bw, len(row), len(cols), row)
                                )
                        if (
                            sum(c[1] for c in cols)
                            + t.get("indent", DEFAULT_TEXT_INDENT)
                            + 4
                            > _col(TEXT_LAST_COL) + 1
                        ):
                            errs.append(
                                "%s: 表の列数の合計が、シートの幅（%s列まで）を超えます。"
                                % (bw, TEXT_LAST_COL)
                            )
            for k, g in enumerate(e.get("handover") or []):
                gw = "%s.handover[%d]" % (ew, k)
                need(g, "group", gw)
                need(g, "items", gw, (list,))
                for m, it in enumerate(g.get("items") or []):
                    need(it, "name", "%s.items[%d]" % (gw, m))
        for j, lay in enumerate(s.get("layouts") or []):
            img = lay.get("image")
            if img and not (Path(base_dir) / img).is_file():
                errs.append("%s.layouts[%d]: 画像が見つかりません: %s" % (w, j, img))
    return errs


def _table_columns(t):
    """表の列定義 [(見出し, 列数)] を返す。preset か columns から。"""
    if "preset" in t:
        cols = list(PRESETS[t["preset"]])
        if "columns" in t:
            return None
        return cols
    out = []
    cols = t["columns"]
    n = len(cols)
    spans_given = [c.get("span") if isinstance(c, dict) else None for c in cols]
    rest = _col(TEXT_LAST_COL) - (t.get("indent", DEFAULT_TEXT_INDENT) + 5) + 1
    fixed = sum(s for s in spans_given if s)
    free = [i for i, s in enumerate(spans_given) if not s]
    for i, c in enumerate(cols):
        title = c["title"] if isinstance(c, dict) else c
        if spans_given[i]:
            span = spans_given[i]
        elif title == "No.":
            span = 1
        else:
            others = [
                j
                for j in free
                if (cols[j]["title"] if isinstance(cols[j], dict) else cols[j]) != "No."
            ]
            no_cols = len(free) - len(others)
            span = max(1, (rest - fixed - no_cols) // max(1, len(others)))
        out.append((title, span))
    _ = n
    return out


# ---------------------------------------------------------------------------
# 『1.1. 取引概要』
# ---------------------------------------------------------------------------
def _build_overview(wb, d, report):
    """取引ID・取引名・取引概要・想定利用ユーザを書く。行が足りなければ広げる。"""
    ws = wb[OVERVIEW_SHEET]
    vcol = _col(OV_VALUE_COL)
    cap = _capacity(ws, vcol, _col(OV_VALUE_LAST_COL))

    # 取引概要・想定利用ユーザの、画面に出す行
    ov_lines = [
        ln for t in d["overview"] for ln in (_split_lines(t, cap) if t else [""])
    ]
    us_lines = [ln for t in d["users"] for ln in _split_lines(t, cap)]
    if not us_lines:
        us_lines = ["-"]
    if not ov_lines:
        ov_lines = ["-"]

    off = 0
    # 取引概要の行が足りなければ、最後の行の前へ広げる（最後の行の下罫線を保つため）
    extra = max(0, len(ov_lines) - (OV_LAST - OV_FIRST + 1))
    if extra:
        insert_rows_keep_layout(ws, OV_LAST, extra, OV_LAST - 1, max_col=MAX_COL)
        ws.unmerge_cells("C%d:F%d" % (OV_FIRST, OV_LAST))
        ws.merge_cells("C%d:F%d" % (OV_FIRST, OV_LAST + extra))
        off += extra
    # 想定利用ユーザの行が足りなければ、同じく広げる
    extra_u = max(0, len(us_lines) - (US_LAST - US_FIRST + 1))
    if extra_u:
        last = US_LAST + off
        insert_rows_keep_layout(ws, last, extra_u, last - 1, max_col=MAX_COL)
        ws.unmerge_cells("C%d:F%d" % (US_FIRST + off, last))
        ws.merge_cells("C%d:F%d" % (US_FIRST + off, last + extra_u))
        off += extra_u

    _put(ws, 8, vcol, d["tx_id"])
    _put(ws, 9, vcol, d["tx_name"])
    for i, ln in enumerate(ov_lines):
        _put(ws, OV_FIRST + i, vcol, ln if ln != "" else None)
    for i, ln in enumerate(us_lines):
        _put(ws, US_FIRST + (extra if extra else 0) + i, vcol, ln)

    area = CellRange(ws.print_area.split("!")[-1].replace("$", ""))
    area.expand(down=off)
    ws.print_area = area.coord
    report["overview_rows_added"] = off


# ---------------------------------------------------------------------------
# 『2. 画面ID(画面名)』
# ---------------------------------------------------------------------------
class _Template:
    """複製・編集の前に取り込んだ、画面シートのひな形。"""

    def __init__(self, ws):
        self.list_row = _capture_block(ws, LIST_FIRST, LIST_FIRST)
        self.region_row = _capture_block(ws, ITEM_BLOCK_FIRST, ITEM_BLOCK_FIRST)
        self.item_row = _capture_block(ws, ITEM_BLOCK_FIRST + 1, ITEM_BLOCK_FIRST + 1)
        self.io_row = _capture_block(ws, IO_FIRST, IO_FIRST)
        self.ev_row = _capture_block(ws, EV_FIRST, EV_FIRST)
        self.hand_head = _capture_block(ws, HAND_BLOCK_FIRST, HAND_BLOCK_FIRST)
        self.hand_blank = _capture_block(ws, HAND_BLOCK_FIRST + 1, HAND_BLOCK_FIRST + 1)
        self.hand_hdr = _capture_block(ws, HAND_BLOCK_FIRST + 2, HAND_BLOCK_FIRST + 3)
        self.hand_group = _capture_block(ws, HAND_BLOCK_FIRST + 4, HAND_BLOCK_FIRST + 4)
        self.hand_item = _capture_block(ws, HAND_BLOCK_FIRST + 5, HAND_BLOCK_FIRST + 5)
        self.free_row = _capture_block(ws, DETAIL_LAST, DETAIL_LAST)
        # 自由記述の表に使う書式は、2.4 入出力一覧の見出し・データから借りる（見た目をそろえるため）
        self.tbl_head = copy(ws["E%d" % (IO_FIRST - 2)]._style)
        self.tbl_data = copy(ws["E%d" % IO_FIRST]._style)
        self.tbl_no = copy(ws["D%d" % IO_FIRST]._style)
        self.dvs = {}
        for dv in ws.data_validations.dataValidation:
            first = str(dv.sqref).split()[0].split(":")[0]
            kind = DV_FIRST_CELL.get(first)
            if kind is None:
                raise AssertionError(
                    "想定外の入力規則です（テンプレートが変わった可能性）: %s"
                    % dv.sqref
                )
            self.dvs[kind] = dv.formula1
        if set(self.dvs) != set(DV_KINDS):
            raise AssertionError("入力規則の種類が足りません: %s" % sorted(self.dvs))


def _copy_sheet_extras(src, dst):
    """copy_worksheet が写さない設定（印刷タイトル・フッター・表示）を写す。"""
    dst.print_title_rows = src.print_title_rows
    dst.HeaderFooter = copy(src.HeaderFooter)
    dst.sheet_view.showGridLines = src.sheet_view.showGridLines
    dst.sheet_view.view = src.sheet_view.view
    dst.sheet_view.zoomScale = src.sheet_view.zoomScale
    dst.sheet_view.zoomScaleNormal = src.sheet_view.zoomScaleNormal
    dst.sheet_view.zoomScalePageLayoutView = src.sheet_view.zoomScalePageLayoutView


def _dv_allowed(wb, formula):
    """入力規則の選択肢の一覧。"""
    return resolve_list_values(wb, formula)


def _end_cell(ws, row, col, cx, cy):
    """画像の左上のセル(row, col。1始まり)と大きさ(EMU)から、右下の位置を求める。

    画像は、左上と右下をセルの位置で指定する(twoCellAnchor)。大きさをEMUだけで指定する
    oneCellAnchor は、A4横・幅に合わせて印刷したとき、セルは縮むのに画像は縮まず、枠からはみ出した
    (PDFで確かめた)。セルの位置で指定すれば、印刷の倍率に合わせて画像も縮む。

    Returns:
        tuple: (終了の列, 列内のずれ(EMU), 終了の行, 行内のずれ(EMU))。列・行は0始まり。
    """
    c, left = col - 1, cx
    while True:
        w = (
            int(
                (256 * _column_width(ws, c + 1) + int(128 / MAX_DIGIT_PX))
                / 256
                * MAX_DIGIT_PX
            )
            * EMU_PER_PIXEL
        )
        if left < w:
            break
        left -= w
        c += 1
    r, top = row - 1, cy
    while True:
        h = int(
            (
                ws.row_dimensions[r + 1].height
                or ws.sheet_format.defaultRowHeight
                or 11.25
            )
            * 12700
        )
        if top < h:
            break
        top -= h
        r += 1
    return c, left, r, top


def _build_screen(wb, ws, num, sc, tpl, base_dir, ctx):
    """1画面分のシートを組み立てる。

    Args:
        wb: ブック。
        ws: 画面のシート（テンプレートまたはその複製）。
        num: シートの章番号（2, 3, …）。
        sc: 画面の定義。
        tpl: _Template。
        base_dir: 画像の相対パスの基準。
        ctx: 警告・赤字・行の高さ・画像などを集める辞書。
    """
    off = 0  # 元の行番号に足すずれ（行を増減するたびに更新する）
    fits = []  # 行の高さを合わせる範囲 (先頭行, 末尾行, only_merged)
    red = ctx["red"]
    warn = ctx["warnings"]
    name = "%s(%s)" % (sc["id"], sc["name"])

    # 入力規則はいったん外し、最後にかけ直す（行の増減で範囲がずれるため）
    ws.data_validations.dataValidation = []
    if num != 2:
        for row in ws.iter_rows():
            for cell in row:
                if cell.comment:
                    cell.comment = None

    # --- 見出しの章番号 ---
    _put(ws, ROW_HEAD, 2, "%d. %s" % (num, name))

    # --- 2.1 画面レイアウト ---
    _put(ws, ROW_H21, 3, "%d.1. 画面レイアウト" % num)
    cursor = LAYOUT_FIRST
    placements = []
    layout_breaks = []  # 2枚目以降の画像は、新しいページから始める
    image_max_w = sum(
        int((256 * _column_width(ws, c) + int(128 / MAX_DIGIT_PX)) / 256 * MAX_DIGIT_PX)
        for c in range(IMAGE_COL, IMAGE_LAST_COL + 1)
    )
    layouts = sc.get("layouts") or []
    captions = []  # (行, 見出し)
    for k, lay in enumerate(layouts):
        if k > 0:
            layout_breaks.append(cursor - 1)
        if lay.get("caption"):
            captions.append((cursor, lay["caption"]))
            cursor += 1
        img = lay.get("image")
        if not img:
            warn.append(
                "[%s] 2.1 画面レイアウト %d番目の画像が指定されていません。「画像未添付」の文字を入れました。画像を用意して、定義にパスを足し、組み立て直してください。"
                % (name, k + 1)
            )
            captions.append((cursor, PLACEHOLDER_TEXT))
            cursor += 2
            continue
        path = str(Path(base_dir) / img)
        with PILImage.open(path) as im:
            w, h = im.size
        scale = min(1.0, image_max_w / w, IMAGE_MAX_H / h)
        pw, ph = int(w * scale), int(h * scale)
        rows = math.ceil(ph / ROW_PX)
        placements.append(
            {
                "path": path,
                "row": cursor,
                "col": IMAGE_COL,
                "cx": pw * EMU_PER_PIXEL,
                "cy": ph * EMU_PER_PIXEL,
                "name": "画面レイアウト %s" % sc["id"],
            }
        )
        cursor += rows + 1
    if not layouts:
        warn.append(
            "[%s] 2.1 画面レイアウトが指定されていません。「画像未添付」の文字を入れました。画像を用意して、定義の layouts にパスを足し、組み立て直してください。"
            % name
        )
        captions.append((LAYOUT_FIRST, PLACEHOLDER_TEXT))
    # 枠（8〜41行目）に収まらないときは、先に行を足してから見出しを書く（足す位置より下の値がずれるため）
    extra = max(0, (cursor - 1) - LAYOUT_LAST)
    if extra:
        insert_rows_keep_layout(
            ws, LAYOUT_LAST + 1, extra, LAYOUT_LAST, max_col=MAX_COL
        )
        off += extra
    for row, text in captions:
        _put_text(ws, row, IMAGE_COL, text)
    brk1 = PAGE_BREAK_ROWS[0] + off
    for p in placements:
        to = _end_cell(ws, p["row"], p["col"], p["cx"], p["cy"])
        ctx["pictures"].append(dict(p, sheet=ws.title, to=to))

    # --- 2.2 一覧表示 ---
    _put(ws, ROW_H22 + off, 3, "%d.2. 一覧表示" % num)
    areas = sc["list_areas"] or [{"name": "-", "paging": "-", "sort": "-", "note": "-"}]
    first = LIST_FIRST + off
    delta = _resize_rows(ws, first, LIST_LAST - LIST_FIRST + 1, len(areas))
    for i, a in enumerate(areas):
        r = first + i
        _stamp_block(ws, r, tpl.list_row)
        _put(ws, r, _col(LIST_COLS["no"]), i + 1)
        for key in ("name", "paging", "sort", "note"):
            _put(ws, r, _col(LIST_COLS[key]), _dash(a.get(key)))
        if a.get("changed"):
            _mark(red, ws, r, [_col(c) for c in LIST_COLS.values()])
    fits.append((first, first + len(areas) - 1, False))
    dvr = {"paging": ["N%d:P%d" % (first, first + len(areas) - 1)]}
    off += delta

    # --- 2.3 画面項目定義 ---
    _put(ws, ROW_H23 + off, 3, "%d.3. 画面項目定義" % num)
    plan = []
    no = 0
    for reg in sc["regions"]:
        plan.append(("region", reg))
        for it in reg["items"]:
            if not it.get("cont"):
                no += 1
            plan.append(("item", it, no))
    first = ITEM_BLOCK_FIRST + off
    have = ITEM_BLOCK_LAST - ITEM_BLOCK_FIRST + 1
    delta = _resize_rows(ws, first, have, len(plan))
    item_rows = []
    for i, p in enumerate(plan):
        r = first + i
        if p[0] == "region":
            _stamp_block(ws, r, tpl.region_row)
            _put(ws, r, _col(ITEM_COLS["no"]), "領域名：%s" % p[1]["name"])
            _put(ws, r, _col(ITEM_COLS["phys"]), "-")
        else:
            it, n = p[1], p[2]
            _stamp_block(ws, r, tpl.item_row)
            if not it.get("cont"):
                _put(ws, r, _col(ITEM_COLS["no"]), n)
            _put(
                ws,
                r,
                _col(ITEM_COLS["name"]),
                (
                    _dash(it.get("name"))
                    if not it.get("cont")
                    else (it.get("name") or None)
                ),
            )
            _put(ws, r, _col(ITEM_COLS["type"]), it["type"])
            _put(ws, r, _col(ITEM_COLS["source"]), _dash(it.get("source")))
            _put(ws, r, _col(ITEM_COLS["edit"]), _dash(it.get("edit")))
            _put(ws, r, _col(ITEM_COLS["initial"]), _dash(it.get("initial")))
            _put(ws, r, _col(ITEM_COLS["required"]), _circle(it.get("required")))
            _put(ws, r, _col(ITEM_COLS["domain"]), _dash(it.get("domain")))
            _put(ws, r, _col(ITEM_COLS["phys"]), _dash(it.get("phys")))
            item_rows.append(r)
            if it.get("changed"):
                _mark(red, ws, r, [_col(c) for c in ITEM_COLS.values()])
    fits.append((first, first + len(plan) - 1, False))
    dvr["item_type"] = ["J%d" % r for r in item_rows]
    dvr["circle"] = ["AD%d" % r for r in item_rows]
    off += delta
    brk2 = PAGE_BREAK_ROWS[1] + off

    # --- 2.4 入出力一覧 ---
    _put(ws, ROW_H24 + off, 3, "%d.4. 入出力一覧" % num)
    ios = sc["io"] or [{"name": "-", "kind": "-", "io": "-"}]
    first = IO_FIRST + off
    delta = _resize_rows(ws, first, IO_LAST - IO_FIRST + 1, len(ios))
    for i, o in enumerate(ios):
        r = first + i
        _stamp_block(ws, r, tpl.io_row)
        _put(ws, r, _col(IO_COLS["no"]), i + 1)
        _put(ws, r, _col(IO_COLS["name"]), o["name"])
        _put(ws, r, _col(IO_COLS["kind"]), o["kind"])
        _put(ws, r, _col(IO_COLS["io"]), o["io"])
        for key in ("c", "r", "u", "d", "lock"):
            _put(ws, r, _col(IO_COLS[key]), _circle(o.get(key)))
        _put(ws, r, _col(IO_COLS["note"]), _dash(o.get("note")))
        if o.get("changed"):
            _mark(red, ws, r, [_col(c) for c in IO_COLS.values()])
    fits.append((first, first + len(ios) - 1, False))
    dvr["io_kind"] = ["K%d:N%d" % (first, first + len(ios) - 1)]
    dvr["io_dir"] = ["O%d:O%d" % (first, first + len(ios) - 1)]
    dvr["circle"] += ["P%d:U%d" % (first, first + len(ios) - 1)]
    off += delta

    # --- 2.5 画面イベント一覧 ---
    _put(ws, ROW_H25 + off, 3, "%d.5. 画面イベント一覧" % num)
    events = sc["events"]
    first = EV_FIRST + off
    delta = _resize_rows(ws, first, EV_LAST - EV_FIRST + 1, len(events))
    server_allowed = ctx["server_values"]
    for i, e in enumerate(events):
        r = first + i
        _stamp_block(ws, r, tpl.ev_row)
        _put(ws, r, _col(EV_COLS["no"]), i + 1)
        for key in ("name", "timing", "summary", "next", "server"):
            _put(ws, r, _col(EV_COLS[key]), e[key])
        if e["server"] not in server_allowed:
            warn.append(
                "[%s] 画面イベント一覧 %d行目（%s）: サーバ通信有無「%s」は選択肢 %s にありません。"
                % (name, i + 1, e["name"], e["server"], server_allowed)
            )
        if e.get("changed"):
            _mark(red, ws, r, [_col(c) for c in EV_COLS.values()])
    fits.append((first, first + len(events) - 1, False))
    dvr["server"] = ["AE%d:AH%d" % (first, first + len(events) - 1)]
    off += delta
    brk3 = PAGE_BREAK_ROWS[2] + off

    # --- 2.6 画面イベント詳細 ---
    _put(ws, ROW_H26 + off, 3, "%d.6. 画面イベント詳細" % num)
    plan = []  # (行数, 書き込む関数)
    ctx["detail_fit_ranges"] = []
    for k, e in enumerate(events):
        title = e["name"] if e["name"].endswith("イベント") else e["name"] + "イベント"
        plan.append((1, _writer_title("%d.6.%d. %s" % (num, k + 1, title))))
        plan.append((1, None))
        blocks = e.get("detail") or [{"text": "-", "indent": 1}]
        for b in blocks:
            plan.append(_plan_detail_block(ws, b, tpl))
        plan.append((1, None))
        plan.append((1, None))
    total = sum(n for n, _ in plan)
    first = DETAIL_FIRST + off
    have = DETAIL_LAST - DETAIL_FIRST + 1
    delta = _resize_rows(ws, first, have, total)
    # 自由記述の領域を、いったん空の行の書式にそろえる
    for i in range(total):
        _stamp_block(ws, first + i, tpl.free_row)
    r = first
    for n, writer in plan:
        if writer:
            writer(ws, r, ctx)
        r += n
    # 表の行の高さの範囲。plan の writer が、行番号を詰めて返す
    for lo, hi in ctx["detail_fit_ranges"]:
        fits.append((lo, hi, True))
    off += delta
    detail_end = first + total - 1

    # --- 画面引継ぎ項目（内部設計情報） ---
    hand_plan = []  # (種類, 値)
    for k, e in enumerate(events):
        title = e["name"] if e["name"].endswith("イベント") else e["name"] + "イベント"
        hand_plan.append(("head", "（%d） %s" % (k + 1, title)))
        hand_plan.append(("blank", None))
        hand_plan.append(("hdr", None))
        groups = e.get("handover") or [
            {"group": "-", "prefix": "-", "items": [{"name": "-"}]}
        ]
        for g in groups:
            hand_plan.append(("group", g))
            items = g["items"] or [{"name": "-"}]
            for n, it in enumerate(items):
                hand_plan.append(
                    ("item", (it, n + 1, e.get("changed") or it.get("changed")))
                )
        hand_plan.append(("blank", None))
    nrows = sum(2 if kind == "hdr" else 1 for kind, _ in hand_plan)
    first = HAND_BLOCK_FIRST + off
    have = HAND_BLOCK_LAST - HAND_BLOCK_FIRST + 1
    _clear_block_values(ws, first, first + have - 1)
    _resize_rows(ws, first, have, nrows)
    r = first
    hand_fit_rows = []
    for kind, val in hand_plan:
        if kind == "head":
            _stamp_block(ws, r, tpl.hand_head)
            _put(ws, r, 2, val)
            r += 1
        elif kind == "blank":
            _stamp_block(ws, r, tpl.hand_blank)
            r += 1
        elif kind == "hdr":
            _stamp_block(ws, r, tpl.hand_hdr, keep_values=True)
            r += 2
        elif kind == "group":
            _stamp_block(ws, r, tpl.hand_group)
            _put(ws, r, 3, "項目グループ：%s" % val["group"])
            _put(ws, r, 12, "プレフィックス：%s" % _dash(val.get("prefix")))
            r += 1
        else:
            it, n, ch = val
            _stamp_block(ws, r, tpl.hand_item)
            _put(ws, r, _col(HAND_ITEM_COLS["no"]), n)
            for key in ("name", "store", "value", "desc", "note"):
                _put(ws, r, _col(HAND_ITEM_COLS[key]), _dash(it.get(key)))
            if ch:
                _mark(red, ws, r, [_col(c) for c in HAND_ITEM_COLS.values()])
            hand_fit_rows.append(r)
            r += 1
    # 項目の行だけを対象にする（間にある見出しの行は、結合されていない細いセルのため数えない）
    for r in hand_fit_rows:
        fits.append((r, r, False))

    # --- 印刷範囲・改ページ ---
    ws.print_area = "A1:%s%d" % (PRINT_LAST_COL, detail_end)
    ws.row_breaks = RowBreak()
    for b in sorted(layout_breaks + [brk1, brk2, brk3]):
        ws.row_breaks.append(Break(id=b))

    # --- 入力規則 ---
    def add_dv(kind, ranges):
        dv = DataValidation(
            type="list",
            formula1=tpl.dvs[kind],
            allow_blank=True,
            showErrorMessage=True,
            showInputMessage=True,
        )
        for rg in ranges:
            dv.add(rg)
        ws.add_data_validation(dv)

    for kind in DV_KINDS:
        add_dv(kind, dvr[kind])
    server_dv = DataValidation(
        type="list",
        formula1=ctx["server_formula"],
        allow_blank=True,
        showErrorMessage=True,
        showInputMessage=True,
    )
    for rg in dvr["server"]:
        server_dv.add(rg)
    ws.add_data_validation(server_dv)

    # プルダウンの選択肢に無い値を警告する（書き込みは止めない）
    for kind, cells in (("item_type", item_rows),):
        allowed = _dv_allowed(wb, tpl.dvs[kind])
        for r in item_rows:
            v = ws.cell(row=r, column=_col(ITEM_COLS["type"])).value
            if v not in allowed:
                warn.append(
                    "[%s] 画面項目定義 J%d: 画面項目種別「%s」は選択肢 %s にありません。"
                    % (name, r, v, allowed)
                )
    _check_dropdown(wb, ws, tpl, dvr, warn, name)

    ctx["fits"][ws.title] = fits
    ctx["sheet_info"][ws.title] = {"print_end": detail_end}
    return ws


def _check_dropdown(wb, ws, tpl, dvr, warn, name):
    """2.2・2.4 のプルダウンの選択肢に無い値を警告する。"""

    def cells(ranges):
        for rg in ranges:
            for row in ws[rg] if ":" in rg else [[ws[rg]]]:
                for c in row:
                    yield c

    for kind, label in (
        ("paging", "一覧表示 ページング有無"),
        ("io_kind", "入出力一覧 種別"),
        ("io_dir", "入出力一覧 I/O"),
        ("circle", "○/-の欄"),
    ):
        allowed = _dv_allowed(wb, tpl.dvs[kind])
        for c in cells(dvr[kind]):
            v = c.value
            if isinstance(c, MergedCell):
                continue
            # 「-」は、該当しないことを表す書き方として許す
            if v not in (None, "", "-") and str(v) not in allowed:
                warn.append(
                    "[%s] %s %s: 「%s」は選択肢 %s にありません。"
                    % (name, label, c.coordinate, v, allowed)
                )


# --- 画面イベント詳細の部品 ---------------------------------------------------
def _writer_title(text):
    """イベント見出し（D列）を書く関数を返す。"""

    def write(ws, row, ctx):
        _put_text(ws, row, 4, text)

    return write


def _plan_detail_block(ws, b, tpl):
    """イベント詳細の1ブロック（見出し・文・表）の、(行数, 書き込む関数) を返す。"""
    if "table" in b:
        return _plan_table(ws, b, tpl)
    kind = next(k for k in ("h1", "h2", "h3", "text") if k in b)
    col = (
        H_LEVEL_COL[kind]
        if kind != "text"
        else 5 + b.get("indent", DEFAULT_TEXT_INDENT)
    )
    cap = _capacity(ws, col, _col(TEXT_LAST_COL))
    lines = _split_lines(b[kind], cap)
    changed = b.get("changed")

    def write(ws_, row, ctx):
        for i, ln in enumerate(lines):
            _put_text(ws_, row + i, col, ln)
            if changed:
                _mark(ctx["red"], ws_, row + i, [col])

    return len(lines), write


def _plan_table(ws, b, tpl):
    """自由記述の表。見出し1行＋データ行。書式は 2.4 入出力一覧から借りる。"""
    t = b["table"]
    cols = _table_columns(t)
    indent = t.get("indent", DEFAULT_TEXT_INDENT)
    rows = t.get("rows") or [["-"] * len(cols)]
    first_col = 5 + indent
    spans = []
    c = first_col
    for title, span in cols:
        spans.append((c, c + span - 1))
        c += span
    changed = b.get("changed")

    def write(ws_, row, ctx):
        def draw(r, values, style_for):
            for (lo, hi), v, st in zip(spans, values, style_for):
                for cc in range(lo, hi + 1):
                    ws_.cell(row=r, column=cc)._style = copy(st)
                if hi > lo:
                    ws_.merge_cells(
                        start_row=r, start_column=lo, end_row=r, end_column=hi
                    )
                _put(ws_, r, lo, v)

        draw(row, [c[0] for c in cols], [tpl.tbl_head] * len(cols))
        for i, vals in enumerate(rows):
            styles = [tpl.tbl_data] * len(cols)
            if cols[0][0] == "No.":
                styles[0] = tpl.tbl_no
            draw(
                row + 1 + i,
                [_dash(v) if not isinstance(v, (int, float)) else v for v in vals],
                styles,
            )
            if changed:
                _mark(ctx["red"], ws_, row + 1 + i, [lo for lo, _ in spans])
        ctx.setdefault("detail_fit_ranges", []).append((row, row + len(rows)))

    return 1 + len(rows) + 1, write


# ---------------------------------------------------------------------------
# 目次・表紙・変更履歴
# ---------------------------------------------------------------------------
TOC_FIRST_BLOCK = 10  # 最初の画面の見出し行（B10）
TOC_BLOCK_ROWS = 8  # 画面1つ分の行数（見出し1＋節6＋空き1）
TOC_SECTIONS = [
    "画面レイアウト",
    "一覧表示",
    "画面項目定義",
    "入出力一覧",
    "画面イベント一覧",
    "画面イベント詳細",
]


def _build_toc(wb, screens):
    """目次を、画面のシート名・章番号に同期する。"""
    ws = wb[TOC_SHEET]
    blk = _capture_block(ws, TOC_FIRST_BLOCK, TOC_FIRST_BLOCK + TOC_BLOCK_ROWS - 2)
    last = TOC_FIRST_BLOCK
    for k, sc in enumerate(screens):
        num = k + 2
        top = TOC_FIRST_BLOCK + TOC_BLOCK_ROWS * k
        if k > 0:
            _stamp_block(ws, top, blk)
        _put(ws, top, 2, "%d. %s(%s)" % (num, sc["id"], sc["name"]))
        for j, label in enumerate(TOC_SECTIONS):
            _put(ws, top + 1 + j, 3, "%d.%d. %s" % (num, j + 1, label))
        last = top + len(TOC_SECTIONS)
    area = CellRange(ws.print_area.split("!")[-1].replace("$", ""))
    area.max_row = max(area.max_row, last + 2)
    ws.print_area = area.coord


def _history_rows(h):
    """変更履歴に書く行を返す（省略時は新規作成の1行）。"""
    rows = h.get("history") or [
        {
            "version": h.get("version", "第1.0版"),
            "date": h["date"],
            "kind": "新規",
            "where": "-",
            "what": "新規作成",
            "author": h["author"],
        }
    ]
    out = []
    for r in rows:

        def lines(v):
            return "\n".join(v) if isinstance(v, list) else v

        out.append(dict(r, where=lines(r["where"]), what=lines(r["what"])))
    return out


def _common_mapping(d):
    """表紙・変更履歴へ書く内容（apply_mapping.py のマッピング形式）。"""
    h = d["header"]
    hist = _history_rows(h)
    if len(hist) > HISTORY_LAST_ROW - HISTORY_FIRST_ROW + 1:
        raise DefinitionError(
            "変更履歴は %d 行までです。" % (HISTORY_LAST_ROW - HISTORY_FIRST_ROW + 1)
        )
    history = {
        "E1": h["pj"],
        "E2": h["system"],
        "E3": h["subsystem"],
        "S1": "%s\n\n%s/%s" % (PRODUCT_NAME, d["tx_id"], d["tx_name"]),
    }
    for i, r in enumerate(hist):
        row = HISTORY_FIRST_ROW + i
        history.update(
            {
                "A%d" % row: i + 1,
                "B%d" % row: r["version"],
                "D%d" % row: r["date"],
                "G%d" % row: r["kind"],
                "J%d" % row: r["where"],
                "Q%d" % row: r["what"],
                "AF%d" % row: r["author"],
            }
        )
    return {
        "sheets": {
            HISTORY_SHEET: history,
            COVER_SHEET: {
                "J12": h["pj"],
                "J16": h["subsystem"],
                "J19": h.get("version", hist[-1]["version"]),
                "J28": h["company"],
                "J30": h["dept"],
            },
        }
    }


# ---------------------------------------------------------------------------
# 画像（drawing の XML へ直接書き足す）
# ---------------------------------------------------------------------------
def insert_pictures(xlsx_path, output_path, placements):
    """画像を、シートの drawing へ書き足す。

    drawing の無いシートには、drawing のパーツ・関係・<drawing>要素を新しく作る。
    既存の図形があるシートでは、その drawing へ書き足す（図形を壊さない）。
    位置は twoCellAnchor（左上・右下をセルで指定。印刷の倍率に合わせて画像も縮む）で書く。

    Args:
        placements: [{"sheet", "path", "row", "col", "cx", "cy", "to", "name"}]。row・col は1始まり、cx・cy は EMU。
            to は (終了の列, 列内のずれ, 終了の行, 行内のずれ)で、_end_cell() が求める。
    """
    with zipfile.ZipFile(xlsx_path) as zin:
        names = zin.namelist()
        sheet_map = _sheet_name_to_target(zin)
        files = {}  # 書き換える・足すファイル
        content_types = zin.read("[Content_Types].xml").decode("utf-8")
        media_nums = [
            int(m.group(1))
            for n in names
            for m in [re.match(r"xl/media/image(\d+)\.\w+$", n)]
            if m
        ]
        next_media = max(media_nums, default=0) + 1
        drawing_nums = [
            int(m.group(1))
            for n in names
            for m in [re.match(r"xl/drawings/drawing(\d+)\.xml$", n)]
            if m
        ]
        next_drawing = max(drawing_nums, default=0) + 1

        def read(path):
            return files[path] if path in files else zin.read(path)

        for sheet_name in dict.fromkeys(p["sheet"] for p in placements):
            target = sheet_map[sheet_name]
            sheet_dir, sheet_file = target.rsplit("/", 1)
            rels_path = "%s/_rels/%s.rels" % (sheet_dir, sheet_file)
            sheet_xml = read(target).decode("utf-8")
            drawing_path = (
                _find_drawing_for_sheet(zin, target)
                if sheet_name not in files
                else None
            )
            if drawing_path is None:
                # 図形の無いシートに、drawing を新しく作る
                drawing_path = "xl/drawings/drawing%d.xml" % next_drawing
                next_drawing += 1
                files[drawing_path] = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
                    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"></xdr:wsDr>'
                ).encode("utf-8")
                rels_xml = (
                    read(rels_path).decode("utf-8")
                    if rels_path in names or rels_path in files
                    else '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
                )
                rids = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels_xml)]
                rid = "rId%d" % (max(rids, default=0) + 1)
                rels_xml = rels_xml.replace(
                    "</Relationships>",
                    '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                    'Target="../drawings/%s"/></Relationships>'
                    % (rid, drawing_path.rsplit("/", 1)[1]),
                )
                files[rels_path] = rels_xml.encode("utf-8")
                content_types = content_types.replace(
                    "</Types>",
                    '<Override PartName="/%s" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>'
                    % drawing_path,
                )
                if "xmlns:r=" not in sheet_xml.split(">", 1)[0]:
                    sheet_xml = sheet_xml.replace(
                        "<worksheet ", '<worksheet xmlns:r="%s" ' % NS_R, 1
                    )
                el = '<drawing r:id="%s"/>' % rid
                if "<legacyDrawing" in sheet_xml:
                    sheet_xml = sheet_xml.replace(
                        "<legacyDrawing", el + "<legacyDrawing", 1
                    )
                elif "<tableParts" in sheet_xml:
                    sheet_xml = sheet_xml.replace("<tableParts", el + "<tableParts", 1)
                elif "<extLst>" in sheet_xml:
                    sheet_xml = sheet_xml.replace("<extLst>", el + "<extLst>", 1)
                else:
                    sheet_xml = sheet_xml.replace("</worksheet>", el + "</worksheet>")
                files[target] = sheet_xml.encode("utf-8")
            else:
                if "xmlns:r=" not in sheet_xml.split(">", 1)[0]:
                    pass
            drawing_xml = read(drawing_path).decode("utf-8")
            d_dir, d_file = drawing_path.rsplit("/", 1)
            d_rels_path = "%s/_rels/%s.rels" % (d_dir, d_file)
            d_rels = (
                read(d_rels_path).decode("utf-8")
                if d_rels_path in names or d_rels_path in files
                else '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
            )
            for p in [p for p in placements if p["sheet"] == sheet_name]:
                media = "image%d.png" % next_media
                next_media += 1
                files["xl/media/%s" % media] = Path(p["path"]).read_bytes()
                rids = [int(x) for x in re.findall(r'Id="rId(\d+)"', d_rels)]
                rid = "rId%d" % (max(rids, default=0) + 1)
                d_rels = d_rels.replace(
                    "</Relationships>",
                    '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                    'Target="../media/%s"/></Relationships>' % (rid, media),
                )
                ids = [
                    int(x) for x in re.findall(r'<xdr:cNvPr id="(\d+)"', drawing_xml)
                ]
                shape_id = max(ids, default=1) + 1
                tc, tco, tr, tro = p["to"]
                pic = (
                    '<xdr:twoCellAnchor editAs="oneCell"><xdr:from><xdr:col>%d</xdr:col><xdr:colOff>0</xdr:colOff>'
                    "<xdr:row>%d</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>"
                    "<xdr:to><xdr:col>%d</xdr:col><xdr:colOff>%d</xdr:colOff>"
                    "<xdr:row>%d</xdr:row><xdr:rowOff>%d</xdr:rowOff></xdr:to>"
                    '<xdr:pic><xdr:nvPicPr><xdr:cNvPr id="%d" name="%s"/>'
                    '<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr></xdr:nvPicPr>'
                    '<xdr:blipFill><a:blip xmlns:r="%s" r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
                    '<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
                    '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr></xdr:pic><xdr:clientData/></xdr:twoCellAnchor>'
                    % (
                        p["col"] - 1,
                        p["row"] - 1,
                        tc,
                        tco,
                        tr,
                        tro,
                        shape_id,
                        p["name"],
                        NS_R,
                        rid,
                        p["cx"],
                        p["cy"],
                    )
                )
                drawing_xml = drawing_xml.replace("</xdr:wsDr>", pic + "</xdr:wsDr>")
            files[drawing_path] = drawing_xml.encode("utf-8")
            files[d_rels_path] = d_rels.encode("utf-8")
        if 'Extension="png"' not in content_types:
            content_types = content_types.replace(
                "</Types>", '<Default Extension="png" ContentType="image/png"/></Types>'
            )
        files["[Content_Types].xml"] = content_types.encode("utf-8")
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            written = set()
            for item in zin.infolist():
                zout.writestr(item, files.get(item.filename, zin.read(item.filename)))
                written.add(item.filename)
            for path, data in files.items():
                if path not in written:
                    zout.writestr(path, data)


# ---------------------------------------------------------------------------
# 全体
# ---------------------------------------------------------------------------
def build(template, definition_path, output):
    """定義JSONからシステム機能設計書(画面)を組み立てる。

    Returns:
        dict: 警告・赤字にしたセル数など。
    """
    base_dir = os.path.dirname(os.path.abspath(definition_path))
    d = json.load(open(definition_path, encoding="utf-8"))
    errs = _validate(d, base_dir)
    if errs:
        raise DefinitionError("\n".join(errs))

    tmp_dir = tempfile.mkdtemp(prefix="screen_fd_")
    work1 = os.path.join(tmp_dir, "w1.xlsx")
    work2 = os.path.join(tmp_dir, "w2.xlsx")
    work3 = os.path.join(tmp_dir, "w3.xlsx")
    work4 = os.path.join(tmp_dir, "w4.xlsx")
    report = {"warnings": []}
    try:
        wb = openpyxl.load_workbook(template)
        ws_tpl = wb[SCREEN_TEMPLATE_SHEET]
        tpl = _Template(ws_tpl)

        # サーバ通信有無の選択肢は、データシートの見出しから探す
        data = wb[DATA_SHEET]
        server_values, server_formula = None, None
        for c in data[1]:
            if c.value == "サーバ通信有無":
                letter = get_column_letter(c.column)
                vals = []
                r = 2
                while data.cell(row=r, column=c.column).value:
                    vals.append(data.cell(row=r, column=c.column).value)
                    r += 1
                server_values = vals
                server_formula = "データ!$%s$2:$%s$%d" % (letter, letter, 1 + len(vals))
        if server_values is None:
            raise AssertionError("データシートに「サーバ通信有無」の列がありません。")

        ctx = {
            "warnings": report["warnings"],
            "red": [],
            "pictures": [],
            "fits": {},
            "dv_ranges": {},
            "sheet_info": {},
            "server_values": server_values,
            "server_formula": server_formula,
        }

        # 画面の数だけ、ひな形の状態のシートを複製する（編集の前に）
        screens = d["screens"]
        sheets = [ws_tpl]
        for _ in screens[1:]:
            c = wb.copy_worksheet(ws_tpl)
            _copy_sheet_extras(ws_tpl, c)
            sheets.append(c)

        _build_overview(wb, d, report)

        names = [_sheet_name(i + 2, sc) for i, sc in enumerate(screens)]
        for name in names:
            if names.count(name) > 1:
                raise DefinitionError("シート名「%s」が重複しています。" % name)
        for ws, name in zip(sheets, names):
            ws.title = name
        # シートの並び: 複製は「データ」の前へ
        for ws in sheets[1:]:
            wb.move_sheet(
                ws,
                offset=wb.sheetnames.index(DATA_SHEET) - wb.sheetnames.index(ws.title),
            )

        for i, (ws, sc) in enumerate(zip(sheets, screens)):
            _build_screen(wb, ws, i + 2, sc, tpl, base_dir, ctx)

        _build_toc(wb, screens)

        # 変更履歴の成果物名の欄は、改行を表示するために折り返す
        hs = wb[HISTORY_SHEET]
        al = copy(hs["S1"].alignment)
        al.wrap_text = True
        hs["S1"].alignment = al

        # 行の高さを合わせる（結合セルの長文が隠れないように）
        for title, ranges in ctx["fits"].items():
            for lo, hi, only_merged in ranges:
                fit_sheet(wb[title], [(lo, hi)], only_merged=only_merged)
        # 変更箇所を赤字にする
        for title, coord in ctx["red"]:
            mark_font_red(wb[title], coord)

        save_with_shapes(wb, template, work1)
        normalize_history(work1, work2)

        # 表紙・変更履歴（apply_mapping.py の書き込み）
        rep = apply_mapping(work2, _common_mapping(d), work3, allow_outside_border=True)
        if rep["errors"]:
            raise DefinitionError("\n".join(rep["errors"]))
        # 日付の型変換は、意図した動作のため警告に含めない
        report["warnings"].extend(w for w in rep["warnings"] if "日付型に変換" not in w)

        wb3 = openpyxl.load_workbook(work3)
        fit_history_rows(wb3[HISTORY_SHEET])
        save_with_shapes(wb3, work3, work4)

        # 画像は、最後に書き足す（以降は openpyxl で開き直さない）
        if ctx["pictures"]:
            insert_pictures(work4, output, ctx["pictures"])
        else:
            shutil.copyfile(work4, output)
        report["pictures"] = len(ctx["pictures"])
        report["red_cells"] = len(ctx["red"])
        report["sheets"] = names
        return report
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    ensure_utf8_stdio()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("template")
    ap.add_argument("definition")
    ap.add_argument("output")
    a = ap.parse_args()
    try:
        report = build(a.template, a.definition, a.output)
    except DefinitionError as e:
        print("NG: 定義に誤りがあります。出力は作っていません。")
        print(str(e))
        sys.exit(1)
    print("created:", a.output)
    print("シート:", report["sheets"])
    print(
        "貼った画像: %d 枚 / 赤字にしたセル: %d"
        % (report["pictures"], report["red_cells"])
    )
    if report["warnings"]:
        print("警告 %d 件:" % len(report["warnings"]))
        for w in report["warnings"]:
            print("  !", w)


if __name__ == "__main__":
    main()
