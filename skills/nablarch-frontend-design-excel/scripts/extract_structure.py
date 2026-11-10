# -*- coding: utf-8 -*-
"""
Excelテンプレートの構造(結合セル/背景色/フォント色/罫線/行列サイズ)を
Markdownのリファレンスとして書き出すツール。

Claude for Microsoft 365 (Claude in Excel) が編集する際に、
「どこが構造として保護されるべきか」を事前に伝えるための資料を作る。

使い方:
    python extract_structure.py <対象xlsxパス> <出力md名>

例(テーブル一覧.xlsxの構造を再抽出する場合):
    python extract_structure.py テーブル一覧.xlsx 構造メモ_テーブル一覧.md
"""

import sys
import io
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio


def color_str(color):
    if color is None:
        return None
    ctype = getattr(color, "type", None)
    if ctype == "rgb":
        rgb = color.rgb
        if isinstance(rgb, str) and rgb not in (None, "00000000"):
            return rgb
        return None
    if ctype == "theme":
        return f"theme{color.theme}(tint={round(color.tint, 3)})"
    if ctype == "indexed":
        return f"indexed{color.indexed}"
    if ctype == "auto":
        return None
    return None


def summarize_fills(ws, max_row, max_col):
    """背景色ごとに、どのセル範囲で使われているかを集約する"""
    color_cells = {}
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            fill = cell.fill
            if fill is None or fill.fgColor is None:
                continue
            col = color_str(fill.fgColor)
            if not col or fill.patternType is None:
                continue
            color_cells.setdefault(col, []).append(cell.coordinate)
    return color_cells


def summarize_fonts(ws, max_row, max_col):
    """既定と異なるフォント色ごとに、使われているセルを集約する"""
    color_cells = {}
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            font = cell.font
            if font is None or font.color is None:
                continue
            col = color_str(font.color)
            if not col:
                continue
            color_cells.setdefault(col, []).append(cell.coordinate)
    return color_cells


def compress_ranges(coords):
    """セル座標リストを、行範囲ごとに簡潔な文字列へまとめる(件数が多い場合の可読性対策)"""
    if len(coords) <= 20:
        return ", ".join(coords)
    return f"{coords[0]} 〜 {coords[-1]} 等、計{len(coords)}セル"


def resolve_list_values(wb, formula1):
    """
    データ入力規則(type='list')のformula1を実際の選択肢に解決する。
    - リテラル指定 ("A,B,C" 形式) はそのまま分解
    - 名前付き範囲・シート参照 (例: データ!$A$2:$A$7) は実際のセル値を読みに行く
    """
    if formula1 is None:
        return None
    f = formula1.strip()
    if f.startswith('"') and f.endswith('"'):
        return [v for v in f[1:-1].split(",") if v != ""]

    ref = f.lstrip("=")
    # 名前付き範囲か判定
    defined = wb.defined_names.get(ref) if hasattr(wb.defined_names, "get") else None
    if defined is not None:
        ref = defined.attr_text

    if "!" in ref:
        sheet_part, cell_part = ref.rsplit("!", 1)
        sheet_name = sheet_part.strip("'")
        if sheet_name in wb.sheetnames:
            try:
                cells = wb[sheet_name][cell_part.replace("$", "")]
                values = []
                for row in cells:
                    row_iter = row if isinstance(row, tuple) else (row,)
                    for c in row_iter:
                        if c.value is not None:
                            values.append(str(c.value).strip())
                return values
            except Exception:
                return [f"(解決不可: {ref})"]
    return [f"(未解決の参照: {f})"]


def detect_label_value_pairs(ws, max_row, max_col):
    """
    ラベルセル(文字列が入っている結合セル)と、隣接する空セル(値入力用と推測される)の
    ペアを検出する。ヒューリスティックであり完全ではない。あくまで構造メモ上の「候補」
    であって、実際にそこへ値を書くべきかは記入要領・公式サンプルとの突合せが必要。

    検出パターン:
    (a) 横並び: ラベル結合セルの右隣に、空の結合セル(または空セル)が1つ隣接している
        (例: 表紙の「項目名: [値]」形式)
    (b) 縦長ラベル: 複数行にまたがるラベル結合セル(例: D10:G29)の右隣の列に、
        同じ行範囲で複数の空セルが並んでいる
        (例: システム機能設計書の「取引概要」等、D列はラベル・H列に1文ずつ記入する形式。
        この形式を見落とし、D列(ラベル)側に値を書き込んでしまいやすい)
    """
    merges = list(ws.merged_cells.ranges)
    merge_covering = {}
    for m in merges:
        for r in range(m.min_row, m.max_row + 1):
            for c in range(m.min_col, m.max_col + 1):
                merge_covering[(r, c)] = m

    def cell_text(row, col):
        cell = ws.cell(row=row, column=col)
        v = cell.value
        if cell.data_type == "f":
            return None
        if isinstance(v, str) and v.strip():
            return v.strip()
        return None

    def is_cell_empty(row, col):
        return ws.cell(row=row, column=col).value is None

    pairs = []
    seen_labels = set()

    for m in merges:
        if m.min_row > max_row or m.min_col > max_col:
            continue
        label = cell_text(m.min_row, m.min_col)
        if not label or (m.min_row, m.min_col) in seen_labels:
            continue

        height = m.max_row - m.min_row + 1
        right_col = m.max_col + 1
        if right_col > max_col:
            continue

        # パターン(b): 縦長ラベル -> 右隣列の複数空セルを値エリアとする
        if height >= 3:
            empties = [
                r
                for r in range(m.min_row, m.max_row + 1)
                if is_cell_empty(r, right_col)
            ]
            all_unmerged = all(
                (r, right_col) not in merge_covering
                or merge_covering[(r, right_col)].min_col
                == merge_covering[(r, right_col)].max_col
                for r in range(m.min_row, m.max_row + 1)
            )
            if all_unmerged and len(empties) >= height * 0.6:
                col_letter = get_column_letter(right_col)
                pairs.append(
                    {
                        "label": label,
                        "label_cell": f"{get_column_letter(m.min_col)}{m.min_row}",
                        "value_area": f"{col_letter}{m.min_row}〜{col_letter}{m.max_row}",
                        "pattern": "縦長ラベル(値は右隣の列に1行1件で記入)",
                    }
                )
                seen_labels.add((m.min_row, m.min_col))
                continue

        # パターン(a): 横並び -> 右隣の結合(または単独)セルが空なら値セルとする
        right_merge = merge_covering.get((m.min_row, right_col))
        if right_merge is not None:
            if right_merge.min_row == m.min_row and is_cell_empty(
                right_merge.min_row, right_merge.min_col
            ):
                pairs.append(
                    {
                        "label": label,
                        "label_cell": f"{get_column_letter(m.min_col)}{m.min_row}",
                        "value_area": str(right_merge),
                        "pattern": "横並び(ラベル:値)",
                    }
                )
                seen_labels.add((m.min_row, m.min_col))
        elif is_cell_empty(m.min_row, right_col):
            pairs.append(
                {
                    "label": label,
                    "label_cell": f"{get_column_letter(m.min_col)}{m.min_row}",
                    "value_area": f"{get_column_letter(right_col)}{m.min_row}",
                    "pattern": "横並び(ラベル:値)",
                }
            )
            seen_labels.add((m.min_row, m.min_col))

    return pairs


def summarize_validations(wb, ws):
    """入力規則(プルダウン等)を、対象セル範囲と許容値のセットで一覧化する"""
    results = []
    for dv in ws.data_validations.dataValidation:
        entry = {
            "range": str(dv.sqref),
            "type": dv.type,
        }
        if dv.type == "list":
            entry["values"] = resolve_list_values(wb, dv.formula1)
        else:
            entry["formula1"] = dv.formula1
            entry["formula2"] = dv.formula2
        results.append(entry)
    return results


def analyze_sheet(wb, ws):
    max_row = min(ws.max_row, 200)
    max_col = min(ws.max_column, 40)

    lines = []
    lines.append(f"### シート『{ws.title}』")
    lines.append("")
    lines.append(
        f"- 使用範囲の目安: 最大 {max_row}行 × {max_col}列（それ以降は未フォーマット領域の可能性あり）"
    )

    # 結合セル
    merges = sorted(str(m) for m in ws.merged_cells.ranges)
    lines.append(f"- 結合セル数: {len(merges)}")
    if merges:
        lines.append(
            "  - 一覧: " + ", ".join(merges[:60]) + (" ..." if len(merges) > 60 else "")
        )

    # 行の高さ(既定と異なるもの)
    custom_heights = {
        r: dim.height
        for r, dim in ws.row_dimensions.items()
        if dim.height is not None and r <= max_row
    }
    if custom_heights:
        lines.append(
            f"- 行高が個別指定されている行数: {len(custom_heights)}（例: "
            + ", ".join(f"{r}行={h}" for r, h in list(custom_heights.items())[:10])
            + " ）"
        )

    # 列幅
    col_widths = {
        (
            get_column_letter(idx if isinstance(idx, int) else 0)
            if isinstance(idx, int)
            else idx
        ): dim.width
        for idx, dim in ws.column_dimensions.items()
        if dim.width is not None
    }
    if col_widths:
        lines.append(
            "- 列幅（個別指定分）: "
            + ", ".join(f"{k}列={v:.1f}" for k, v in list(col_widths.items())[:20])
        )

    # 背景色
    fills = summarize_fills(ws, max_row, max_col)
    if fills:
        lines.append(f"- 背景色の種類: {len(fills)}種")
        for color, cells in fills.items():
            lines.append(f"  - `#{color}` : {compress_ranges(cells)}")

    # フォント色
    fonts = summarize_fonts(ws, max_row, max_col)
    if fonts:
        lines.append(f"- フォント色の種類（既定色以外）: {len(fonts)}種")
        for color, cells in fonts.items():
            lines.append(f"  - `#{color}` : {compress_ranges(cells)}")

    # 罫線が引かれているセル範囲(概略。全体に罫線がある場合は範囲のみ通知)
    bordered = []
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            b = cell.border
            if b and any(
                [
                    b.top and b.top.style,
                    b.bottom and b.bottom.style,
                    b.left and b.left.style,
                    b.right and b.right.style,
                ]
            ):
                bordered.append(cell.coordinate)
    if bordered:
        lines.append(f"- 罫線が設定されているセル: {compress_ranges(bordered)}")

    # ラベル→値入力セルの候補(ヒューリスティック検出。要サンプル突合せ)
    label_pairs = detect_label_value_pairs(ws, max_row, max_col)
    if label_pairs:
        lines.append(
            f"- ラベル→値入力セルの候補: {len(label_pairs)}件"
            "（※機械的な推測です。実際にそこへ書くかは記入要領・公式サンプルで必ず確認すること）"
        )
        for p in label_pairs:
            lines.append(
                f"  - 『{p['label']}』({p['label_cell']}) → {p['value_area']} 【{p['pattern']}】"
            )

    # 入力規則(プルダウン等) - 自由記述にせず、必ずこの選択肢から選ぶ必要がある
    validations = summarize_validations(wb, ws)
    if validations:
        lines.append(
            f"- 入力規則（プルダウン等）: {len(validations)}件 ※記入時はここに列挙した選択肢以外を入力しないこと"
        )
        for v in validations:
            if v["type"] == "list":
                vals = v.get("values") or []
                lines.append(f"  - `{v['range']}` : プルダウン選択肢 = {vals}")
            else:
                lines.append(
                    f"  - `{v['range']}` : 種別={v['type']}, 条件式1={v.get('formula1')}, 条件式2={v.get('formula2')}"
                )

    # 条件付き書式
    if ws.conditional_formatting._cf_rules:
        lines.append(
            f"- 条件付き書式が設定されている範囲: {list(ws.conditional_formatting._cf_rules.keys())}"
        )

    # シート保護
    if ws.protection.sheet:
        lines.append("- シート保護: 有効（入力可能セルが制限されている可能性あり）")

    lines.append("")
    return "\n".join(lines)


def main():
    ensure_utf8_stdio()
    xlsx_path = sys.argv[1]
    out_path = sys.argv[2]

    wb = openpyxl.load_workbook(xlsx_path, data_only=False)

    out = io.StringIO()
    out.write(f"# 構造メモ: {xlsx_path}\n\n")
    out.write(
        "このファイルは元のExcelテンプレートの構造（結合セル・背景色・フォント色・行列サイズ・罫線・入力規則）を\n"
    )
    out.write(
        "機械的に抽出したものです。編集時にこれらを変更しないよう注意してください。\n"
    )
    out.write(
        "特に「入力規則（プルダウン等）」に記載された項目は、一覧にある選択肢以外の値を入力しないこと。\n\n"
    )
    out.write(f"シート一覧: {', '.join(wb.sheetnames)}\n\n")

    for ws in wb.worksheets:
        out.write(analyze_sheet(wb, ws))
        out.write("\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out.getvalue())

    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
