# -*- coding: utf-8 -*-
"""
確定済みの記載内容(マッピングJSON)を、Excelテンプレートのセルに書き込むスクリプト。

設計方針(レイアウトを崩さないための制約):
- セルの `value` のみを書き換える。フォント・背景色・罫線・列幅・行高は一切変更しない。
- 行や列の挿入・削除は一切行わない(openpyxlのinsert_rows/insert_cols/appendは使用しない)。
- 結合セルへの書き込みは、結合範囲の左上アンカーセルへ自動的に振り替える。
- 罫線が設定されている範囲(=テンプレートとして書式が用意された領域)を超える書き込みは、
  既定では拒否する(表の行数を超えて無理に書き込まないため)。
  意図的に範囲外へ書き込みたい場合のみ --allow-outside-border を指定する。
- プルダウン(入力規則)が設定されているセルに、選択肢に無い値を書こうとした場合は警告を出す
  (エラーで止めはしない。将来的に選択肢が追加される可能性があるため)。
  プルダウンの選択肢自体(『データ』シートの型一覧等)を参照している場合、その選択肢を
  **同じ呼び出し内で**書き換えていても、この判定は書き換え後の値と正しく比較する。
- 書き込み先セルが**既に数式(formula)を持っている場合は書き込みを拒否する**。
  Nablarch標準テンプレートは、PJ名/システム名/サブシステム名などのヘッダーを
  「変更履歴」シートの値を`=IF(INDIRECT(...))`で参照する数式にしている場合があり、
  これを知らずに上書きすると数式が失われる。
  数式セルへ書き込みたい場合のみ --force-formula-overwrite を指定する。
- **全件を先に検証し、1件でもエラーがあれば1セルも書き込まずに終了する(all-or-nothing)。**
  一部のセルだけ正常に書き込まれた中途半端な出力ファイルができることを防ぐため。
- **出力パスは必須。省略して元ファイルを直接上書きすることはできない**
  (誤って元ファイルを壊すと、記入要領を再確認しながらの再実行ができなくなるため)。
- **1セルに80文字以上の長文を改行・区切りなく書き込むと警告する(エラーにはしない)。**
  Nablarch標準テンプレートの自由記述欄は、1文ごとに別の行のセルに分けて書くのが公式サンプルの
  書き方であり、1セルへのべた書きは避けるべきであるため注意を促す。
- **書き込み先セルの表示形式が日付(例: `yyyy-mm-dd`)で、値が`YYYY-MM-DD`形式の文字列の場合は、
  Excelの日付型に変換してから書き込む。** 文字列のまま書き込むと、セルの見た目は日付形式でも
  実体は文字列のままになり、`変更履歴`シートの変更日をMAXで集計する表紙の最終更新日の数式等が
  正しく計算できなくなる。

使い方:
    python apply_mapping.py <元xlsxパス> <マッピングJSONパス> <出力xlsxパス> [--allow-outside-border] [--force-formula-overwrite]

マッピングJSONの形式:
{
  "sheets": {
    "シート名": {
      "A1": "値",
      "B2": 123,
      ...
    },
    "別のシート名": { ... }
  }
}
"""
import sys
import re
import json
import argparse
import datetime
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import get_merge_anchor, get_bordered_bbox, get_validations_map, save_with_shapes, ensure_utf8_stdio
from openpyxl.utils.cell import coordinate_from_string
from openpyxl.utils import column_index_from_string

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_FORMAT_RE = re.compile(r"[ymd]{2,}", re.IGNORECASE)


MIN_LENGTH_FOR_PARAGRAPH_CHECK = 80


def _check_paragraph_formatting(anchor, value):
    """
    複数の文・複数の内容を1つのセルに改行も区切りも無く詰め込んでいないかを確認する。
    Nablarch標準テンプレートの自由記述欄(取引概要・起動条件・前提事項等)は、
    1文(または一まとまりの内容)ごとに別の行のセル(例: H10, H12, H13...)に分けて書くのが
    公式サンプルの書き方であり、1つのセルに複数文をべた書きするのは見落とされやすいため、
    機械的に警告する。
    """
    if not isinstance(value, str):
        return None
    if len(value) < MIN_LENGTH_FOR_PARAGRAPH_CHECK:
        return None
    return (
        f"{anchor}に{len(value)}文字の長い文章が1セルにまとめて書き込まれています。"
        f"Nablarch標準テンプレートの自由記述欄は、1文(または一まとまりの内容)ごとに"
        f"別の行のセルに分けて書くのが公式サンプルの書き方です。対象テンプレートの記入要領を確認し、"
        f"複数のセルに分けるべきでないか検討してください。"
    )


def _coerce_date_if_needed(value, cell):
    """
    セルの表示形式が日付で、値が`YYYY-MM-DD`形式の文字列なら、Excelの日付型(date)に変換する。
    文字列のまま書き込むと、表示形式は日付でも実体は文字列のままになり、
    MAX関数等の数式で日付として集計されない(セルのテキスト扱いになるため無視される)。
    """
    if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
        return value
    number_format = cell.number_format or "General"
    if number_format == "General" or not _DATE_FORMAT_RE.search(number_format):
        return value
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return value


def apply_mapping(xlsx_path, mapping, output_path, allow_outside_border=False, force_formula_overwrite=False):
    wb = openpyxl.load_workbook(xlsx_path, data_only=False)

    report = {"written": [], "warnings": [], "errors": []}
    planned = []  # (sheet_name, anchor, value) のうち検証を通過したもの。この段階ではまだ書き込まない。

    for sheet_name, cell_map in mapping.get("sheets", {}).items():
        if sheet_name not in wb.sheetnames:
            report["errors"].append(f"シートが存在しません: {sheet_name}")
            continue
        ws = wb[sheet_name]

        bbox_row, bbox_col = get_bordered_bbox(ws)
        # pendingを渡すことで、プルダウンの選択肢自体(「データ」シートの型一覧等)を
        # 同じ呼び出し内で書き換える場合でも、更新後の値と比較して判定する
        # (更新前の古い選択肢と比較してしまう誤検知を防ぐ)。
        validations = get_validations_map(wb, ws, pending=mapping.get("sheets", {}))

        for coordinate, value in cell_map.items():
            try:
                col_str, row = coordinate_from_string(coordinate)
                col = column_index_from_string(col_str)
            except Exception:
                report["errors"].append(f"[{sheet_name}] 不正なセル指定: {coordinate}")
                continue

            if not allow_outside_border and bbox_row and bbox_col:
                if row > bbox_row or col > bbox_col:
                    report["errors"].append(
                        f"[{sheet_name}] {coordinate} はテンプレートの罫線設定範囲"
                        f"(最大 {bbox_row}行×{bbox_col}列)を超えています。"
                        f"表の行数が不足している可能性があるため書き込みを中止しました。"
                        f"(意図的な書き込みなら --allow-outside-border を指定)"
                    )
                    continue

            anchor = get_merge_anchor(ws, coordinate)
            anchor_cell = ws[anchor]

            if not force_formula_overwrite and anchor_cell.data_type == "f":
                report["errors"].append(
                    f"[{sheet_name}] {anchor} には数式が設定されています"
                    f"(現在の内容: {anchor_cell.value!r})。"
                    f"多くの場合、他シート(変更履歴等)の値を参照する仕組みのため、"
                    f"直接値を書き込むと数式が失われます。書き込みを中止しました。"
                    f"(意図的に上書きするなら --force-formula-overwrite を指定)"
                )
                continue

            if anchor in validations:
                allowed = validations[anchor]
                if str(value) not in allowed:
                    report["warnings"].append(
                        f"[{sheet_name}] {anchor} はプルダウン選択肢 {allowed} が設定されていますが、"
                        f"指定値 '{value}' は選択肢に含まれていません。"
                    )

            coerced_value = _coerce_date_if_needed(value, anchor_cell)
            if coerced_value != value:
                report["warnings"].append(
                    f"[{sheet_name}] {anchor} は日付形式のセルのため、"
                    f"文字列 '{value}' をExcelの日付型に変換して書き込みました。"
                )

            paragraph_warning = _check_paragraph_formatting(anchor, coerced_value)
            if paragraph_warning:
                report["warnings"].append(f"[{sheet_name}] {paragraph_warning}")

            planned.append((sheet_name, ws, anchor, coordinate, coerced_value))

    if report["errors"]:
        # all-or-nothing: 1件でもエラーがあれば、正常なセルも含めて一切書き込まない。
        report["saved"] = False
        return report

    if not planned:
        report["saved"] = False
        return report

    for sheet_name, ws, anchor, coordinate, value in planned:
        old_value = ws[anchor].value
        ws[anchor] = value
        report["written"].append({
            "sheet": sheet_name,
            "cell": anchor,
            "requested_cell": coordinate,
            "old_value": old_value,
            "new_value": value,
        })

    # 変更履歴シートにPJ名(E1)・サブシステム名(E3)を書いた場合、
    # 表紙のテキストボックス内プレースホルダー([プロジェクト名]/[サブシステム名])も
    # 併せて実値に置き換える(角括弧はそのまま残る)。
    change_history = mapping.get("sheets", {}).get("変更履歴", {})
    text_replacements = {}
    if "E1" in change_history:
        text_replacements["プロジェクト名"] = change_history["E1"]
    if "E3" in change_history:
        text_replacements["サブシステム名"] = change_history["E3"]

    save_with_shapes(wb, xlsx_path, output_path, text_replacements or None)
    report["saved"] = True
    return report


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xlsx_path")
    parser.add_argument("mapping_json_path")
    parser.add_argument("output_path")
    parser.add_argument("--allow-outside-border", action="store_true")
    parser.add_argument("--force-formula-overwrite", action="store_true")
    args = parser.parse_args()

    with open(args.mapping_json_path, encoding="utf-8") as f:
        mapping = json.load(f)

    report = apply_mapping(args.xlsx_path, mapping, args.output_path,
                            args.allow_outside_border, args.force_formula_overwrite)

    if report["errors"]:
        print(f"=== エラー {len(report['errors'])}件 → 1セルも書き込まずに中止しました ===")
        for e in report["errors"]:
            print(f"  x {e}")
        print("\n(all-or-nothingのため、上記以外の正常なセルも含め出力ファイルは作成していません)")
        sys.exit(1)

    if report["saved"]:
        print(f"=== 書き込み結果: {args.output_path} ===")
    else:
        print("=== 書き込み結果: 保存なし（マッピングJSONに有効な書き込みが1件もありませんでした） ===")
    print(f"書き込みセル数: {len(report['written'])}")
    for w in report["written"]:
        mark = " (結合セルのため書き込み先を変更)" if w["cell"] != w["requested_cell"] else ""
        print(f"  {w['sheet']}!{w['cell']}{mark} : {w['old_value']!r} -> {w['new_value']!r}")

    if report["warnings"]:
        print(f"\n=== 警告 {len(report['warnings'])}件 ===")
        for w in report["warnings"]:
            print(f"  ! {w}")


if __name__ == "__main__":
    main()
