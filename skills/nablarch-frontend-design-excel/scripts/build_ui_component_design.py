# -*- coding: utf-8 -*-
# Revision History
# 2026/11/10: Created the builder for the "画面共通部品設計書" template.
#   - 記入例の名前と分類をプロジェクトに依存しない内容に変更。
"""
画面共通部品設計書のテンプレート（Nablarch の書式）を作る。

【目的】
Nablarch の「共通コンポーネント設計書」は、バックエンドのクラス（メソッド、CRUD、エラー）向けの様式で、
画面の共通部品（表示の例、状態、公開する関数）を書くには合わない。
そこで、表紙・変更履歴・ヘッダー帯・フォント・罫線・配色・ページ設定は、Nablarch の共通コンポーネント設計書から引き継ぎ、
本体のシートだけを、次の7シートに差し替える。

    1. 概要 / 2. 画面レイアウト / 3. 状態 / 4. 入力属性 / 5. オブジェクト定義 / 6. 関数定義 / 7. 関数詳細

「目次」シートは作らない（Nablarch の単体テスト仕様書にも、目次シートが無いため）。
1ファイルが1つの共通部品であるため、目次は不要である。

【使い方】
    python -X utf8 build_ui_component_design.py <出力xlsx> [--example | --content <定義json>]

    （指定なし）  : 見出しだけの空のテンプレートを作る。
    --example     : 架空のボタンを題材にした記入例を入れる（見た目の確認用）。
    --content     : 定義 JSON の内容を入れて、1つの共通部品の設計書を作る。
                    JSON の形は、`_example()` の戻り値と同じ（`references/記入要領_画面共通部品設計書.md` に説明がある）。
                    表の行数と、関数詳細のブロックの数は、JSON の内容に合わせて増減する。

土台のテンプレートは、`assets/templates/フォーマット/` の共通コンポーネント設計書を使う。
"""

import argparse
import datetime
import json
import math
import sys
import unicodedata
from pathlib import Path

import openpyxl
from openpyxl.worksheet.pagebreak import Break
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import Color
from openpyxl.worksheet.properties import PageSetupProperties

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio, save_with_shapes  # noqa: E402
from fit_change_history_rows import fit_rows as fit_history_rows  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
# 書式の土台にする、Nablarch の共通コンポーネント設計書（このスキルのフォーマット）
BASE_TEMPLATE = (
    SKILL_DIR
    / "assets"
    / "templates"
    / "フォーマット"
    / "共通コンポーネント設計書_(共通コンポーネントID)_(共通コンポーネント名).xlsx"
)
# 成果物名（表紙 J14 と、変更履歴 S1）
DELIVERABLE_NAME = "画面共通部品設計書"
# 土台から取り除く、目次と本体のシートの名前
BASE_BODY_SHEET = "1.  コンポーネント名 "
BASE_TOC_SHEET = "目次"
# 本体のシート（左から順）
SHEET_NAMES = ["1. 概要", "2. 画面レイアウト", "3. 状態", "4. 入力属性", "5. オブジェクト定義", "6. 関数定義", "7. 関数詳細"]

# 方眼紙の範囲。A列は余白。
# 各シートの表の列は、B（2列目）から AH（34列目）の座標で定義し、書くときに、1列右（C から AI）へずらす。
# 節の見出しだけをB列に置き、内容をC列以降にすることで、見出しを選んだ状態で Ctrl＋↑↓ を押すと、
# 見出しだけを順に移動できる（B列の見出しの間が、空のセルになるため）
COL_FIRST = 2
COL_LAST = 34
CONTENT_SHIFT = 1
LAST_COLUMN_LETTER = "AI"
# 1行の高さ（9pt）
LINE_HEIGHT = 12.0
# 方眼紙1セルに入る全角文字の数の目安（列幅 4.83）
FULLWIDTH_CHARS_PER_CELL = 1.9

# 書き方のコメント（列タイトル、ラベル、節の見出しに付ける）。シート名 → {タイトル: コメント}。
# 節の見出しは、番号を除いた文字の先頭が、キーと一致するものに付ける（キーの末尾が「*」のとき）。
# コメントは、この設計書だけで意味が分かるように書く。規約などの別の資料への参照で済ませない
COMMENTS = {
    "1. 概要": {
        "部品ID": "対象プロジェクトの規則に従って部品の識別子を書く。ファイル名の部品IDと一致させる。",
        "部品名": "部品の呼び名を書く（例：ボタン）。",
        "分類": "対象プロジェクトで定めた共通部品の分類を書く。",
        "目的": "この部品を使うと何が得られるかを、使う人の立場で書く。作る側の都合（実装を1か所にする、など）や、他の資料への参照は書かない。",
        "概要": "部品の機能を、この設計書だけで分かるように書く。「規約に従う」とだけ書かず、形、色、キーなどの具体的な内容を書く。",
        "利用条件": "この部品を使うための前提（フレームワーク、依存する部品、使う場面）を書く。",
        "対象外": "この部品が扱わないこと（画面ごとの処理など）を書く。",
        "機能ID": "F-01 の形式で、この部品の中で重複しないように採番する。",
        "機能名": "使う人から見た機能の名前を書く。",
        "内容": "その機能で何ができるかを、1〜2文で書く。",
        "利用する関数": "この機能に関係する入力属性、イベント、公開関数の名前を書く。",
        "備考": "使う人への補足があるときだけ書く。",
        "No.": "通し番号を書く。",
        "対象": "注意が当てはまる状態や条件を書く。",
        "理由・補足": "そうなる理由を書き、使う人が納得して使えるようにする。",
        "関連する状態・関数": "状態属性IDや関連する公開関数名を書く。",
        "提供機能*": "この部品で使える機能を、使う人から見た単位で、一覧にする。",
        "特記事項*": "この部品を使うときの注意（制約、例外）だけを書く。未決定の事項や課題は書かない。",
    },
    "2. 画面レイアウト": {
        "構成要素一覧*": "表示イメージに含まれる要素を、1行に1つずつ書く。",
        "レイアウト例*": "表示が異なる代表的なパターンを、1つずつ書く。見出しの「：」の後に、パターンの名前を書く。枠には、スクリーンショットなどを貼る。",
        "要素ID": "E-01 の形式で、この部品の中で重複しないように採番する。",
        "名称": "画面上の要素の名前を書く。",
        "表示内容": "その要素に表示する内容を書く。",
        "表示条件": "その要素が表示される条件を書く。常に表示するときは「常に表示」と書く。",
        "操作・イベント": "利用者の操作と、それで起きることを書く。操作がないときは「なし」と書く。",
        "関連状態": "『3. 状態』の属性IDを書く。",
        "関連関数": "関連する入力属性、イベントまたは公開関数の名前を書く。",
        "備考": "使う人への補足があるときだけ書く。",
    },
    "3. 状態": {
        "属性ID": "ST-01 の形式で採番する。同じ属性の値は、同じIDで、複数の行に書く。",
        "状態属性": "部品が持つ状態の名前を書く（例：操作可否）。",
        "値": "その属性が取る値を書く（例：enabled）。",
        "意味": "その値のときの状態を書く。",
        "表示・操作への影響": "その値のときに、表示と操作がどう変わるかを書く。",
        "関連関数": "その値にする、または、その値を読む関数のIDを書く。",
        "備考": "使う人への補足があるときだけ書く。",
        "パターンID": "P-01 の形式で採番する。",
        "状態の組合せ": "属性IDと値で、「ST-01=enabled、ST-02=指定なし」のように書く。",
        "表示イメージ": "『2. 画面レイアウト』のレイアウト例の番号または名前を書く。",
        "動作・制約": "その組合せのときの動作と制約を書く。",
        "No.": "通し番号を書く。",
        "変更前": "変わる前の状態を、「ST-01=enabled」の形式で書く。",
        "操作・条件": "状態を変える操作、関数の呼び出し、条件を書く。",
        "変更後": "変わった後の状態を、「ST-01=disabled」の形式で書く。",
        "状態属性*": "部品が持つ状態を、互いに独立した軸ごとに書く。",
        "代表的な組合せ*": "状態属性の値の組合せのうち、表示や動作が異なる代表的なものだけを書く。",
        "状態遷移*": "操作の結果が誤解されやすい箇所だけを書く。",
    },
    "4. 入力属性": {
        "属性名": "部品が受け取る入力属性の名前を書く。",
        "型": "属性が受け取る値の型を書く。",
        "必須": "省略できない属性は必須、できる属性は任意と書く。",
        "既定値": "省略時の値を書く。",
        "説明": "属性の意味や使用方法を書く。",
        "イベント名": "画面側に通知するイベントの名前を書く。",
    },
    "5. オブジェクト定義": {
        "属性名": "オブジェクトに含まれる属性の名前を書く。",
        "データ型": "属性の値の型を書く。",
        "必須": "省略できない属性は必須と書く。",
        "既定値": "省略時の値を書く。",
        "説明": "属性の意味や制約を書く。",
    },
    "6. 関数定義": {
        "関数名": "画面側が呼び出す公開関数の名前を書く。",
        "引数": "関数に渡す値の型と意味を書く。",
        "戻り値": "関数の戻り値の型と意味を書く。",
        "説明": "関数の目的と動作を書く。",
    },
    "7. 関数詳細": {
        "概要": "関数の目的を、1文で書く。",
        "引数": "各引数の型、意味、制約を書く。",
        "戻り値": "戻り値の内容を書く。",
        "事前条件": "呼び出す前に満たす必要がある条件を書く。",
        "処理仕様": "処理の順序を、①②③の形で書く。",
        "状態への影響": "変わる状態の属性IDと値を書く。ないときは「なし」と書く。",
        "エラー・例外": "起きるエラーと、その扱いを書く。ないときは「なし」と書く。",
        "M-*": "見出しは、「関数ID　関数名」の形式で書く。詳細が必要な公開関数だけを書く。",
    },
}

THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
# Nablarch の見出しの背景色（テーマ色の白を25%暗くした灰色）
GREY = PatternFill("solid", fgColor=Color(theme=0, tint=-0.249977111117893))
FONT = Font(name="ＭＳ 明朝", size=9)


def _text_width(text):
    """文字列の表示幅（全角を1、半角を0.5として数えた文字数）を返す。"""
    width = 0.0
    for ch in text:
        width += 1.0 if unicodedata.east_asian_width(ch) in ("W", "F", "A") else 0.5
    return width


def _lines_needed(text, cells):
    """結合したセル（cells個分の幅）に、文字列を折り返して入れたときの行数を返す。"""
    capacity = max(1.0, cells * FULLWIDTH_CHARS_PER_CELL)
    total = 0
    for line in str(text).split("\n"):
        total += max(1, math.ceil(_text_width(line) / capacity))
    return total


class SheetWriter:
    """方眼紙のシートへ、結合セルと罫線つきで書き込む補助。書いた行の高さも、内容に合わせて決める。"""

    def __init__(self, ws):
        self.ws = ws
        self.comments = COMMENTS.get(ws.title, {})
        # 次に書く行（1〜3行目はヘッダー帯、4行目は空き）
        self.row = 5

    def put(self, row, c1, c2, text="", *, grey=False, border=True, align="left", merge=True, wrap=True):
        """
        c1〜c2列に文字を置く。置いた文字に必要な行数を返す。
        merge=True のときは、c1〜c2列を結合する。False のときは結合せず、文字は c1 のセルだけに入れる。
        merge=False で枠線があるときは、範囲の外周だけに線を引く（セルの間には引かない）。
        """
        ws = self.ws
        if merge and c2 > c1:
            ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)
        for col in range(c1, c2 + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = FONT
            cell.alignment = Alignment(horizontal=align, vertical="top", wrap_text=wrap)
            if border and (merge or c1 == c2):
                cell.border = BORDER
            elif border:
                cell.border = Border(
                    left=THIN if col == c1 else None,
                    right=THIN if col == c2 else None,
                    top=THIN,
                    bottom=THIN,
                )
            if grey:
                cell.fill = GREY
        ws.cell(row=row, column=c1).value = text if text != "" else None
        if not wrap:
            return 1
        return _lines_needed(text, c2 - c1 + 1) if text != "" else 1

    def _comment(self, row, col, title):
        """タイトルに対応する書き方のコメントがあれば、セルに付ける。"""
        text = self.comments.get(title)
        if text is None:
            # 節の見出しは、番号を除いた文字の先頭が、末尾に「*」のあるキーと一致するものに付ける
            heading = title.split(". ", 1)[-1]
            for key, value in self.comments.items():
                if key.endswith("*") and heading.startswith(key[:-1]):
                    text = value
                    break
        if not text:
            return
        comment = Comment(text, "作成者")
        comment.width = 260
        comment.height = max(79, 18 * (math.ceil(_text_width(text) / 15) + 1))
        self.ws.cell(row=row, column=col).comment = comment

    def set_height(self, row, lines):
        """行の高さを、行数に合わせて決める。"""
        self.ws.row_dimensions[row].height = min(409, LINE_HEIGHT * max(1, lines))

    def section(self, title):
        """節の見出し（枠なし、結合なし）を、B列に1行書く。"""
        # 結合しない。右のセルが空のため、文字は右へはみ出して表示される
        self.put(self.row, COL_FIRST, COL_FIRST, title, border=False, wrap=False)
        self._comment(self.row, COL_FIRST, title)
        self.set_height(self.row, 1)
        self.row += 1

    def note(self, text):
        """枠なしの説明文を、本文の全幅で書く。"""
        lines = self.put(self.row, COL_FIRST + CONTENT_SHIFT, COL_LAST + CONTENT_SHIFT, text, border=False)
        self.set_height(self.row, lines)
        self.row += 1

    def blank(self, count=1):
        """空行を入れる。"""
        for _ in range(count):
            self.set_height(self.row, 1)
            self.row += 1

    def table(self, columns, rows, blank_rows=0, header_lines=1):
        """
        表を書く。
        columns: [(見出し, 開始列, 終了列), ...]
        rows: [[値, ...], ...] 列と同じ順で値を渡す。
        blank_rows: rows の後ろに足す、空の行の数。
        """
        lines = header_lines
        columns = [(title, c1 + CONTENT_SHIFT, c2 + CONTENT_SHIFT) for title, c1, c2 in columns]
        for title, c1, c2 in columns:
            lines = max(lines, self.put(self.row, c1, c2, title, grey=True))
            self._comment(self.row, c1, title)
        self.set_height(self.row, lines)
        self.row += 1
        for values in rows:
            lines = 1
            for (_, c1, c2), value in zip(columns, values):
                lines = max(lines, self.put(self.row, c1, c2, value))
            self.set_height(self.row, lines)
            self.row += 1
        for _ in range(blank_rows):
            for _, c1, c2 in columns:
                self.put(self.row, c1, c2, "")
            self.set_height(self.row, 1)
            self.row += 1

    def frame(self, height_rows, text=""):
        """表示イメージを貼るための、1つの大きな枠（height_rows 行分を結合）を書く。"""
        ws = self.ws
        top = self.row
        first, last = COL_FIRST + CONTENT_SHIFT, COL_LAST + CONTENT_SHIFT
        ws.merge_cells(start_row=top, start_column=first, end_row=top + height_rows - 1, end_column=last)
        for row in range(top, top + height_rows):
            self.set_height(row, 1)
            for col in range(first, last + 1):
                ws.cell(row=row, column=col).border = BORDER
        cell = ws.cell(row=top, column=first)
        cell.font = FONT
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        cell.value = text if text else None
        self.row += height_rows

    def label_rows(self, items, label_cols=(COL_FIRST, 5), value_cols=(6, COL_LAST)):
        """「ラベル（灰色）と値」の行を、項目の数だけ縦に並べる。items: [(ラベル, 値, 最低行数), ...]"""
        for label, value, min_lines in items:
            self.put(self.row, label_cols[0] + CONTENT_SHIFT, label_cols[1] + CONTENT_SHIFT, label, grey=True)
            self._comment(self.row, label_cols[0] + CONTENT_SHIFT, label)
            lines = self.put(self.row, value_cols[0] + CONTENT_SHIFT, value_cols[1] + CONTENT_SHIFT, value)
            self.set_height(self.row, max(lines, min_lines))
            self.row += 1


def _prepare_sheets(wb):
    """
    土台のテンプレートの本体シートから、ヘッダー帯（1〜3行目）だけを持つ空のシートを作り、
    目次と土台の本体シートを取り除く。作ったシートの名前の一覧を返す。
    """
    base = wb[BASE_BODY_SHEET]
    created = []
    for name in SHEET_NAMES:
        ws = wb.copy_worksheet(base)
        ws.title = name
        # 4行目より下の結合を解き、内容と行の高さを消す
        for merged in list(ws.merged_cells.ranges):
            if merged.min_row >= 4:
                ws.unmerge_cells(str(merged))
        ws.delete_rows(4, ws.max_row)
        for row in list(ws.row_dimensions.keys()):
            if row >= 4:
                del ws.row_dimensions[row]
        created.append(ws)
    # 目次と、土台の本体シートを取り除く
    del wb[BASE_TOC_SHEET]
    del wb[BASE_BODY_SHEET]
    # 並び順を、表紙、変更履歴、本体シートにする
    wb._sheets = [wb["表紙"], wb["変更履歴"]] + created
    return created


def _finish_sheet(ws, last_row):
    """印刷の設定（範囲、ページ、タイトル行、フッター）を、Nablarch の本体シートに合わせる。"""
    ws.print_area = f"A1:{LAST_COLUMN_LETTER}{last_row + 1}"
    ws.print_title_rows = "1:4"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = 9
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_options.horizontalCentered = True
    ws.oddFooter.center.text = "- &P -"
    ws.sheet_view.showGridLines = False


def _fill_overview(ws, content):
    """シート『1. 概要』。基本情報、提供機能、特記事項、設計上の留意事項を書く。"""
    w = SheetWriter(ws)
    ex = content["overview"] if content else None

    w.section("1. 基本情報")
    w.label_rows([
        ("部品ID", ex["id"] if ex else "", 1),
        ("部品名", ex["name"] if ex else "", 1),
        ("分類", ex["category"] if ex else "", 1),
        ("目的", ex["purpose"] if ex else "", 1),
        ("概要", ex["summary"] if ex else "", 3),
        ("利用条件", ex["conditions"] if ex else "", 2),
        ("対象外", ex["out_of_scope"] if ex else "", 1),
    ])
    w.blank()

    w.section("2. 提供機能")
    w.table(
        [("機能ID", 2, 4), ("機能名", 5, 11), ("内容", 12, 24), ("利用する関数", 25, 30), ("備考", 31, 34)],
        ex["features"] if ex else [],
        blank_rows=0 if ex else 5,
    )
    w.blank()

    w.section("3. 特記事項")
    w.note("この部品を使うときの注意（制約、例外）だけを書く。未決定の事項や課題は書かない。")
    w.table(
        [("No.", 2, 3), ("分類", 4, 6), ("対象", 7, 10), ("内容", 11, 22), ("理由・補足", 23, 30),
         ("関連する状態・関数", 31, 34)],
        ex["notes"] if ex else [],
        blank_rows=0 if ex else 3,
    )
    w.blank()

    w.section("4. 設計上の留意事項")
    w.note(ex["remarks"] if ex else
           "使う人が知っておくべき、この部品に固有の留意事項を書く。必要な内容は、他の資料への参照で済ませず、ここに書く。")
    w.blank()
    usage = ex.get("usage", "") if ex else ""
    # 利用例の枠が次ページへ送られる際、見出しだけが前ページに残らないようにする。
    if usage:
        ws.row_breaks.append(Break(id=w.row - 1))
    w.section("5. ページでの利用例")
    lines = w.put(w.row, COL_FIRST + CONTENT_SHIFT, COL_LAST + CONTENT_SHIFT, usage)
    w.set_height(w.row, lines)
    w.row += 1
    _finish_sheet(ws, w.row)


def _fill_layout(ws, content):
    """シート『2. 画面レイアウト』。表示パターンごとの表示イメージの枠と、構成要素の一覧を書く。"""
    w = SheetWriter(ws)
    ex = content["layout"] if content else None

    w.note("表示が異なる代表的なパターンだけを書く。画面全体のイメージは不要。"
           "表示イメージの枠に、画面のスクリーンショットまたは表示イメージを貼る。")
    w.blank()
    patterns = ex["patterns"] if ex else ["", "", ""]
    for number, pattern in enumerate(patterns, start=1):
        # 従来の文字列指定を保ち、枠の高さが必要な例だけ行数を指定する。
        if isinstance(pattern, str):
            title, height_rows = pattern, 14
        elif isinstance(pattern, dict):
            title, height_rows = pattern["title"], pattern.get("height_rows", 14)
            if not isinstance(title, str) or type(height_rows) is not int or not 14 <= height_rows <= 30:
                raise ValueError("レイアウト例のtitleは文字列、height_rowsは14〜30の整数にしてください")
        else:
            raise ValueError("レイアウト例は文字列またはtitleとheight_rowsを持つオブジェクトにしてください")
        # 前の例を途中で分割しないよう、2つ目以降は例の見出しから次のページにする。
        if number > 1:
            ws.row_breaks.append(Break(id=w.row - 1))
        w.section(f"{number}. レイアウト例：{title}")
        # 1行12pt、14〜30行の枠とし、画像の可読性が足りなければ拡張する。
        w.frame(height_rows, "（表示イメージを貼る）" if ex else "")
        w.blank()

    w.section(f"{len(patterns) + 1}. 構成要素一覧")
    w.table(
        [("要素ID", 2, 3), ("名称", 4, 7), ("表示内容", 8, 15), ("表示条件", 16, 20),
         ("操作・イベント", 21, 25), ("関連状態", 26, 28), ("関連関数", 29, 31), ("備考", 32, 34)],
        ex["elements"] if ex else [],
        blank_rows=0 if ex else 5,
    )
    _finish_sheet(ws, w.row)


def _fill_state(ws, content):
    """シート『3. 状態』。状態属性、代表的な組合せ、状態遷移を書く。"""
    w = SheetWriter(ws)
    ex = content["state"] if content else None

    w.note("部品が持つ状態を、属性ごとに定義する。画面レイアウトの表示パターンと対応づける。")
    w.blank()
    w.section("1. 状態属性（独立した軸）")
    w.table(
        [("属性ID", 2, 3), ("状態属性", 4, 8), ("値", 9, 12), ("意味", 13, 19),
         ("表示・操作への影響", 20, 26), ("関連関数", 27, 30), ("備考", 31, 34)],
        ex["attributes"] if ex else [],
        blank_rows=0 if ex else 5,
    )
    w.blank()
    w.section("2. 代表的な組合せと表示イメージの対応")
    w.table(
        [("パターンID", 2, 3), ("状態の組合せ", 4, 12), ("表示イメージ", 13, 17),
         ("動作・制約", 18, 28), ("備考", 29, 34)],
        ex["patterns"] if ex else [],
        blank_rows=0 if ex else 4,
    )
    w.blank()
    w.section("3. 状態遷移（必要な場合のみ記載）")
    w.table(
        [("No.", 2, 3), ("変更前", 4, 9), ("操作・条件", 10, 17), ("変更後", 18, 23),
         ("関連関数", 24, 27), ("備考", 28, 34)],
        ex["transitions"] if ex else [],
        blank_rows=0 if ex else 3,
    )
    w.blank()
    w.note("表示パターンは、必要な組合せだけを図示する。状態遷移は、操作の結果が誤解されやすい箇所だけを定義する。")
    _finish_sheet(ws, w.row)


def _fill_function_detail(ws, content):
    """シート『7. 関数詳細』。詳細が必要な関数ごとに説明を書く。"""
    w = SheetWriter(ws)
    ex = content["details"] if content else None
    items = ["概要", "引数", "戻り値", "事前条件", "処理仕様", "状態への影響", "エラー・例外"]

    w.note("関数定義だけでは説明が足りない関数だけを書く。")
    w.blank()
    blocks = ex if ex else []
    if not blocks:
        w.note("該当なし。")
    for block in blocks:
        # ブロックの見出し（関数IDと関数名）。他のシートの節の見出しと同じ書式にする
        w.section(block["title"])
        w.label_rows(
            [(item, block["values"].get(item, ""), 1) for item in items],
        )
        w.blank()
    _finish_sheet(ws, w.row)


def _fill_inputs(ws, content):
    """部品に渡す入力属性とイベントを分類して記載する。"""
    w = SheetWriter(ws)
    interface = content.get('interface', {}) if content else {}
    w.section('1. 部品の入力属性')
    w.table([('属性名', 2, 8), ('型', 9, 15), ('必須', 16, 19), ('既定値', 20, 24), ('説明', 25, 34)], interface.get('props', []))
    w.blank()
    w.section('2. イベント')
    w.table([('イベント名', 2, 8), ('引数', 9, 17), ('説明', 18, 34)], interface.get('events', []))
    _finish_sheet(ws, w.row)


def _fill_objects(ws, content):
    """入力属性のオブジェクトを種類ごとに一枚のシートで定義する。"""
    w = SheetWriter(ws)
    objects = content.get('objects', []) if content else []
    if not objects:
        w.section('1. オブジェクト定義')
        w.note('該当なし。')
    for index, obj in enumerate(objects, 1):
        w.section(f"{index}. {obj['name']}（入力属性：{obj['prop']}）")
        w.table([('属性名', 2, 8), ('データ型', 9, 15), ('必須', 16, 19), ('既定値', 20, 24), ('説明', 25, 34)], obj['fields'])
        w.blank()
    _finish_sheet(ws, w.row)


def _fill_public_functions(ws, content):
    """公開関数がない場合もシートを残す。"""
    w = SheetWriter(ws)
    entries = content.get('public_functions', []) if content else []
    w.section('1. 公開関数')
    if entries:
        w.table([('関数名', 2, 8), ('引数', 9, 15), ('戻り値', 16, 20), ('説明', 21, 34)], entries)
    else:
        w.note('該当なし。')
    related = content.get('related_functions', []) if content else []
    if related:
        w.blank()
        w.section('2. 利用する関連関数')
        w.table([('関数名', 2, 8), ('引数', 9, 15), ('戻り値', 16, 20), ('説明', 21, 34)], related)
    _finish_sheet(ws, w.row)


def _legacy_example():
    """架空の記入例。対象システムの仕様ではなくJSONの形の見本。"""
    return {
        # 表紙と変更履歴に入れる値。省略した項目は、書かない（会社名・部門名は、材料が無ければ空にする）
        "meta": {
            "project": "サンプルプロジェクト",
            "system": "サンプルシステム",
            "subsystem": "サンプル画面",
            "version": "第1.0版",
            "date": "2026-11-10",
            "author": "（担当者名）",
            "company": "",
            "department": "",
        },
        "overview": {
            "id": "SampleButton",
            "name": "ボタン",
            "category": "入力と操作（記入例）",
            "purpose": "ボタンの見た目と動きを、アプリ全体で統一するための共通部品として提供する。",
            "summary": "表示名と操作可能な状態を指定し、必要な場合はショートカットキーを設定できる、架空のボタン部品の記入例。",
            "conditions": "対象のアプリケーションで定めた部品として使用する。",
            "out_of_scope": "画面固有の処理（押したときの処理内容）。",
            "features": [
                ["F-01", "ボタン表示", "アプリ共通の見た目（形、色、大きさ）でボタンを表示する", "props（variant、color、size）", ""],
                ["F-02", "ファンクションキー", "shortcut で指定したキーの押下を、ボタンの押下として扱う", "props（shortcut）", "画面は keydown を書かない"],
            ],
            "notes": [
                ["1", "操作制御", "disabled の状態", "disabled のとき、ショートカットも無効にする", "押せない操作を、キーで実行させないため", "ST-01、M-02"],
            ],
            "remarks": "ボタンの文言は、画面から渡す。複数の画面で使う文言は、メッセージファイルで管理する。",
        },
        "layout": {
            "patterns": ["通常", "無効（disabled）", "ショートカット指定あり"],
            "elements": [
                ["E-01", "ボタン本体", "ラベル、アイコン", "常に表示", "押下（click）", "ST-01", "F-01", ""],
                ["E-02", "ショートカット表示", "ラベルの末尾に（F3）のように表示", "shortcut を指定したとき", "対応するキーの押下", "ST-02", "F-02", ""],
            ],
        },
        "state": {
            "attributes": [
                ["ST-01", "操作可否", "enabled", "押せる", "通常の色で表示", "", ""],
                ["ST-01", "操作可否", "disabled", "押せない", "薄い色で表示。ショートカットも無効", "", ""],
                ["ST-02", "ショートカット", "指定あり", "キーで押せる", "ラベルにキーを表示", "", ""],
            ],
            "patterns": [
                ["P-01", "ST-01=enabled、ST-02=指定なし", "レイアウト例1", "押下で click を発火する", ""],
                ["P-02", "ST-01=disabled", "レイアウト例2", "押下とショートカットを受け付けない", ""],
            ],
            "transitions": [
                ["1", "ST-01=enabled", "disabled を true にする", "ST-01=disabled", "", ""],
            ],
        },
        "functions": {
            "functions": [
                ["M-01", "click", "ボタンを押したとき、またはショートカットが押されたときに発火する", "event: MouseEvent | KeyboardEvent", "void", "ST-01", "―"],
                ["M-02", "onShortcut(event)", "shortcut に対応するキーを判定し、ボタンの押下として扱う", "event: KeyboardEvent / 押されたキー", "void", "ST-01", "あり"],
            ],
        },
        "details": [
            {
                "title": "M-02　onShortcut(event)",
                "values": {
                    "概要": "ファンクションキーの押下を、ボタンの押下として扱う。",
                    "引数": "event: KeyboardEvent（押されたキーの情報）",
                    "戻り値": "なし（void）",
                    "事前条件": "shortcut が指定されている。disabled が false。",
                    "処理仕様": "① 押されたキーが shortcut と一致するかを判定する。\n② 一致するときは、ブラウザの既定の動作を止める。\n③ ボタンの click を発火する。",
                    "状態への影響": "なし。",
                    "エラー・例外": "なし。一致しないキーは、何もしない。",
                },
            },
        ],
    }


def _example():
    """新しい入力形式の記入例を返す。"""
    content = _legacy_example()
    content.pop('functions', None)
    content['interface'] = {'props': [['shortcut', 'string', '任意', 'なし', '割り当てるキー。']], 'events': [['click', 'MouseEvent', 'ボタン押下時に通知する。']]}
    content['objects'] = []
    content['public_functions'] = []
    content['details'] = []
    return content


def _fill_cover_and_history(wb, meta):
    """表紙と変更履歴を書く（初版）。座標は、記入要領_共通シート.md の表のとおり。"""
    history = wb["変更履歴"]
    # PJ名・システム名・サブシステム名は、変更履歴にだけ書く（他のシートは数式で参照する）
    history["E1"].value = meta.get("project", "")
    history["E2"].value = meta.get("system", "")
    history["E3"].value = meta.get("subsystem", "")
    # 変更履歴をJSONに持たせると、再生成時にも既存の履歴を引き継げる。
    revisions = meta.get('history', [{
        'version': meta.get('version', '第1.0版'), 'date': meta.get('date', ''),
        'kind': '新規', 'sections': '-', 'description': '新規作成', 'author': meta.get('author', ''),
    }])
    if not isinstance(revisions, list) or not 1 <= len(revisions) <= 26:
        raise ValueError('変更履歴は1〜26件の配列で指定してください。')
    if revisions[-1]['version'] != meta.get('version', '第1.0版'):
        raise ValueError('表紙の版数と最後の変更履歴の版数を一致させてください。')
    for number, revision in enumerate(revisions, 1):
        row = number + 7
        history[f'A{row}'] = number
        history[f'B{row}'] = revision['version']
        history[f'D{row}'] = datetime.date.fromisoformat(revision['date']) if revision.get('date') else None
        history[f'G{row}'] = revision['kind']
        history[f'J{row}'] = revision.get('sections', '')
        history[f'Q{row}'] = revision.get('description', '')
        history[f'AF{row}'] = revision.get('author', '')
    fit_history_rows(history)
    cover = wb["表紙"]
    cover["J12"].value = meta.get("project", "")
    cover["J16"].value = meta.get("subsystem", "")
    cover["J19"].value = meta.get("version", "第1.0版")
    # 会社名・部門名は、材料が無ければ空にする（角括弧のプレースホルダーを消す）
    cover["J28"].value = meta.get("company", "")
    cover["J30"].value = meta.get("department", "")


REQUIRED_KEYS = ["overview", "layout", "state", "interface", "objects", "public_functions", "details"]


def build(output, content=None):
    """
    土台のテンプレートから、画面共通部品設計書を作って保存する。
    content: 定義JSONの辞書。None のときは、見出しだけの空のテンプレートを作る。
    """
    if content is not None:
        missing = [key for key in REQUIRED_KEYS if key not in content]
        if missing:
            raise ValueError(f"定義 JSON に、次のキーがありません: {', '.join(missing)}")
    wb = openpyxl.load_workbook(BASE_TEMPLATE)
    sheets = _prepare_sheets(wb)
    fillers = [_fill_overview, _fill_layout, _fill_state, _fill_inputs, _fill_objects, _fill_public_functions, _fill_function_detail]
    for ws, filler in zip(sheets, fillers):
        filler(ws, content)
    if content is not None and "meta" in content:
        _fill_cover_and_history(wb, content["meta"])
    # 成果物名を、表紙と変更履歴に入れる
    wb["表紙"]["J14"].value = DELIVERABLE_NAME
    wb["変更履歴"]["S1"].value = DELIVERABLE_NAME
    wb.active = 0
    # 全シートの目盛線を隠し、表紙のA1を開く状態で保存する。
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.sheet_view.tabSelected = ws.title == '表紙'
    cover_view = wb['表紙'].sheet_view
    cover_view.topLeftCell = 'A1'
    cover_view.selection[0].activeCell = 'A1'
    cover_view.selection[0].sqref = 'A1'
    return save_with_shapes(wb, str(BASE_TEMPLATE), str(output))


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="画面共通部品設計書を作る")
    parser.add_argument("output", help="出力する xlsx のパス")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--example", action="store_true", help="架空のボタンの記入例を入れる")
    group.add_argument("--content", help="内容を書いた定義 JSON のパス")
    args = parser.parse_args()
    content = None
    if args.example:
        content = _example()
    elif args.content:
        content = json.loads(Path(args.content).read_text(encoding="utf-8"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out, content)
    print(f"作成しました: {out}")


if __name__ == "__main__":
    main()
