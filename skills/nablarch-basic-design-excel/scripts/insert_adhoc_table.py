# -*- coding: utf-8 -*-
"""
「2.4/2.6. 処理詳細」のような、罫線も結合セルも無い自由記述エリアに、
新規の表(見出し行＋データ行、罫線・結合セル付き)をその場で作成するスクリプト。

【背景】
Nablarch標準の「処理詳細」は完全に空白の自由記述エリアであり、実際の公式サンプル
(振込依頼作成・口座振替結果ワークテーブル作成)を確認すると、処理ステップの内容に応じて
バリデーション表・エラー応答表・パラメータ表等の**表がその場で新規に作成**されている。
`apply_mapping.py`はセルの値しか書けず、`extend_table_rows.py`・`insert_row_block.py`は
どちらも「既存の表を複製・拡張する」スクリプトのため、表が何も無い場所に新規の表を作ることは
できない。このスクリプトはその隙間を埋める。

【方針】
罫線・フォント・塗りつぶし・配置を一から指定するのではなく、**同じファイル内の既存の表の
見出しセル・データセルから書式を借用する**。Nablarch標準テンプレートは表ごとに書式(罫線の
太さ・フォント等)が統一されているため、既存の表(多くの場合「2.1/2.4 入出力一覧」等、
必ず存在するセクション)から借用すれば、見た目の一貫性が自動的に保たれる。

このスクリプトが作るのは構造(見出しの文字列・罫線・結合セル)のみ。データ行の値は
空のまま残すので、`apply_mapping.py`で反映すること(insert_row_block.pyと同じ設計方針)。

安全のため、指定した行範囲(見出し行〜データ最終行)に既に罫線または値を持つセルがあれば
エラーで中止する(意図せず既存の表・内容を壊すことを防ぐ)。

使い方:
    python insert_adhoc_table.py <元xlsxパス> <シート名> <見出し行番号> <データ行数> \\
        <列定義JSONパス> <見出し書式の元セル> <データ書式の元セル> <出力xlsxパス> [--preset <プリセット名>]

列定義JSON(--presetを使わない場合に指定):
[
  {"header": "No.", "start_col": "E", "end_col": "E"},
  {"header": "バリデーション名", "start_col": "F", "end_col": "K"},
  ...
]

プリセット(--presetで指定すると列定義JSONは不要):
- validation         : No./バリデーション名/バリデーション内容/メッセージID/埋め込み文字列/後続バリデーションの続行判定
                        (E / F:K / L:U / V:X / Y:AB / AC:AF)
- error_response_web  : HTTPステータスコード/障害コード/メッセージID/埋め込み文字列 (E:I / J:L / M:P / Q:AD)
- error_response_batch: 終了コード/障害コード/メッセージID/埋め込み文字列 (E:G / H:J / K:N / O:AB)
- parameter           : パラメータ/設定値 (E:K / L:AD)

【注意】**プリセットは「必ず使うべきもの」ではない。** これらは、たまたま確認した2つの公式サンプル
(振込依頼作成・口座振替結果ワークテーブル作成)に出てきた列構成をそのまま切り出しただけであり、
Nablarchの公式な決まりごとではない。このスクリプトの本体は**任意の列構成を指定できる列定義JSON**
であり、プリセットはその中でも複数のサンプルに共通して出てきた3パターン(入力検証・エラー応答・
パラメータ設定)を毎回手で列定義JSONを書かずに済むようにした時短用のショートカットに過ぎない。

**表の列構成を決める判断基準は「この処理ステップで実際に何を伝える必要があるか」であり、
「プリセットにある形に当てはめられそうか」ではない。** 内容がプリセットの3パターンに
自然に合致するならそのまま使ってよいが、合致しない場合はプリセットに無理に押し込めず、
列定義JSONを自作すること。表そのものが不要（自由記述の文章で十分）な場合にまで、
このスクリプトで表を作る必要はない。

プリセットは「字下げ無し」の位置を前提にしている。公式サンプルには、`(a)/(b)...`のように
1段階字下げした場所に同じ表を置く例もあり、その場合は列を1〜2列右にずらした独自の列定義JSONを使うこと。

例(バッチ処理の「2.6. 処理詳細」に、6行のバリデーション表を70行目から作る場合。
   見出し・データの書式は「2.4 入出力一覧」の見出し行31・データ行33から借用):
    python insert_adhoc_table.py 出力.xlsx "2. E10201（評価処理）" 70 3 - D31 D33 出力2.xlsx --preset validation
"""
import sys
import json
import argparse
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import save_with_shapes, find_next_populated_row, ensure_utf8_stdio


PRESETS = {
    "validation": [
        {"header": "No.", "start_col": "E", "end_col": "E"},
        {"header": "バリデーション名", "start_col": "F", "end_col": "K"},
        {"header": "バリデーション内容", "start_col": "L", "end_col": "U"},
        {"header": "メッセージID", "start_col": "V", "end_col": "X"},
        {"header": "埋め込み文字列", "start_col": "Y", "end_col": "AB"},
        {"header": "後続バリデーションの続行判定", "start_col": "AC", "end_col": "AF"},
    ],
    "error_response_web": [
        {"header": "HTTPステータスコード", "start_col": "E", "end_col": "I"},
        {"header": "障害コード", "start_col": "J", "end_col": "L"},
        {"header": "メッセージID", "start_col": "M", "end_col": "P"},
        {"header": "埋め込み文字列", "start_col": "Q", "end_col": "AD"},
    ],
    "error_response_batch": [
        {"header": "終了コード", "start_col": "E", "end_col": "G"},
        {"header": "障害コード", "start_col": "H", "end_col": "J"},
        {"header": "メッセージID", "start_col": "K", "end_col": "N"},
        {"header": "埋め込み文字列", "start_col": "O", "end_col": "AB"},
    ],
    "parameter": [
        {"header": "パラメータ", "start_col": "E", "end_col": "K"},
        {"header": "設定値", "start_col": "L", "end_col": "AD"},
    ],
}


def _resolve_style_cell(wb, default_ws, ref):
    """"シート名!セル" または "セル" の形式を解釈し、Cellオブジェクトを返す"""
    if "!" in ref:
        sheet_part, coord = ref.rsplit("!", 1)
        sheet_name = sheet_part.strip("'")
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"書式の借用元シートが存在しません: {sheet_name}")
        return wb[sheet_name][coord]
    return default_ws[ref]


def _apply_style_to_range(ws, min_row, max_row, min_col, max_col, style_cell):
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = copy(style_cell.font)
            cell.fill = copy(style_cell.fill)
            cell.border = copy(style_cell.border)
            cell.alignment = copy(style_cell.alignment)
            cell.number_format = style_cell.number_format
            cell.protection = copy(style_cell.protection)


def insert_adhoc_table(xlsx_path, sheet_name, header_row, num_data_rows, columns,
                        header_style_cell, data_style_cell, output_path,
                        allow_overwrite=False):
    if num_data_rows <= 0:
        raise ValueError(f"データ行数({num_data_rows})は1以上を指定してください。")
    if not columns:
        raise ValueError("列定義が空です。")

    wb = openpyxl.load_workbook(xlsx_path)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"シートが存在しません: {sheet_name}")
    if sheet_name in ("表紙", "変更履歴", "目次"):
        raise ValueError(
            f"『{sheet_name}』シートへの使用は禁止されています。"
            f"insert_adhoc_table.pyは本体シート専用です（表紙・変更履歴・目次には絶対に使わないこと）。"
        )
    ws = wb[sheet_name]

    parsed_columns = []
    min_col_overall = None
    max_col_overall = None
    for col in columns:
        start_col = column_index_from_string(col["start_col"])
        end_col = column_index_from_string(col["end_col"])
        if end_col < start_col:
            raise ValueError(f"列定義が不正です(start_col > end_col): {col}")
        parsed_columns.append((col["header"], start_col, end_col))
        min_col_overall = start_col if min_col_overall is None else min(min_col_overall, start_col)
        max_col_overall = end_col if max_col_overall is None else max(max_col_overall, end_col)

    last_row = header_row + num_data_rows

    if not allow_overwrite:
        # 見出し行の1行前から、対象範囲に既に値や罫線を持つセルが無いか確認する。
        for r in range(header_row, last_row + 1):
            for c in range(min_col_overall, max_col_overall + 1):
                cell = ws.cell(row=r, column=c)
                b = cell.border
                has_border = b and any([b.top and b.top.style, b.bottom and b.bottom.style,
                                        b.left and b.left.style, b.right and b.right.style])
                if cell.value is not None or has_border:
                    raise ValueError(
                        f"{cell.coordinate}に既に値または罫線があります。"
                        f"insert_adhoc_table.pyは空白の領域に新規の表を作るためのスクリプトであり、"
                        f"既存の内容を上書きする可能性があるため中止しました。"
                        f"行番号を見直すか、意図的に上書きしたい場合のみ --allow-overwrite を指定してください。"
                    )
        # さらに、対象範囲の直後に既存の内容(次の見出し等)が無いかも確認する。
        boundary_row = find_next_populated_row(ws, last_row, min_col_overall, max_col_overall)
        if boundary_row is not None and boundary_row <= last_row + 2:
            raise ValueError(
                f"{boundary_row}行目付近に既存の内容があります。表のサイズ(データ{num_data_rows}行)が"
                f"大きすぎて後続の内容に近づきすぎている可能性があります。行数を見直してください。"
                f"(意図的にこのまま作成したい場合のみ --allow-overwrite を指定)"
            )

    header_style_src = _resolve_style_cell(wb, ws, header_style_cell)
    data_style_src = _resolve_style_cell(wb, ws, data_style_cell)

    # --- 見出し行 ---
    for header_text, start_col, end_col in parsed_columns:
        ws.cell(row=header_row, column=start_col, value=header_text)
        if end_col > start_col:
            ws.merge_cells(start_row=header_row, start_column=start_col,
                            end_row=header_row, end_column=end_col)
        _apply_style_to_range(ws, header_row, header_row, start_col, end_col, header_style_src)

    # --- データ行 ---
    for i in range(num_data_rows):
        r = header_row + 1 + i
        for _, start_col, end_col in parsed_columns:
            if end_col > start_col:
                ws.merge_cells(start_row=r, start_column=start_col, end_row=r, end_column=end_col)
            _apply_style_to_range(ws, r, r, start_col, end_col, data_style_src)

    save_with_shapes(wb, xlsx_path, output_path)

    return {
        "sheet": sheet_name,
        "header_row": header_row,
        "data_rows": list(range(header_row + 1, last_row + 1)),
        "columns": columns,
    }


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xlsx_path")
    parser.add_argument("sheet_name")
    parser.add_argument("header_row", type=int)
    parser.add_argument("num_data_rows", type=int)
    parser.add_argument("columns_json_path", help="列定義JSONファイルパス。--preset使用時は'-'でよい")
    parser.add_argument("header_style_cell")
    parser.add_argument("data_style_cell")
    parser.add_argument("output_path")
    parser.add_argument("--preset", choices=list(PRESETS.keys()))
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    if args.preset:
        columns = PRESETS[args.preset]
    else:
        with open(args.columns_json_path, encoding="utf-8") as f:
            columns = json.load(f)

    result = insert_adhoc_table(
        args.xlsx_path, args.sheet_name, args.header_row, args.num_data_rows, columns,
        args.header_style_cell, args.data_style_cell, args.output_path, args.allow_overwrite,
    )
    print(f"=== 新規表の作成結果: {args.output_path} ===")
    print(f"見出し行: {result['header_row']}")
    print(f"データ行: {result['data_rows']}")
    print(f"列構成: {result['columns']}")
    print("\n※見出し文字列は書き込み済みですが、データ行の値はまだ空です。apply_mapping.pyで反映してください。")


if __name__ == "__main__":
    main()
