# -*- coding: utf-8 -*-
"""
単体テスト仕様書(画面)／単体テスト仕様書(共通コンポーネント)を、テスト項目の定義ファイル(JSON)から組み立てるスクリプト。

単体テスト仕様書のテスト仕様のシートには、テスト観点カタログの観点が、あらかじめ1行ずつ並んでいる。
仕様書を作るときは、まずその機能にある分類(大項目〜)を整理し、無い分類の行はシートから消す。
残した分類の観点ごとに「テストケースを書く」か「対象外理由を書く」かのどちらかを埋めることで、
観点の抜けが無いこと（全量をテストしたこと）を示す。対象外の行は灰色にする。
1つの観点に複数のテストケースがある場合は、その観点の下に行を足す必要があり、
足すとケースNo(数式)・罫線・入力規則・印刷範囲がずれるため、手でマッピングJSONを組むと間違える。
そのため、定義ファイルから一括で組み立てる。

使い方:
    python build_unit_test_spec.py <テンプレートxlsx> <テスト項目定義json> <出力xlsx>
        [--allow-unaddressed] [--cases-json <ケース一覧の出力先json>]

  --list-catalog      : 組み立てずに、空のテンプレートの観点を「観点No  [分類]  観点の文言」の一覧で標準出力に出す。
                        python build_unit_test_spec.py <テンプレート> --list-catalog [--filter 画面表示/表示結果] [--sheet-template クラス単体|リクエスト単体|取引単体]
                        --filter は分類の前方一致(「/」でつなぐ)、--sheet-template の既定は、画面ならリクエスト単体・共通コンポーネントならクラス単体。
                        観点Noは、組み立てと同じ数え方(詳細の列が空でない行ごとに1つ目が増え、観点の列が空でない行ごとに2つ目が増える)。
                        「観点」のNoや「分類」を決める前に、これで残る観点を見る。
  --allow-unaddressed : テストケースも対象外理由も無い観点が残っていても、エラーにしない(書きかけの確認用)。
  --cases-json        : 組み立てた結果の全テストケース(ケースNo・分類・観点・テスト内容など)をJSONに書き出す。

テンプレートは assets/templates/フォーマット/ の
「単体テスト仕様書(画面)_(取引ID)_(取引名).xlsx」または
「単体テスト仕様書(共通コンポーネント)_(共通コンポーネントID)_(共通コンポーネント名).xlsx」。
テンプレートの種類は、シートの構成から判定する(『【リクエストID】_リクエスト単体』シートがあれば画面、無ければ共通コンポーネント)。
表紙・変更履歴も、定義の "document" から書く。

テスト項目定義JSONの形式:
{
  "document": {                              # 表紙・変更履歴。必須
    "PJ名": "サンプルプロジェクト", "システム名": "サンプルシステム", "サブシステム名": "受注管理システム",
    "会社名": "…", "部門名": "…",
    "変更履歴": [                             # 1要素=1行(8行目から)。表紙の版数は最後の要素の版数になる
      {"版数": "第1.0版", "変更日": "2026-01-06", "区分": "新規",
       "変更箇所": ["-"], "変更内容": ["新規作成"],   # 1要素=1行(セル内改行で並べる)
       "担当者": "TIS"}
    ]
  },
  "header": {                                # テスト仕様のシートの見出し(全シート共通)。省略可
    "機能名": "受注管理", "取引名": "受注登録"   # 共通コンポーネントでは、取引名に「-」を書く
                                             # 作成者・作成日・更新者・更新日は、変更履歴から自動で表示される(書かない)
  },
  "sheets": [
    {
      "template": "クラス単体",               # クラス単体 / リクエスト単体 / 取引単体(画面のみ)
      "name": "useOrderForm",                 # シート名は「<name>_クラス単体」「<name>_リクエスト単体」になる。
                                              #   リクエスト単体では、name は画面イベントID。取引単体では使わない(シート名は「取引単体」のまま)
      "header": {"テストターゲット名": "useOrderForm"},   # シートごとの見出し。リクエスト単体では「リクエストID」も書く。取引単体には書けない
      "分類": [                               # この機能にある分類。必須。ここに書いていない分類の行は、シートから消す
        ["バリデーション", "単項目バリデーション", "必須バリデーション"],
        ["画面表示", "表示結果"]              # クラス・リクエスト単体：大項目・中項目・小項目・詳細を上から順に並べたもの(前方一致)
                                              # 取引単体：区分・確認観点1・確認観点2を上から順に並べたもの(前方一致)
      ],
      "対象外": [                             # 「分類」に書いた分類のうち、まとめて対象外にするもの。省略可
        {"分類": ["DB操作"], "理由": "DBはバックエンドのテストで確認するため対象外"}
      ],
      "観点": [                               # 観点ごとの記入。No は空のテンプレートでのケースNoの前2つ(「詳細-観点」)
                                              #   取引単体では「確認観点2-確認観点3」(確認観点3が空の行は、確認観点2-1)
        {"No": "1-1", "cases": [
          {"前提": "受注者名を空にする",       # 前提条件。テスト内容の先頭に「【前提】…」として書く。省略可
           "テスト内容": "「登録」ボタンを押す。",
           "想定結果": "受注者名の下にエラーメッセージが表示され、APIは呼ばれない。",
           "対応設計書": "システム機能設計書", "対応箇所": "入力データ定義",
           "テストコード": "orderForm.spec.ts > 受注者名が空だとエラー"}
                                              # ほかに書ける列はテンプレートの見出しと同じ名前(テストデータシート名・データNo・実施者 など)。
                                              # 「テストコード」はテンプレートに列が無いため、テスト内容の末尾に「【テストコード】…」として書く
        ]},
        {"No": "3-5", "対象外理由": "サロゲートペア文字を許容しない設計のため対象外"}
                                              # 版を上げるとき、その版で変えたケース・観点には "changed" を付ける（赤字になる）。
                                              #   ケースに付ける：true なら、ケースの列（対応設計書・対応箇所・テスト内容・想定結果）の全部、
                                              #     列名のリスト（例: ["想定結果"]）なら、その列だけが赤字になる（「テストコード」は、テスト内容の列になる）。
                                              #   追加観点・対象外理由の記入に付ける：true なら分類・観点（対象外理由の記入は対象外理由）の全部、列名のリストならその列だけ。
                                              #   1つでも付いていれば、表紙の版数も赤字になる。前の版の "changed" は消す（作り直すので、赤字は今の版の分だけになる）
      ],
      "追加観点": [                           # テンプレートに無い、プロジェクト独自の観点。省略可
        {"after": "12-1",                     # この観点(空のテンプレートでの「詳細-観点」)の直後に足す
         "詳細": "権限",                       # 新しい詳細を始めるときに書く(大項目・中項目・小項目も同様)。省略すると直前の詳細の続き
                                              #   取引単体では、確認観点2・確認観点3を書く(区分・確認観点1も書ける)
         "観点": "閲覧権限の無い利用者がルートを開いた場合、一覧へ戻されること。",
         "cases": [{"テスト内容": "…", "想定結果": "…"}]}
      ]
    }
  ]
}

シートの組み合わせは、単体テスト標準(機能テストの分類と処理方式の組み合わせ)に合わせる。合わない場合はエラーにする。
単体テスト仕様書(画面)
- リクエスト単体(画面イベント単位)は、例外なく作る(1つ以上)。
- クラス単体(部品単位。コンポーネント・composable・ストア・入力チェックの関数など)は、ロジックが複雑なものに限って作る(0以上)。
- 取引単体(取引単位。画面遷移をまたぐ一連の操作)は、1つだけ作れる。リクエスト単体が2つ以上ある取引のときだけ作る(1つのときはエラー)。
  リクエスト単体が2つ以上あるのに取引単体が無いときは、エラーにせず、警告を出す(単体テスト標準では、画面の取引は取引単体を作る)。
単体テスト仕様書(共通コンポーネント)
- クラス単体だけを作る(1つ以上)。リクエスト単体・取引単体はエラー。

終了コード 0 で終われば、組み立ては成功。出力は verify_layout.py の対象外(シート構成が変わり、ケースNoの配列数式も誤検知になる)。
代わりに、警告の確認、--cases-json の確認、export_sheet_preview.py での見た目の確認を行う。

記入の決まりは `記入要領_単体テスト仕様書_画面.md`、`記入要領_単体テスト仕様書_共通コンポーネント.md` を参照する。
"""

import argparse
import json
import re
import sys
from copy import copy
from pathlib import Path

import openpyxl
import datetime

from openpyxl.styles import Border, Color, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula

sys.path.insert(0, str(Path(__file__).parent))
from fit_change_history_rows import (
    _column_width,
    _display_width,
    fit_rows,
)  # noqa: E402
from xlsx_common import (  # noqa: E402
    copy_data_validations,
    ensure_utf8_stdio,
    mark_font_red,
    save_with_shapes,
)

# テンプレートの種類と、テンプレートでのシート名・作成後のシート名の付け方
TEMPLATE_SHEETS = {
    "クラス単体": "【テストターゲット名】_クラス単体",
    "リクエスト単体": "【リクエストID】_リクエスト単体",
    "取引単体": "取引単体",
}

# 見出し行とデータの先頭行(全シート共通)
HEADER_ROW = 10
FIRST_ROW = 11

# 見出し(1〜9行目)に「<項目名>：<値>」の形で書く項目
HEADER_LABELS = (
    "機能名",
    "取引名",
    "テストターゲット名",
    "リクエストID",
)

# 見出しのうち、変更履歴シートから自動で表示する項目(定義には書かない)
HEADER_FROM_HISTORY = ("作成者", "作成日", "更新者", "更新日")

# 対象外の行の塗り(灰色)。Nablarchのテンプレート原本・記入例で、対象外の行に付けている色と同じ
EXCLUDED_FILL = PatternFill(
    fill_type="solid", fgColor=Color(theme=0, tint=-0.499984740745262)
)

# 変更履歴シートの列(結合セルの左上)と、1行目のデータ行・最終行
HISTORY_COLUMNS = {
    "No": "A",
    "版数": "B",
    "変更日": "D",
    "区分": "G",
    "変更箇所": "J",
    "変更内容": "Q",
    "担当者": "AF",
}
HISTORY_FIRST_ROW = 8
HISTORY_LAST_ROW = 33

# 分類の列(上の階層から順)。クラス単体・リクエスト単体は「大項目〜詳細」、
# 取引単体は「区分・確認観点1・確認観点2」が分類にあたる(確認観点2は、ケースNoの1つ目を数える列でもある)
CATEGORY_HEADERS_TEST = ("大項目", "中項目", "小項目", "詳細")
CATEGORY_HEADERS_TRANSACTION = ("区分", "確認観点1", "確認観点2")

# テンプレートに列が無く、テスト内容の末尾に書く項目(画面のテンプレートには、テストコードの列が無い)
CODE_KEY = "テストコード"

# 1行あたりの高さ(9ptのフォント)と、列幅1あたりに入る表示幅(半角1・全角2)の目安。
# このテンプレート(9pt)をExcelでPDFにして測ったところ、列幅1あたり表示幅1程度が入った。
# 単語の区切りで早めに折り返すことがあるため、少し控えめに見積もる
LINE_HEIGHT = 12.0
DISPLAY_PER_WIDTH = 0.95


class SheetLayout:
    """テスト仕様のシートの列の配置。見出し行の名前から求める。

    クラス単体・リクエスト単体と、取引単体とで、ケースNoを数える列が違う。
    - クラス単体・リクエスト単体：1つ目は「詳細」、2つ目は「観点」、3つ目は「テスト内容」。
    - 取引単体：1つ目は「確認観点2」、2つ目は「確認観点3」、3つ目は「テスト内容」。
    """

    def __init__(self, ws):
        # 見出しの名前 → 列番号
        self.columns = {c.value: c.column for c in ws[HEADER_ROW] if c.value}
        # 取引単体かどうか(確認観点3の列があるのは、取引単体だけ)
        self.is_transaction = "確認観点3" in self.columns
        if self.is_transaction:
            self.category_headers = CATEGORY_HEADERS_TRANSACTION
            self.level1_name, self.level2_name = "確認観点2", "確認観点3"
        else:
            self.category_headers = CATEGORY_HEADERS_TEST
            self.level1_name, self.level2_name = "詳細", "観点"
        needed = self.category_headers + (self.level2_name, "テスト内容", "対象外理由", "実施結果")
        for name in needed:
            if name not in self.columns:
                raise ValueError(f"シート『{ws.title}』の{HEADER_ROW}行目に「{name}」の列がありません")
        # ケースNoの1つ目を数える列
        self.level1 = self.columns[self.level1_name]
        # ケースNoの2つ目を数える列
        self.level2 = self.columns[self.level2_name]
        # ケースNoの3つ目を数える列(テスト内容)
        self.content = self.columns["テスト内容"]
        # 対象外理由の列
        self.reason = self.columns["対象外理由"]
        # 実施結果の列(入力規則 OK/NG を付ける列)
        self.result = self.columns["実施結果"]
        # 分類の列(左から順)
        self.categories = [self.columns[h] for h in self.category_headers]
        # 表の右端の列
        self.last_col = max(self.columns.values())


def _last_template_row(ws):
    """表の最終行(ケースNoの数式がある最後の行)を返す。"""
    last = FIRST_ROW
    for row in range(FIRST_ROW, ws.max_row + 1):
        if isinstance(ws.cell(row=row, column=1).value, ArrayFormula):
            last = row
    return last


def _catalog_ids(ws, layout, last_row):
    """空のテンプレートの各行に「詳細-観点」の番号を振る(ケースNoの前2つと同じ)。"""
    ids = {}
    level1 = level2 = 0
    for row in range(FIRST_ROW, last_row + 1):
        if ws.cell(row=row, column=layout.level1).value not in (None, ""):
            level1 += 1
            level2 = 0
        if ws.cell(row=row, column=layout.level2).value not in (None, ""):
            level2 += 1
        ids[row] = f"{level1}-{max(level2, 1)}"
    return ids


def _is_category(value):
    """分類の列の値が、分類そのものかどうか。

    大項目の列には、分類の補足の注記(「※ファイルアップロードを含む」など)が下の行に入っていることがある。
    「※」で始まる値は注記であり、新しい分類としては扱わない。
    """
    return value not in (None, "") and not str(value).startswith("※")


def _catalog_paths(ws, layout, last_row):
    """各行の分類(大項目〜詳細を、空欄は上の行から引き継いで並べたもの)を返す。"""
    paths = {}
    current = [""] * len(layout.categories)
    for row in range(FIRST_ROW, last_row + 1):
        for i, col in enumerate(layout.categories):
            value = ws.cell(row=row, column=col).value
            if not _is_category(value):
                continue
            current[i] = str(value)
            # 上の階層が変わったら、下の階層は引き継がない
            for j in range(i + 1, len(current)):
                current[j] = ""
        paths[row] = list(current)
    return paths


def _row_formula(template_text, row):
    """ケースNoの数式(テンプレートの11行目のもの)を、指定した行のものに書き換える。

    $E$11 のような絶対参照の 11 はそのまま残し、E11 のような相対参照の 11 だけを行番号にする。
    """
    return re.sub(
        r"(?<![$A-Z])([A-Z])11(?!\d)", lambda m: f"{m.group(1)}{row}", template_text
    )


def _case_values(case, layout):
    """テストケース1件を、列番号 → 値 の辞書にする。"""
    values = {}
    for key, value in case.items():
        if key in ("前提", "changed") or (key == CODE_KEY and key not in layout.columns):
            continue
        if key not in layout.columns:
            raise ValueError(
                f"テンプレートに無い列です: {key}（書ける列: {', '.join(layout.columns)}）"
            )
        values[layout.columns[key]] = value
    # 前提条件は、テスト内容の先頭に「【前提】…」として書く(記入要領のとおり)
    # テストコードの場所は、列が無いため、テスト内容の末尾に「【テストコード】…」として書く
    code = case.get(CODE_KEY) if CODE_KEY not in layout.columns else None
    if case.get("前提") or code:
        lines = []
        if case.get("前提"):
            lines.append(f"【前提】{case['前提']}")
        if case.get("テスト内容"):
            lines.append(case["テスト内容"])
        if code:
            lines.append(f"【{CODE_KEY}】{code}")
        values[layout.content] = "\n".join(lines)
    return values


def _changed_columns(flag, values, layout):
    """"changed" の指定（True または列名のリスト）から、赤字にする列番号のリストを返す。

    values は、その行（またはその部分）に書く 列番号 → 値 の辞書。True のときは、値のある列の全部にする。
    """
    if not flag:
        return []
    if flag is True:
        return list(values)
    columns = []
    for name in flag:
        # テストコードは、列が無いため、テスト内容の列で赤字にする
        if name == CODE_KEY and name not in layout.columns:
            name = "テスト内容"
        if name not in layout.columns:
            raise ValueError(f"changed に、テンプレートに無い列名があります: {name}")
        columns.append(layout.columns[name])
    return columns


def _observation_text(ws, layout, row):
    """カタログの行の、観点の文言を返す(取引単体は、確認観点2と確認観点3を「／」でつなぐ)。"""
    level2 = ws.cell(row=row, column=layout.level2).value
    if not layout.is_transaction:
        return str(level2 or "")
    level1 = ws.cell(row=row, column=layout.level1).value
    return "／".join(str(v) for v in (level1, level2) if v not in (None, ""))


def _catalog_label(ws, layout, ids, paths, rows_by_id, cid):
    """観点No・分類・観点の文言を、1行の文字列にする(エラー表示と --list-catalog で共通)。"""
    row = rows_by_id[cid]
    category = "/".join(c for c in paths[row] if c)
    return f"{cid}  [{category}]  {_observation_text(ws, layout, row)}"


def list_catalog(template, sheet_template=None, prefix=None):
    """テンプレートの観点を、観点No・分類・観点の文言の一覧にして返す(1観点1行の文字列のリスト)。

    観点Noは、組み立て(_plan_rows)と同じ _catalog_ids で数える。
    prefix は分類の前方一致(「画面表示/表示結果」のように「/」でつなぐ)。
    """
    wb = openpyxl.load_workbook(template)
    if sheet_template is None:
        # 既定は、画面ならリクエスト単体、共通コンポーネントならクラス単体
        sheet_template = (
            "リクエスト単体" if TEMPLATE_SHEETS["リクエスト単体"] in wb.sheetnames else "クラス単体"
        )
    if sheet_template not in TEMPLATE_SHEETS:
        raise ValueError(f"--sheet-template は {', '.join(TEMPLATE_SHEETS)} のどれかです")
    name = TEMPLATE_SHEETS[sheet_template]
    if name not in wb.sheetnames:
        raise ValueError(f"このテンプレートに『{name}』シートはありません")
    ws = wb[name]
    layout = SheetLayout(ws)
    last_row = _last_template_row(ws)
    ids = _catalog_ids(ws, layout, last_row)
    paths = _catalog_paths(ws, layout, last_row)
    rows_by_id = {}
    for row, cid in ids.items():
        rows_by_id.setdefault(cid, row)
    lines = []
    for cid, row in rows_by_id.items():
        category = "/".join(c for c in paths[row] if c)
        if prefix and not (category == prefix or category.startswith(prefix + "/")):
            continue
        lines.append(_catalog_label(ws, layout, ids, paths, rows_by_id, cid))
    return lines


def _plan_rows(sheet_def, ws, layout, last_row, allow_unaddressed):
    """出力する行の並びを組み立てる。

    戻り値は、行の並び plan、記入の無い観点 missing、赤字にする位置 changed の3つ。
    plan は、出力する行ごとの (書式の元にするテンプレートの行, 値の辞書, 行の種類) のリスト。
    行の種類は catalog(テンプレートの観点の行) / extra(同じ観点の2件目以降のケース) / added(追加観点の行)。
    changed は、(plan の何番目の行か, 赤字にする列番号のリスト) のリスト。
    """
    ids = _catalog_ids(ws, layout, last_row)
    paths = _catalog_paths(ws, layout, last_row)
    rows_by_id = {}
    for row, cid in ids.items():
        rows_by_id.setdefault(cid, row)

    # その機能にある分類の行だけを残す(無い分類の行は、シートから消す)
    kept_prefixes = sheet_def.get("分類")
    if not kept_prefixes:
        raise ValueError("「分類」に、この機能にある分類(大項目〜)を書いてください")
    for prefix in kept_prefixes:
        if not any(path[: len(prefix)] == prefix for path in paths.values()):
            raise ValueError(f"分類が、テンプレートのどの観点にも当たりません: {prefix}")
    kept_rows = {
        row
        for row, path in paths.items()
        if any(path[: len(prefix)] == prefix for prefix in kept_prefixes)
    }
    kept_ids = {ids[row] for row in kept_rows}

    # 観点ごとの記入
    entries = {}
    for item in sheet_def.get("観点", []):
        cid = item["No"]
        if cid not in rows_by_id:
            raise ValueError(f"テンプレートに無い観点のNoです: {cid}")
        if cid not in kept_ids:
            raise ValueError(f"観点 {cid} は、「分類」に書いていない分類の観点です")
        if cid in entries:
            raise ValueError(f"同じ観点のNoが2回書かれています: {cid}")
        if bool(item.get("cases")) == bool(item.get("対象外理由")):
            raise ValueError(
                f"観点 {cid} には、cases と 対象外理由 のどちらか一方だけを書いてください"
            )
        entries[cid] = item

    # 分類の単位での対象外(個別の記入が優先)
    for rule in sheet_def.get("対象外", []):
        prefix = rule["分類"]
        matched = False
        for row, path in paths.items():
            if row in kept_rows and path[: len(prefix)] == prefix:
                matched = True
                entries.setdefault(
                    ids[row], {"No": ids[row], "対象外理由": rule["理由"]}
                )
        if not matched:
            raise ValueError(
                f"対象外の分類が、「分類」に書いた分類のどの観点にも当たりません: {prefix}"
            )

    # 追加観点(after の観点の直後に足す)
    added = {}
    for item in sheet_def.get("追加観点", []):
        if item["after"] not in kept_ids:
            raise ValueError(
                f"追加観点の after が、「分類」に書いた分類の観点のNoではありません: {item['after']}"
            )
        if not item.get("cases") and not item.get("対象外理由"):
            raise ValueError(
                f"追加観点「{item.get('観点')}」に、cases も 対象外理由 もありません"
            )
        added.setdefault(item["after"], []).append(item)

    # 記入の無い観点
    missing = [
        cid for cid in dict.fromkeys(ids[r] for r in sorted(kept_rows)) if cid not in entries
    ]
    if missing and not allow_unaddressed:
        details = "\n".join(
            "  " + _catalog_label(ws, layout, ids, paths, rows_by_id, cid) for cid in missing
        )
        raise ValueError(
            "テストケースも対象外理由も無い観点があります（全量を埋めてください）。"
            "「分類」は前方一致のため、指定した分類の下にある観点が全部残ります。"
            "不要な分類は「分類」から外すか、「対象外」にまとめて理由を書いてください:\n"
            + details
        )

    # テンプレートの行を、同じ観点(番号)のまとまりに分ける
    groups = []
    for row in sorted(kept_rows):
        if groups and groups[-1][0] == ids[row]:
            groups[-1][1].append(row)
        else:
            groups.append((ids[row], [row]))

    plan = []
    changed = []
    for cid, rows in groups:
        entry = entries.get(cid) or {}
        cases = entry.get("cases") or [{}]

        # 1. 観点の行(1件目のケース、または対象外理由)
        values = {}
        if entry.get("対象外理由"):
            values[layout.reason] = entry["対象外理由"]
            changed.append((len(plan), _changed_columns(entry.get("changed"), values, layout)))
        else:
            values.update(_case_values(cases[0], layout))
            changed.append((len(plan), _changed_columns(cases[0].get("changed"), values, layout)))
        plan.append((rows[0], values, "catalog"))

        # 2. 同じ番号の続きの行(テンプレートで分類の注記を下の行に持つもの)は、そのまま写す
        for row in rows[1:]:
            plan.append((row, {}, "catalog"))

        # 3. 2件目以降のケース
        for case in cases[1:]:
            case_values = _case_values(case, layout)
            changed.append((len(plan), _changed_columns(case.get("changed"), case_values, layout)))
            plan.append((rows[0], case_values, "extra"))

        # 4. この観点の後ろに足す追加観点
        for item in added.get(cid, []):
            base = {}
            for header in layout.category_headers + (layout.level2_name,):
                if header in item:
                    base[layout.columns[header]] = item[header]
            if item.get("対象外理由"):
                base[layout.reason] = item["対象外理由"]
                changed.append((len(plan), _changed_columns(item.get("changed"), base, layout)))
                plan.append((rows[0], base, "added"))
                continue
            first = dict(base)
            first_case = _case_values(item["cases"][0], layout)
            first.update(first_case)
            columns = _changed_columns(item.get("changed"), base, layout)
            columns += _changed_columns(item["cases"][0].get("changed"), first_case, layout)
            changed.append((len(plan), columns))
            plan.append((rows[0], first, "added"))
            for case in item["cases"][1:]:
                case_values = _case_values(case, layout)
                changed.append((len(plan), _changed_columns(case.get("changed"), case_values, layout)))
                plan.append((rows[0], case_values, "extra"))

    return plan, missing, changed


def _estimate_height(ws, values, base_height):
    """セルの表示幅と列の幅から、行の高さの目安を求める(折り返して全部見えるように)。

    列の幅は _column_width で読む(ws.column_dimensions[列] と書くと、まとめて設定された列
    (J:K など)に新しい設定が作られ、列の幅が変わってしまうため)。
    """
    lines = 1
    for col, value in values.items():
        if value in (None, ""):
            continue
        per_line = max(1, int(_column_width(ws, col) * DISPLAY_PER_WIDTH))
        count = 0
        for text_line in str(value).split("\n"):
            count += max(1, -(-_display_width(text_line) // per_line))
        lines = max(lines, count)
    return max(base_height or 0, LINE_HEIGHT * lines + 4)


def _relabel_categories(ws, row, layout, path, previous_path):
    """分類の見出し(大項目〜詳細)を、残した行に合わせて書き直す。

    テンプレートでは、分類の名前は、そのまとまりの最初の行にだけ書いてある。
    最初の行を消すと名前も消えるため、分類が変わる行に名前と上の罫線を書き直し、
    同じ分類の続きの行からは名前と上の罫線を消す。
    """
    for i, col in enumerate(layout.categories):
        cell = ws.cell(row=row, column=col)
        # 分類の補足の注記(「※…」)は、そのまま残す
        if cell.value not in (None, "") and not _is_category(cell.value):
            continue
        border = cell.border
        changed = previous_path is None or path[: i + 1] != previous_path[: i + 1]
        if changed and path[i]:
            cell.value = path[i]
            _reset_font_color(cell)
            style = border.left.style or border.right.style or "thin"
            cell.border = Border(left=copy(border.left), right=copy(border.right), top=Side(style=style), bottom=copy(border.bottom))
        else:
            cell.value = None
            cell.border = Border(left=copy(border.left), right=copy(border.right), top=Side(), bottom=copy(border.bottom))


def _reset_font_color(cell):
    """文字色を標準の色に戻す。

    テンプレートの分類の列は、続きの行のセルの文字色が背景と同じ色(見えない色)になっている。
    そのセルの書式を写した行に分類の名前を書くと、名前が見えなくなるため、標準の色に戻す。
    """
    font = cell.font
    cell.font = Font(name=font.name, size=font.sz, bold=font.b, italic=font.i, vertAlign=font.vertAlign, underline=font.u, strike=font.strike)


def _without_top(border, columns_without_top, col):
    """続きの行の分類・観点の列は、上の罫線を消す(1つの観点の中の行であることを示す)。"""
    if col not in columns_without_top:
        return copy(border)
    return Border(
        left=copy(border.left),
        right=copy(border.right),
        top=Side(),
        bottom=copy(border.bottom),
    )


def build_sheet(ws, sheet_def, allow_unaddressed):
    """テスト仕様のシート1枚を、定義のとおりに組み立てる。"""
    layout = SheetLayout(ws)
    last_row = _last_template_row(ws)
    template_formula = ws.cell(row=FIRST_ROW, column=1).value.text

    # 1. テンプレートの行の書式・高さ・値を控える
    snapshot = {}
    for row in range(FIRST_ROW, last_row + 1):
        snapshot[row] = {
            "height": ws.row_dimensions[row].height,
            "cells": {
                col: (
                    ws.cell(row=row, column=col).value,
                    ws.cell(row=row, column=col)._style,
                )
                for col in range(2, layout.last_col + 1)
            },
            "a_style": ws.cell(row=row, column=1)._style,
        }
    region_merges = [rng for rng in ws.merged_cells.ranges if rng.min_row >= FIRST_ROW]

    # 2. 出力する行の並びを決める
    paths = _catalog_paths(ws, layout, last_row)
    plan, missing, changed = _plan_rows(sheet_def, ws, layout, last_row, allow_unaddressed)

    # 3. 表の部分を消す
    for rng in region_merges:
        ws.unmerge_cells(str(rng))
    clear_to = max(last_row, FIRST_ROW + len(plan) - 1)
    for row in range(FIRST_ROW, clear_to + 1):
        for col in range(1, layout.last_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.value = None
            cell.style = "Normal"
        ws.row_dimensions[row].height = None

    # 4. 行を書く
    columns_without_top = set(layout.categories) | {layout.level2}
    first_out_row = {}
    previous_path = None
    for offset, (src, values, kind) in enumerate(plan):
        out = FIRST_ROW + offset
        first_out_row.setdefault(src, out)
        src_cells = snapshot[src]["cells"]
        ws.cell(row=out, column=1)._style = copy(snapshot[src]["a_style"])
        for col in range(2, layout.last_col + 1):
            value, style = src_cells[col]
            cell = ws.cell(row=out, column=col)
            cell._style = copy(style)
            if kind == "catalog":
                cell.value = value
            elif kind == "extra" and col in columns_without_top:
                # 同じ観点の2件目以降：分類・観点は空にし、上の罫線を消す
                cell.border = _without_top(cell.border, columns_without_top, col)
            elif kind == "added" and col in columns_without_top:
                # 追加観点：観点は書き、分類は書いた階層だけ上の罫線を残す
                if col not in values:
                    cell.border = _without_top(cell.border, columns_without_top, col)
                elif col in layout.categories:
                    # 写した行が続きの行だと、分類の名前が見えない色になるため
                    _reset_font_color(cell)
        if kind == "catalog":
            _relabel_categories(ws, out, layout, paths[src], previous_path)
            previous_path = paths[src]
        for col, value in values.items():
            ws.cell(row=out, column=col).value = value
        # ケースNoの数式
        ws.cell(row=out, column=1).value = ArrayFormula(
            f"A{out}", _row_formula(template_formula, out)
        )
        # 対象外の行は、観点から右を灰色にする(テストした行と見分けられるように)
        if values.get(layout.reason):
            for col in range(layout.level2, layout.last_col + 1):
                ws.cell(row=out, column=col).fill = copy(EXCLUDED_FILL)
        # 行の高さ
        shown = {
            col: ws.cell(row=out, column=col).value
            for col in range(2, layout.last_col + 1)
        }
        ws.row_dimensions[out].height = _estimate_height(
            ws, shown, snapshot[src]["height"] if kind == "catalog" else None
        )

    new_last = FIRST_ROW + len(plan) - 1

    # 変更した箇所（"changed"）を赤字にする。値の無いセルは、色が見えないので対象にならない
    marked = 0
    for offset, columns in changed:
        for col in columns:
            if mark_font_red(ws, f"{openpyxl.utils.get_column_letter(col)}{FIRST_ROW + offset}"):
                marked += 1

    # 表の最終行には、下の罫線を引く(分類の列は、まとまりの最後の行にしか下の罫線が無く、
    # その行を消した場合に表の下が開くため)
    for col in range(1, layout.last_col + 1):
        cell = ws.cell(row=new_last, column=col)
        border = cell.border
        style = border.left.style or border.right.style or "thin"
        cell.border = Border(
            left=copy(border.left), right=copy(border.right), top=copy(border.top), bottom=Side(style=style)
        )

    # 5. 分類の注記の結合セル(「※ファイルアップロードを含む」など)を、新しい行の位置で結合し直す
    for rng in region_merges:
        if rng.min_row not in first_out_row:
            continue
        start = first_out_row[rng.min_row]
        end = first_out_row.get(rng.max_row, start)
        ws.merge_cells(
            start_row=start,
            start_column=rng.min_col,
            end_row=end,
            end_column=rng.max_col,
        )

    # 6. 実施結果の入力規則(OK/NG)を、表の行全体に付け直す
    keep = [
        dv
        for dv in ws.data_validations.dataValidation
        if not any(r.min_row >= FIRST_ROW for r in dv.sqref.ranges)
    ]
    ws.data_validations.dataValidation = keep
    result_letter = openpyxl.utils.get_column_letter(layout.result)
    dv = DataValidation(type="list", formula1='"OK,NG"', allow_blank=True)
    dv.add(f"{result_letter}{FIRST_ROW}:{result_letter}{new_last}")
    ws.add_data_validation(dv)

    # 7. 対象外理由の列を表示する
    # テンプレートの原本では、この列はグループ化して非表示になっている。
    # 観点ごとに「テストした」か「対象外にした理由」のどちらかが見えないと、全量の確認ができないため表示する
    # (グループ化は残すので、Excelで畳むこともできる)。
    # まとめて設定された列に新しい設定を作らないよう、この列を含む既存の設定を探して直す
    for dim in ws.column_dimensions.values():
        low = dim.min or openpyxl.utils.column_index_from_string(dim.index)
        if low <= layout.reason <= (dim.max or low):
            dim.hidden = False

    # 8. 印刷範囲とオートフィルター
    last_letter = openpyxl.utils.get_column_letter(layout.last_col)
    ws.print_area = f"A1:{last_letter}{new_last}"
    if ws.auto_filter.ref:
        ws.auto_filter.ref = f"A{HEADER_ROW}:{last_letter}{HEADER_ROW}"

    return layout, new_last, missing, marked


def _write_document(wb, document):
    """表紙と変更履歴シートを書く。

    PJ名・システム名・サブシステム名は変更履歴シートにだけ書く(ほかのシート・表紙は数式で表示する)。
    表紙の版数は、変更履歴の最後の行の版数にそろえる。
    """
    history_rows = document["変更履歴"]
    if not history_rows:
        raise ValueError("document の変更履歴に、1行以上書いてください")
    if len(history_rows) > HISTORY_LAST_ROW - HISTORY_FIRST_ROW + 1:
        raise ValueError(
            f"変更履歴は {HISTORY_LAST_ROW - HISTORY_FIRST_ROW + 1} 行までです"
        )

    # 1. 変更履歴シート
    history = wb["変更履歴"]
    history["E1"] = document["PJ名"]
    history["E2"] = document["システム名"]
    history["E3"] = document["サブシステム名"]
    for i, item in enumerate(history_rows):
        row = HISTORY_FIRST_ROW + i
        history[f"{HISTORY_COLUMNS['No']}{row}"] = i + 1
        history[f"{HISTORY_COLUMNS['版数']}{row}"] = item["版数"]
        # 変更日は日付型にする(表紙の最終更新日・見出しの作成日などの数式が計算できるように)
        history[f"{HISTORY_COLUMNS['変更日']}{row}"] = datetime.datetime.strptime(
            item["変更日"], "%Y-%m-%d"
        )
        history[f"{HISTORY_COLUMNS['区分']}{row}"] = item["区分"]
        # 変更箇所・変更内容は、1要素=1行のセル内改行で書く(記入要領_共通シート.md)
        history[f"{HISTORY_COLUMNS['変更箇所']}{row}"] = "\n".join(item["変更箇所"])
        history[f"{HISTORY_COLUMNS['変更内容']}{row}"] = "\n".join(item["変更内容"])
        history[f"{HISTORY_COLUMNS['担当者']}{row}"] = item["担当者"]
    fit_rows(history)

    # 2. 表紙(J23・J25・I21 は数式なので書かない)
    cover = wb["表紙"]
    cover["J12"] = document["PJ名"]
    cover["J16"] = document["サブシステム名"]
    cover["J19"] = history_rows[-1]["版数"]
    cover["J28"] = document["会社名"]
    cover["J30"] = document["部門名"]


# 見出しの右側の項目と、その値を変更履歴シートから表示する数式
HISTORY_LINKED_LABELS = {
    "作成者：": '="作成者："&INDIRECT("変更履歴!AC1")',
    "更新者：": '="更新者："&INDIRECT("変更履歴!AC2")',
    "作成日：": '="作成日："&IF(INDIRECT("変更履歴!AG1")="","",TEXT(INDIRECT("変更履歴!AG1"),"yyyy/mm/dd"))',
    "更新日：": '="更新日："&IF(INDIRECT("変更履歴!AG2")="","",TEXT(INDIRECT("変更履歴!AG2"),"yyyy/mm/dd"))',
}


def _link_header_to_history(ws):
    """見出しのPJ名(A1)・サブシステム名(A4)・作成者・作成日・更新者・更新日を、変更履歴シートから表示する数式にする。

    画面・共通コンポーネントのテンプレートでは、これらが固定の文字(「[プロジェクト名]」「作成者：」など)のため、
    変更履歴シートの値を表示する数式に置き換える(PJ名などは、変更履歴シートにだけ書く)。
    """
    ws["A1"] = '=IF(INDIRECT("変更履歴!E1")<>"",INDIRECT("変更履歴!E1"),"")'
    ws["A4"] = '="サブシステム名："&INDIRECT("変更履歴!E3")'
    for row in ws.iter_rows(min_row=5, max_row=HEADER_ROW - 1):
        for cell in row:
            if cell.value in HISTORY_LINKED_LABELS:
                cell.value = HISTORY_LINKED_LABELS[cell.value]


def _fill_header(ws, header):
    """見出し(1〜9行目)の「<項目名>：」のセルに値を書く。"""
    for key, value in header.items():
        if key in HEADER_FROM_HISTORY:
            raise ValueError(
                f"{key} は変更履歴シートから自動で表示されるため、header には書かない（document の変更履歴に書く）"
            )
        if key not in HEADER_LABELS:
            raise ValueError(
                f"見出しに無い項目です: {key}（書ける項目: {', '.join(HEADER_LABELS)}）"
            )
        target = None
        for row in ws.iter_rows(min_row=1, max_row=HEADER_ROW - 1):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith(f"{key}："):
                    target = cell
        if target is None:
            raise ValueError(f"シート『{ws.title}』に「{key}：」の欄がありません")
        target.value = f"{key}：{value}"


def compute_case_numbers(ws, layout, last_row):
    """ケースNo(Excelの数式と同じ数え方)と、各行の内容を返す。

    openpyxlで書いたファイルには数式の計算結果が入らないため、確認用に同じ計算をする。
    取引単体では、確認観点2を分類に含め、確認観点3を観点として返す。
    """
    cases = []
    level1 = level2 = level3 = 0
    current = [""] * len(layout.categories)
    point = ""
    skipped = {"ケースNo", "ケースNo.", layout.level2_name} | set(layout.category_headers)
    for row in range(FIRST_ROW, last_row + 1):

        def val(col):
            return ws.cell(row=row, column=col).value

        for i, col in enumerate(layout.categories):
            if _is_category(val(col)):
                current[i] = str(val(col))
                for j in range(i + 1, len(current)):
                    current[j] = ""
        if val(layout.level1) not in (None, ""):
            level1 += 1
            level2 = 0
            level3 = 0
            point = ""
        if val(layout.level2) not in (None, ""):
            level2 += 1
            level3 = 0
            point = str(val(layout.level2))
        if val(layout.content) not in (None, ""):
            level3 += 1
        record = {
            "ケースNo": f"{level1}-{max(level2, 1)}-{max(level3, 1)}",
            "分類": [c for c in current if c and c != "-"],
            "観点": point,
        }
        for name, col in layout.columns.items():
            if name in skipped:
                continue
            if val(col) not in (None, ""):
                record[name] = val(col)
        cases.append(record)
    return cases


def _check_sheet_combination(wb, sheet_defs):
    """シートの組み合わせが、単体テスト標準に合うかを検査する。合わなければ ValueError。

    戻り値は、エラーにはしないが知らせたい事項(警告)のリスト。
    - 画面：リクエスト単体は1つ以上。取引単体は1つまで、かつリクエスト単体が2つ以上のときだけ。
    - 共通コンポーネント：クラス単体だけ(1つ以上)。
    """
    kinds = [d.get("template") for d in sheet_defs]
    for kind in kinds:
        if kind not in TEMPLATE_SHEETS:
            raise ValueError(f"template は {', '.join(TEMPLATE_SHEETS)} のどれかです: {kind}")
    # テンプレートの種類(『【リクエストID】_リクエスト単体』シートがあれば画面)
    is_component = TEMPLATE_SHEETS["リクエスト単体"] not in wb.sheetnames
    warnings = []
    if is_component:
        if any(k != "クラス単体" for k in kinds):
            raise ValueError(
                "共通コンポーネントの単体テスト仕様書には、クラス単体のシートだけを作る"
                "（リクエスト単体・取引単体は作れない）"
            )
        if not kinds:
            raise ValueError("クラス単体のシートを、1つ以上定義してください")
    else:
        requests = kinds.count("リクエスト単体")
        if requests == 0:
            raise ValueError(
                "リクエスト単体(画面イベント単位)のテストは、例外なく作る（単体テスト標準）"
            )
        if kinds.count("取引単体") > 1:
            raise ValueError("取引単体のシートは、1つしか作れない")
        if "取引単体" in kinds and requests < 2:
            raise ValueError(
                "取引単体(取引単位)は、リクエスト単体が2つ以上ある取引のときだけ作る（画面遷移をまたぐ操作が無い取引では作らない）"
            )
        if requests >= 2 and "取引単体" not in kinds:
            warnings.append(
                "リクエスト単体が2つ以上あるのに、取引単体がありません（単体テスト標準では、画面の取引は取引単体を作る）"
            )
    # シート名の重複(名前は、取引単体を除き、種類ごとの name で決まる)
    names = []
    for d in sheet_defs:
        if d["template"] != "取引単体":
            if not d.get("name"):
                raise ValueError(f"{d['template']} のシートには、name を書いてください")
            names.append(f"{d['name']}_{d['template']}")
    for name in names:
        if names.count(name) > 1:
            raise ValueError(f"同じシート名が2つあります: {name}")
    return warnings


def build(template, definition_path, output, allow_unaddressed=False, cases_json=None):
    definition = json.loads(Path(definition_path).read_text(encoding="utf-8"))
    wb = openpyxl.load_workbook(template)

    # 1. 定義のシートを、テンプレートのシートから複製して作る
    # 単体テスト標準(機能テストの分類と処理方式の組み合わせ)に合わないシートを止める
    warnings = _check_sheet_combination(wb, definition["sheets"])

    used_templates = set()
    built = []
    for sheet_def in definition["sheets"]:
        kind = sheet_def["template"]
        if kind not in TEMPLATE_SHEETS:
            raise ValueError(
                f"template は {', '.join(TEMPLATE_SHEETS)} のどれかです: {kind}"
            )
        source_name = TEMPLATE_SHEETS[kind]
        if source_name not in wb.sheetnames:
            raise ValueError(f"このテンプレートに『{source_name}』シートはありません")
        new_name = source_name if kind == "取引単体" else f"{sheet_def['name']}_{kind}"
        if len(new_name) > 31 or re.search(r"[\[\]:*?/\\]", new_name):
            raise ValueError(
                f"シート名に使えない名前です（31文字以内、[ ] : * ? / \\ は不可）: {new_name}"
            )
        if kind == "取引単体":
            ws = wb[source_name]
        else:
            source = wb[source_name]
            ws = wb.copy_worksheet(source)
            copy_data_validations(source, ws)
            ws.title = new_name
            ws.freeze_panes = source.freeze_panes
            if source.auto_filter.ref:
                ws.auto_filter.ref = source.auto_filter.ref
        used_templates.add(source_name)
        built.append((ws, sheet_def))

    # 2. 使わないテンプレートのシートを消し、作ったシートを並べる(クラス単体 → リクエスト単体 → 取引単体)
    for name in TEMPLATE_SHEETS.values():
        if name in wb.sheetnames and not (
            name == "取引単体" and name in used_templates
        ):
            del wb[name]
    order = {"クラス単体": 0, "リクエスト単体": 1, "取引単体": 2}
    fixed = [wb[n] for n in ("表紙", "変更履歴")]
    sheets = sorted(
        (ws for ws, _ in built),
        key=lambda s: order[[k for k in order if s.title.endswith(k)][0]],
    )
    wb._sheets = fixed + sheets

    # 3. シートごとに中身を組み立てる
    summary = []
    all_cases = {}
    marked_total = 0
    for ws, sheet_def in built:
        header = dict(definition.get("header", {}))
        header.update(sheet_def.get("header", {}))
        _link_header_to_history(ws)
        _fill_header(ws, header)
        layout, last_row, missing, marked = build_sheet(ws, sheet_def, allow_unaddressed)
        marked_total += marked
        cases = compute_case_numbers(ws, layout, last_row)
        all_cases[ws.title] = cases
        written = [c for c in cases if c.get("テスト内容")]
        excluded = [c for c in cases if c.get("対象外理由")]
        summary.append((ws.title, len(written), len(excluded), missing))

    _write_document(wb, definition["document"])

    # 変更した箇所があるときは、表紙の版数も赤字にする
    if marked_total > 0:
        mark_font_red(wb["表紙"], "J19")

    save_with_shapes(wb, template, output)

    if cases_json:
        Path(cases_json).write_text(
            json.dumps(all_cases, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    return summary, warnings


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("template")
    parser.add_argument("definition", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--allow-unaddressed", action="store_true")
    parser.add_argument("--cases-json")
    parser.add_argument("--list-catalog", action="store_true")
    parser.add_argument("--filter")
    parser.add_argument("--sheet-template")
    args = parser.parse_args()

    # 観点の一覧(空のテンプレートの観点No・分類・観点の文言)
    if args.list_catalog:
        for line in list_catalog(args.template, args.sheet_template, args.filter):
            print(line)
        return
    if not args.definition or not args.output:
        parser.error("定義jsonと出力パスを指定してください(観点の一覧だけなら --list-catalog)")

    summary, warnings = build(
        args.template,
        args.definition,
        args.output,
        args.allow_unaddressed,
        args.cases_json,
    )
    for title, written, excluded, missing in summary:
        print(f"{title}: テストケース {written} 件 / 対象外 {excluded} 件")
        if missing:
            print(f"  記入の無い観点: {', '.join(missing)}", file=sys.stderr)
    for message in warnings:
        print(f"警告: {message}", file=sys.stderr)


if __name__ == "__main__":
    main()
