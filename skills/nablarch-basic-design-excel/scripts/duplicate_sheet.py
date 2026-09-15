# -*- coding: utf-8 -*-
"""
「1インスタンス＝1シート」型のテンプレート（テーブル定義書の論理テーブル名シート、
外部インタフェース設計書(JSON)の【レコード名】シート、システム機能設計書の
複数ページ画面シート等）で、テンプレートのシートを複製するスクリプト。

このスクリプトは構造(結合セル・書式・入力規則・コメント)だけを複製し、
値は書き込まない(値の書き込みは複製後にapply_mapping.pyで行う)。

openpyxlのcopy_worksheet()の既知の制約への対応:
- 入力規則(プルダウン)は複製されない -> copy_data_validations()で明示的にコピーする(実機検証済み)
- セルコメントは複製される(実機検証済み。対応不要)
- 結合セル・書式・行高・列幅は複製される(実機検証済み)

使い方:
    python duplicate_sheet.py <元xlsxパス> <複製元シート名> <新しいシート名> <出力xlsxパス>
        [--before-sheet <このシート名の直前に配置>]

出力パスは必須(元ファイルを直接上書きする事故を防ぐため)。

例(テーブル定義書に「顧客」テーブル用のシートを追加する場合):
    python duplicate_sheet.py テーブル定義書_xxx.xlsx 論理テーブル名 顧客 出力.xlsx --before-sheet データ
"""

import sys
import argparse
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import copy_data_validations, save_with_shapes, ensure_utf8_stdio


def duplicate_sheet(
    xlsx_path, source_sheet, new_sheet_name, output_path, before_sheet=None
):
    wb = openpyxl.load_workbook(xlsx_path)

    if source_sheet not in wb.sheetnames:
        raise ValueError(f"複製元シートが存在しません: {source_sheet}")
    if new_sheet_name in wb.sheetnames:
        raise ValueError(
            f"シート名が既に存在します(重複はできません): {new_sheet_name}"
        )

    src_ws = wb[source_sheet]
    new_ws = wb.copy_worksheet(src_ws)
    new_ws.title = new_sheet_name

    dv_count = copy_data_validations(src_ws, new_ws)

    if before_sheet is not None:
        if before_sheet not in wb.sheetnames:
            raise ValueError(
                f"--before-sheetで指定されたシートが存在しません: {before_sheet}"
            )
        target_index = wb.sheetnames.index(before_sheet)
        current_index = wb.sheetnames.index(new_sheet_name)
        wb.move_sheet(new_sheet_name, offset=(target_index - current_index))

    save_with_shapes(wb, xlsx_path, output_path)

    return {
        "new_sheet": new_sheet_name,
        "data_validations_copied": dv_count,
        "sheet_order": wb.sheetnames,
    }


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("xlsx_path")
    parser.add_argument("source_sheet")
    parser.add_argument("new_sheet_name")
    parser.add_argument("output_path")
    parser.add_argument("--before-sheet", default=None)
    args = parser.parse_args()

    result = duplicate_sheet(
        args.xlsx_path,
        args.source_sheet,
        args.new_sheet_name,
        args.output_path,
        args.before_sheet,
    )

    print(f"=== シート複製結果: {args.output_path} ===")
    print(f"新規シート: {result['new_sheet']}")
    print(f"複製した入力規則(プルダウン)の数: {result['data_validations_copied']}")
    print(f"複製後のシート順: {result['sheet_order']}")
    print(
        "\n※このシートにはまだ値が入っていません。apply_mapping.pyで値を反映してください。"
    )
    print(
        "※目次シートは自動更新されません。記入要領_共通シート.mdの案内に従い手動で追記してください。"
    )


if __name__ == "__main__":
    main()
