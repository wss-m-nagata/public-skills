# -*- coding: utf-8 -*-
"""
2つのExcelファイル(反映前・反映後)を比較し、値以外の構造(結合セル・背景色・
フォント色・行高・列幅・罫線・数式・入力規則・シート保護・図形)が変化していないかを検証する。

数式セルの内容(data_type=='f')も比較する。ただしこれは数式の「文字列」が変化したかを
見ているだけで、セル内部に保存された計算結果のキャッシュ値までは比較できない
(openpyxlで保存すると通常キャッシュは失われるが、テンプレート側でfullCalcOnLoad=Trueが
設定されていれば、Excelで開いた際に自動再計算されるため実害は小さい)。

apply_mapping.py / duplicate_sheet.py / extend_table_rows.py で処理した後、
必ずこのスクリプトで検証すること。これらのスクリプトはsave_with_shapes()を通じて
図形の復元を自動で行うが、復元に失敗するケース(元にしたファイルの指定間違い等)を
検知するため、このスクリプト側でも独立して図形の有無を確認する。

使い方:
    python verify_layout.py <反映前xlsxパス> <反映後xlsxパス>

終了コード:
    0 = 構造の差分なし(合格)
    1 = 構造に差分あり(不合格。詳細を標準出力に表示)
"""
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import snapshot_sheet_structure, ensure_utf8_stdio
from restore_shapes import sheets_with_drawings, shape_anchor_counts


def diff_sheet(name, before, after):
    diffs = []

    if before["dimensions"] != after["dimensions"]:
        diffs.append(f"シート範囲(行数×列数)が変化: {before['dimensions']} -> {after['dimensions']}")

    if before["merged_cells"] != after["merged_cells"]:
        added = sorted(set(after["merged_cells"]) - set(before["merged_cells"]))
        removed = sorted(set(before["merged_cells"]) - set(after["merged_cells"]))
        if added:
            diffs.append(f"結合セルが追加された: {added}")
        if removed:
            diffs.append(f"結合セルが解除された: {removed}")

    if before["row_heights"] != after["row_heights"]:
        diffs.append("行の高さが変化した箇所があります")

    if before["col_widths"] != after["col_widths"]:
        diffs.append("列の幅が変化した箇所があります")

    fill_diff = {k: (before["fills"].get(k), after["fills"].get(k))
                 for k in set(before["fills"]) | set(after["fills"])
                 if before["fills"].get(k) != after["fills"].get(k)}
    if fill_diff:
        diffs.append(f"背景色が変化したセル: {fill_diff}")

    font_diff = {k: (before["fonts"].get(k), after["fonts"].get(k))
                 for k in set(before["fonts"]) | set(after["fonts"])
                 if before["fonts"].get(k) != after["fonts"].get(k)}
    if font_diff:
        diffs.append(f"フォント色が変化したセル: {font_diff}")

    removed_borders = before["borders"] - after["borders"]
    if removed_borders:
        diffs.append(f"罫線が消えたセル: {sorted(removed_borders)}")

    formula_diff = {k: (before["formulas"].get(k), after["formulas"].get(k))
                    for k in set(before["formulas"]) | set(after["formulas"])
                    if before["formulas"].get(k) != after["formulas"].get(k)}
    if formula_diff:
        diffs.append(
            f"数式が変化・消失したセル: {formula_diff}"
            f"（意図的に--force-formula-overwriteで上書きした場合を除き、想定外の数式破壊の可能性があります）"
        )

    if before["validations"] != after["validations"]:
        diffs.append(f"入力規則(プルダウン)が変化: {before['validations']} -> {after['validations']}")

    if before["sheet_protection"] != after["sheet_protection"]:
        diffs.append("シート保護の設定が変化しました")

    return diffs


def verify(before_path, after_path):
    wb_before = openpyxl.load_workbook(before_path, data_only=False)
    wb_after = openpyxl.load_workbook(after_path, data_only=False)

    all_diffs = {}

    if wb_before.sheetnames != wb_after.sheetnames:
        all_diffs["__workbook__"] = [
            f"シート構成が変化: {wb_before.sheetnames} -> {wb_after.sheetnames}"
        ]

    for name in wb_before.sheetnames:
        if name not in wb_after.sheetnames:
            continue
        before = snapshot_sheet_structure(wb_before, wb_before[name])
        after = snapshot_sheet_structure(wb_after, wb_after[name])
        diffs = diff_sheet(name, before, after)
        if diffs:
            all_diffs[name] = diffs

    # 図形(テキストボックス等)が失われていないか・不自然に増えていないかを確認
    # openpyxlはこれをセル単位の構造としては扱わないため、上のsnapshot_sheet_structureでは検出できない
    before_shapes = sheets_with_drawings(before_path)
    after_shapes = sheets_with_drawings(after_path)
    lost_shapes = before_shapes - after_shapes
    if lost_shapes:
        all_diffs.setdefault("__workbook__", []).append(
            f"図形(テキストボックス等)が失われたシート: {sorted(lost_shapes)}"
            f"（restore_shapes.pyによる復元に失敗した可能性。表紙の「関係者外秘」等の表示が"
            f"消えていないか目視でも確認すること）"
        )

    # 図形の個数(シートごと)が変化していないかを確認。
    # 有無だけでなく個数を見るのは、「元ファイル」に誤ってサンプル/実例ファイルを指定した場合、
    # 図形自体は失われないが、古い図形が新しい図形に上乗せされて増える(表紙の二重表示)ことを
    # 検知するため。
    before_counts = shape_anchor_counts(before_path)
    after_counts = shape_anchor_counts(after_path)
    increased = {
        name: (before_counts.get(name, 0), after_counts[name])
        for name in after_counts
        if after_counts[name] > before_counts.get(name, 0)
    }
    if increased:
        all_diffs.setdefault("__workbook__", []).append(
            f"図形の個数が増えたシート: {increased}"
            f"（`insert_flow_diagram.py`で処理フロー図を意図的に追加した場合は正常な差分。"
            f"意図した追加でない場合は、「元ファイル」にsample/実例ファイルを誤って指定した"
            f"可能性がある。古い図形ベースの表紙が新しいセルベースの表紙に重なって二重表示される"
            f"事故が起きるため、restore_shapes.py・duplicate_sheet.py・apply_mapping.py等の"
            f"「元xlsxパス」引数を確認すること）"
        )

    return all_diffs


def main():
    ensure_utf8_stdio()
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)

    before_path, after_path = sys.argv[1], sys.argv[2]
    diffs = verify(before_path, after_path)

    if not diffs:
        print("OK: 構造(レイアウト)の差分はありません。値のみが反映されています。")
        sys.exit(0)

    print("NG: 構造に差分が見つかりました。")
    for sheet, sheet_diffs in diffs.items():
        print(f"\n[{sheet}]")
        for d in sheet_diffs:
            print(f"  - {d}")
    sys.exit(1)


if __name__ == "__main__":
    main()
