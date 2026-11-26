"""デスクトップ版Excelが使えない環境で基本方針検討資料を生成する。"""

import argparse
import json
import re
from datetime import date
from io import BytesIO
from math import ceil, floor
from pathlib import Path
from unicodedata import east_asian_width

try:
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.hyperlink import Hyperlink
except ModuleNotFoundError as exc:
    if exc.name != "openpyxl":
        raise
    raise SystemExit("Python版にはopenpyxlが必要です。SKILL.mdの準備手順を参照してください。") from exc

from workbook_drawings import Diagram, attach_drawings, flow, information_transfer


_TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "concept-workbook.xlsx"
_SHEETS = ["概要", "スコープ", "To-Be", "検討事項"]
_END = 38
_SHIFT = 38
_DRAWING_COL = 44
_COLUMN_WIDTH = 3.625  # 同梱ひな形の標準フォントで約29ピクセル。
_COLUMN_POINTS = 21.75
_ROW_POINTS = 13.5
_FONT = "ＭＳ 明朝"
_INPUT = "FFF6EA"
_HEADER = "E6E6E6"
_GRAY = "C0C0C0"
_LINE = Side(style="thin", color="A6A6A6")
_DOUBLE = Side(style="double", color="000000")
_NUMBER = {"No.", "No", "番号"}


def _text(value):
    """セルの文章は句点ごとに改行し、空欄は空の文字列とする。"""
    return "" if value is None else re.sub(r"。(?=[^\r\n])", "。\n", str(value))


def _line_count(value, capacity):
    """全角文字を考慮してセル内の折り返し行数を見積もる。"""
    return sum(max(1, ceil(sum(2 if east_asian_width(c) in "WF" else 1 for c in line)
                           / capacity)) for line in (_text(value).split("\n")))


def _span(sheet, row, start, end, value=None, *, fill=None, border=False, size=11,
          bold=False, center=False, wrap=True, formula=False, last_row=None):
    """結合範囲に書式を付け、数式と入力文字列を区別して書き込む。"""
    bottom = row if last_row is None else last_row
    cell = sheet.cell(row, start)
    cell.font = Font(name=_FONT, size=size, bold=bold)
    cell.alignment = Alignment(horizontal="center" if center else "left", vertical="center",
                               wrap_text=wrap, shrink_to_fit=not wrap)
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    if border:
        cell.border = Border(left=_LINE, right=_LINE, top=_LINE, bottom=_LINE)
    if value is not None and value != "":
        cell.value = value if formula else _text(value)
        if not formula:
            cell.data_type = "s"
    if start != end or bottom != row:
        sheet.merge_cells(start_row=row, end_row=bottom, start_column=start, end_column=end)
    return cell


def _preliminaries(book, data):
    """同梱ひな形の表紙と変更履歴を埋め、使わない書式シートを外す。"""
    del book["書式"]
    cover = book["表紙"]
    for address, key in (("D12", "project"), ("D14", "title"), ("D16", "position"), ("D19", "version")):
        if data.get(key):
            cover[address] = _text(data[key])
            cover[address].data_type = "s"

    history = book["変更履歴"]
    for region in list(history.merged_cells.ranges):
        if region.max_row <= 3:
            history.unmerge_cells(str(region))
    for cells in history.iter_rows(min_row=1, max_row=3, max_col=7):
        for cell in cells:
            cell.value = None
            cell.border = Border()
            cell.fill = PatternFill()
    for row, (label, key, right) in enumerate(zip(
        ("PJ名", "システム名", "サブシステム名"),
        ("project", "system", "subsystem"), ("成果物名", "作成", "変更"),
    ), 1):
        _span(history, row, 1, 2, label, fill=_GRAY, border=True, size=9)
        _span(history, row, 3, 4, data.get(key), border=True, size=9, wrap=False)
        _span(history, row, 5, 5, right, fill=_GRAY, border=True, size=9)
        _span(history, row, 6, 7, data["title"] if row == 1 else None, border=True, size=9)

    def history_stamp(row):
        """変更履歴の行からヘッダー用の日付と氏名を表示する。"""
        return f'=TEXT(C{row},"yyyy/mm/dd")&IF(G{row}="","","　"&G{row})'

    history["F2"] = history_stamp(8)
    if len(data["history"]) > 1:
        history["F3"] = history_stamp(7 + len(data["history"]))
    history.column_dimensions["A"].width = 4.2
    history.row_dimensions[1].height = 20
    history.row_dimensions[4].height = 28
    for row, entry in enumerate(data["history"], 8):
        history.cell(row, 1, row - 7)
        for column, key in ((2, "version"), (4, "category"), (5, "area"), (6, "summary"), (7, "author")):
            cell = history.cell(row, column)
            cell.value = _text(entry.get(key)) or None
            if cell.value is not None:
                cell.data_type = "s"
        history.cell(row, 3).value = date.fromisoformat(entry["date"])
        history.cell(row, 3).number_format = "yyyy/mm/dd"
        history.row_dimensions[row].height = max(26, _line_count(entry.get("summary"), 45) * 16 + 4)
    for column in range(1, 8):
        for row in (4, 7):
            cell = history.cell(row, column)
            cell.fill = PatternFill()
            cell.font = Font(name=_FONT, size=cell.font.sz or 11)
        history.cell(7, column).border = Border(bottom=_DOUBLE)
        history.cell(8, column).border = Border(top=_DOUBLE)
    history.print_area = f"A1:G{max(15, 7 + len(data['history']))}"


def _common_header(sheet):
    """変更履歴を参照する本文共通ヘッダーを作る。"""
    for row, (left, right) in enumerate(zip(
        ("PJ名", "システム名", "サブシステム名"), ("成果物名", "作成", "変更"),
    ), 1):
        _span(sheet, row, 2, 7, left, size=9, fill=_GRAY, border=True)
        _span(sheet, row, 22, 27, right, size=9, fill=_GRAY, border=True)
        for start, end, field in ((8, 21, "C"), (28, _END, "F")):
            ref = f"'変更履歴'!{field}{row}"
            _span(sheet, row, start, end, f'=IF({ref}="","",{ref})',
                  size=9, border=True, formula=True)
        sheet.row_dimensions[row].height = 17


def _write_table(sheet, row, start, block, first_number):
    """番号、記入欄、記載例を対にし、表の終わりの次の行を返す。"""
    columns = block["columns"]
    skip = int(columns[0] in _NUMBER)
    content = columns[skip:]
    hints = block.get("prefillColumns", [])
    responses = [s for s in block.get("responses", []) if s and s != "作成者記入欄"]
    entry_headers = [
        s.replace("（仮説）", "").replace("の例", "").replace("質問例", "質問")
        .replace("現時点の案・", "") for s in content
    ]
    if not content or len(content) + len(responses) > 6 or set(hints) - set(content):
        raise ValueError("表の列または記入欄へ転記する列が不正です。")
    if not block["rows"] or any(len(item) != len(columns) for item in block["rows"]):
        raise ValueError("表には列数のそろったデータ行が必要です。")

    heights = [26] * (1 + len(block["rows"]))
    for shift, headings in ((0, entry_headers + responses), (_SHIFT, content)):
        weights = [
            2 if h in ("ID", "工程ID", "状態", "対象")
            else 6 if re.search("記入欄|合意内容|詳細|備考|留意点|現状|説明|内容|方針|確認したい", h)
            else 4 for h in headings
        ]
        cursor = start + shift
        headers = ["No."] + headings
        for index, heading in enumerate(headers):
            width = 1 if index == 0 else max(1, (_END - start) * weights[index - 1] // sum(weights))
            end = _END + shift if index == len(headings) else cursor + width - 1
            _span(sheet, row, cursor, end, heading, fill=_HEADER, border=True,
                  bold=True, center=index == 0, wrap=index != 0)
            capacity = max(3, 3 * (end - cursor + 1) - 1)
            heights[0] = max(heights[0], 15 * _line_count(heading, capacity) + 7)
            for offset, item in enumerate(block["rows"], 1):
                hint = index > 0 and index <= len(content) and content[index - 1] in hints
                value = first_number + offset - 1 if index == 0 else (
                    item[index - 1 + skip] if shift or hint else None
                )
                _span(sheet, row + offset, cursor, end, value, border=True,
                      fill=_INPUT if not shift and index and not (hint and value) else None,
                      center=index == 0, wrap=index != 0)
                heights[offset] = max(heights[offset], 15 * _line_count(value, capacity) + 7)
            cursor = end + 1
    for offset, height in enumerate(heights):
        sheet.row_dimensions[row + offset].height = min(344, height)
    return row + len(heights) + 1


def _write_notes(sheet, row, start, notes):
    """右に説明をまとめ、左に対応する記入余白を置く。"""
    text = "\n".join(notes)
    _span(sheet, row, start, _END, fill=_INPUT, border=True)
    _span(sheet, row, start + _SHIFT, _END + _SHIFT, text)
    sheet.row_dimensions[row].height = min(344, max(42, 16 * _line_count(text, 94) + 8))
    return row + 1


def _write_diagram(sheet, diagram, row, block):
    """図形の配置に必要な高さを確保し、左側に記入用の枠を作る。"""
    _span(sheet, row, 5, _END, block.get("entryTitle", "流れを記入"), bold=True)
    _span(sheet, row, 43, 76, block["title"], bold=True)
    sheet.row_dimensions[row].height = 24
    sheet.row_dimensions[row + 1].height = 7
    row += 2
    diagram.x = (_DRAWING_COL - 1) * _COLUMN_POINTS
    # Excelで行高が1ピクセル単位に丸められた後の座標を使用する。
    diagram.y = sum(
        floor((sheet.row_dimensions[i].height or _ROW_POINTS) / 0.75) * 0.75
        for i in range(1, row)
    )
    width = (77 - _DRAWING_COL) * _COLUMN_POINTS
    render = flow if block["kind"] == "flow" else information_transfer
    height = render(diagram, block, width)
    end = row + ceil(height / _ROW_POINTS) - 1
    for index in range(row, end + 1):
        sheet.row_dimensions[index].height = _ROW_POINTS
    _span(sheet, row, 6, _END, fill=_INPUT, border=True, last_row=end)
    return end + 2


def _write_sheet(book, index, spec):
    """本文シートを構成し、図形を格納したオブジェクトを返す。"""
    sheet = book.create_sheet(spec["name"])
    sheet.sheet_format.defaultRowHeight = _ROW_POINTS
    sheet.sheet_format.defaultColWidth = _COLUMN_WIDTH
    # ExcelとLibreOfficeのどちらでも、列の実幅を図形座標とそろえる。
    sheet.column_dimensions.group("A", "BX", outline_level=0)
    sheet.column_dimensions["A"].width = _COLUMN_WIDTH
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 90
    _common_header(sheet)
    _span(sheet, 5, 2, 2, index, size=17, bold=True)
    _span(sheet, 5, 3, _END, spec["name"], size=17, bold=True)
    _span(sheet, 5, 40, 76, "こちらの記載例（参考・印刷範囲外）", size=17, bold=True)
    sheet.row_dimensions[5].height = 28
    intro = spec.get("intro") or "色付きの欄にご記入ください。"
    _span(sheet, 6, 4, _END, intro)
    _span(sheet, 6, 40, 76,
          "提示側の想定に基づく記載例です。実際の状況に合わせて、左側で観点や内容を修正・追加・削除できます。")
    sheet.row_dimensions[6].height = max(43, 17 * _line_count(intro, 103) + 5)
    link = _span(sheet, 4, 40, 44, "← 記入欄")
    link.hyperlink = Hyperlink(ref=link.coordinate, location=f"'{sheet.title}'!A1")
    link.font = Font(name=_FONT, size=11, color="0563C1", underline="single")

    diagram = Diagram()
    row = 8
    next_number = 1
    print_starts = [1]
    for section in spec["sections"]:
        if section.get("pageBreakBefore"):
            print_starts.append(row)
        for shift in (0, _SHIFT):
            _span(sheet, row, 3 + shift, 3 + shift, section["number"], bold=True, wrap=False)
            _span(sheet, row, 4 + shift, _END + shift, section["title"], size=13, bold=True)
        sheet.row_dimensions[row].height = 25
        row += 1
        column = 5
        notes = []
        for block in section["blocks"]:
            kind = block["kind"]
            if kind == "note":
                notes.append(block["text"])
                continue
            if notes:
                row = _write_notes(sheet, row, column, notes)
                notes.clear()
            if kind == "label":
                label = block["text"]
                entry = label.replace("現状の想定", "現在の業務").replace("情報源の例", "情報源")
                _span(sheet, row, 5, _END, entry, bold=True)
                _span(sheet, row, 43, 76, label, bold=True)
                sheet.row_dimensions[row].height = 22
                row += 1
                column = 6
            elif kind == "table":
                row = _write_table(sheet, row, column, block, next_number)
                next_number += len(block["rows"])
            elif kind in ("flow", "information-transfer"):
                row = _write_diagram(sheet, diagram, row, block)
            else:
                raise ValueError(f"不明な本文の種類です: {kind}")
        if notes:
            row = _write_notes(sheet, row, column, notes)
        row += 1

    ends = [start - 2 for start in print_starts[1:]] + [row - 1]
    sheet.print_area = [f"A{start}:AL{end}" for start, end in zip(print_starts, ends)]
    sheet.print_title_rows = "1:3"
    sheet.print_options.horizontalCentered = True
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1
    if len(diagram.root):
        diagram.align_to_cells(
            _COLUMN_POINTS, [
                floor((sheet.row_dimensions[i].height or _ROW_POINTS) / 0.75) * 0.75
                for i in range(1, row + 1)
            ],
        )
    return diagram


def main():
    """PowerShell版と同じ入力JSONから、同梱ひな形を使ってExcelを生成する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-workbook", type=Path, required=True)
    args = parser.parse_args()
    target = args.output_workbook
    try:
        if target.suffix.lower() != ".xlsx" or target.exists():
            raise ValueError("未作成の .xlsx を指定してください。")
        data = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
        if [spec["name"] for spec in data["sheets"]] != _SHEETS:
            raise ValueError("指定の順序で本文4シートを用意してください。")
        history = data["history"]
        if not 1 <= len(history) <= 26 or history[-1]["version"] != data["version"]:
            raise ValueError("変更履歴は1～26行とし、末尾の版数を表紙とそろえてください。")
        book = load_workbook(_TEMPLATE)
        _preliminaries(book, data)
        drawings = {}
        for index, spec in enumerate(data["sheets"], 1):
            if not spec["sections"] or any(not all(s.get(k) for k in ("number", "title", "blocks"))
                                            for s in spec["sections"]):
                raise ValueError("節の項番・見出し・本文を用意してください。")
            diagram = _write_sheet(book, index, spec)
            if len(diagram.root):
                drawings[index + 2] = diagram
        book.active = 0
        buffer = BytesIO()
        book.save(buffer)
        output = attach_drawings(buffer, drawings) if drawings else buffer.getvalue()
        with target.open("xb") as file:
            file.write(output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Excelを作成できませんでした。{exc}\n")
    print(f"作成しました。{target.resolve()}")


if __name__ == "__main__":
    main()
