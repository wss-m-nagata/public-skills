# Revision History
# 2026/11/21: WSS永田 道拓: 画面E2Eの試験項目表と条件マトリックスの生成を追加。
#   - 想定結果の続き行に個別の番号を付け、対象外の記載欄をハイフンで表示する。
#   - 更新したケースの項目と想定結果を赤字にする。
"""画面E2E用の試験項目表と条件マトリックスを組み立てる。"""

import re
from copy import copy

from openpyxl.styles import Alignment, Border, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from add_test_data_sheet import write_test_data_sheet
from fit_row_heights import fit_sheet
from xlsx_common import mark_font_red


HEADER_ROW = 10
THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MATRIX_COLUMNS = ("No.", "画面の状態", "入力値", "操作", "想定結果")
CHANGE_COLUMNS = ("対応設計書", "対応箇所", "テスト内容", "想定結果")


def _changed_cells(case, columns, values, row, result_count):
    """変更を指定した列と、個別に指定した想定結果の行をセル番地に変換する。"""
    flag = case.get("changed", False)
    if flag is True:
        labels = CHANGE_COLUMNS
    elif flag is False:
        labels = []
    elif isinstance(flag, list):
        labels = ["テスト内容" if label == "テストコード" else label for label in flag]
        if any(label not in CHANGE_COLUMNS for label in labels):
            raise ValueError(f"changed の列名は {', '.join(CHANGE_COLUMNS)} またはテストコードを指定してください")
    else:
        raise ValueError("changed は true / false または列名の配列を指定してください")

    cells = {
        f"{get_column_letter(columns[label])}{row}"
        for label in labels if label in values and values[label]
    }
    result_rows = case.get("changed_result_rows", [])
    if not isinstance(result_rows, list) or any(
        type(number) is not int or not 1 <= number <= result_count for number in result_rows
    ):
        raise ValueError(f"changed_result_rows は 1〜{result_count} の想定結果の行番号を指定してください")
    if "想定結果" in labels:
        result_rows = range(1, result_count + 1)
    result_col = get_column_letter(columns["想定結果"])
    cells.update(f"{result_col}{row + number - 1}" for number in result_rows)
    return cells


def _format_page(ws, last_column, last_row):
    """通常表示にし、実際に使用する列を印刷範囲に含める。"""
    ws.sheet_view.view = "normal"
    ws.sheet_view.showGridLines = True
    ws.print_area = f"A1:{get_column_letter(last_column)}{last_row}"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.scale = None
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.orientation = "landscape"


def _set_text(cell, value):
    """試験の入出力を数式として解釈せず、文字として書く。"""
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"


def _write_matrix(wb, matrices, header, body_font):
    """ABCD列を見出し用に使い、E列から表を書く。"""
    ws = wb.create_sheet("条件マトリックス")
    ws["A1"] = "条件マトリックス"
    ws["B3"] = "画面状態と操作条件"
    for col in "ABCD":
        ws.column_dimensions[col].width = 3
    for col, width in zip("EFGHI", (8, 26, 28, 24, 42)):
        ws.column_dimensions[col].width = width
    for cell in (ws["A1"], ws["B3"]):
        cell.font = copy(header.font)

    row = 5
    for matrix in matrices:
        ws.cell(row, 4, f"{matrix['No']}：{matrix['名称']}").font = copy(header.font)
        row += 1
        for column, label in enumerate(MATRIX_COLUMNS, 5):
            cell = ws.cell(row, column, label)
            cell.font = copy(header.font)
            cell.fill = copy(header.fill)
            cell.border = BORDER
        ws.row_dimensions[row].height = 21
        row += 1
        for number, condition in enumerate(matrix["条件"], 1):
            values = [number, *(condition[key] for key in MATRIX_COLUMNS[1:])]
            for column, value in enumerate(values, 5):
                cell = ws.cell(row, column)
                _set_text(cell, value)
                cell.font = copy(body_font)
                cell.border = BORDER
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            row += 1
        # 表名は試験データと同様に、右隣の空きセルへ横に表示する。
        fit_sheet(ws, [(row - len(matrix["条件"]), row - 1)])
        row += 1
    _format_page(ws, 9, ws.max_row)
    return ws


def write_e2e_sheets(wb, definition):
    """既存の取引単体様式を使い、試験仕様を1ケースにつき1行以上で書く。"""
    if "【リクエストID】_リクエスト単体" not in wb.sheetnames:
        raise ValueError("画面E2Eには画面用の単体テスト仕様書テンプレートを指定してください")
    ws = wb["取引単体"]
    if not definition["cases"]:
        raise ValueError("cases に1件以上の試験ケースを書いてください")

    # マトリックスと試験データの参照先を生成前に確定する。
    matrices = definition.get("matrices", [])
    matrix_rows = {}
    for matrix in matrices:
        no = matrix["No"]
        if not re.fullmatch(r"C[0-9]{2,}", no) or no in matrix_rows or not matrix["条件"]:
            raise ValueError(f"条件マトリックスの番号または条件が不正です: {no}")
        matrix_rows[no] = len(matrix["条件"])
    test_data = definition.get("test_data")
    if test_data and test_data.get("sheet_name", "試験データ") != "試験データ":
        raise ValueError("画面E2Eの試験データのシート名は「試験データ」です")
    datasets = [entry["no"] for entry in test_data["datasets"]] if test_data else []
    if len(datasets) != len(set(datasets)) or any(not re.fullmatch(r"D[0-9]{2,}", no) for no in datasets):
        raise ValueError("試験データ番号は D01 形式で重複なく指定してください")

    # 原本の見出しはそのまま使い、例示行と行・列の既定書式を外す。
    columns = {cell.value: cell.column for cell in ws[HEADER_ROW] if cell.value}
    body_font = copy(ws.cell(HEADER_ROW + 1, columns["テスト内容"]).font)
    ws.delete_rows(HEADER_ROW + 1, ws.max_row - HEADER_ROW)
    for row_number in list(ws.row_dimensions):
        if row_number > HEADER_ROW:
            del ws.row_dimensions[row_number]
    for dimension in ws.column_dimensions.values():
        dimension._style = None
    for name in ("【テストターゲット名】_クラス単体", "【リクエストID】_リクエスト単体"):
        del wb[name]
    ws.freeze_panes = "A11"
    ws.column_dimensions["I"].max = 9
    ws.column_dimensions["I"].width = 48
    ws.column_dimensions["J"].width = 38

    # ケース共通の内容は先頭行だけに置き、想定結果は続く行に分ける。
    changed_cells = set()
    row = HEADER_ROW + 1
    for number, case in enumerate(definition["cases"], 1):
        content = ["【前提】", *case["前提"], "", "【操作】"]
        operations = case["操作"]
        results = case["想定結果"]
        if not operations or not results or any(not item.strip() for item in [*operations, *results]):
            raise ValueError(f"ケース {number} の操作と想定結果を1件以上記入してください")
        content.extend(f"{n}. {step}" for n, step in enumerate(operations, 1))
        for no, index in case.get("条件マトリックス", []):
            if type(index) is not int or not 1 <= index <= matrix_rows.get(no, 0):
                raise ValueError(f"ケース {number} の条件マトリックス参照がありません: {no} の No.{index}")
            content.append(f"条件マトリックス {no} の No.{index}")
        if case.get("テストコード"):
            content.extend(["", f"【テストコード】{case['テストコード']}"])
        data_no = case.get("データNo")
        if data_no is not None and data_no not in datasets:
            raise ValueError(f"ケース {number} の試験データ参照がありません: {data_no}")

        values = {key: case[key] for key in ("区分", "確認観点1", "確認観点2", "確認観点3", "対応設計書", "対応箇所") if key in case}
        values.update({"ケースNo.": str(number), "テスト内容": "\n".join(content)})
        if data_no:
            values.update({"テストデータシート名": "試験データ", "データNo": data_no})
        changed_cells.update(_changed_cells(case, columns, values, row, len(results)))
        for label, value in values.items():
            _set_text(ws.cell(row, columns[label]), value)
        for result_number, result in enumerate(results, 1):
            # 続き行もNGを報告できるよう、元のケースNoに確認項目の枝番を付ける。
            if result_number > 1:
                _set_text(ws.cell(row, columns["ケースNo."]), f"{number}-{result_number}")
                for column in range(columns["ケースNo."] + 1, columns["テスト内容"] + 1):
                    _set_text(ws.cell(row, column), "-")
            _set_text(ws.cell(row, columns["想定結果"]), result)
            row += 1

    last_row = row - 1
    last_column = max(columns.values())
    for cells in ws.iter_rows(min_row=HEADER_ROW + 1, max_row=last_row, max_col=last_column):
        for cell in cells:
            cell.fill = PatternFill()
            cell.border = BORDER
            cell.font = copy(body_font)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    # 本文のフォントを揃えた後で、今回の変更箇所だけを赤字にする。
    for coordinate in changed_cells:
        mark_font_red(ws, coordinate)
    result_col = get_column_letter(columns["実施結果"])
    validation = DataValidation(type="list", formula1='"OK,NG"', allow_blank=True)
    ws.add_data_validation(validation)
    validation.add(f"{result_col}{HEADER_ROW + 1}:{result_col}{last_row}")
    # 行単位のフィルターで追加の想定結果が隠れないようにする。
    ws.auto_filter.ref = None
    ws.print_title_rows = f"1:{HEADER_ROW}"
    _format_page(ws, last_column, last_row)
    fit_sheet(ws, [(HEADER_ROW + 1, last_row)])

    # 補足シートをケース表と同じブックに保存する。
    if matrices:
        _write_matrix(wb, matrices, ws["A10"], body_font)
    if test_data:
        data_ws = write_test_data_sheet(wb, test_data)
        _format_page(data_ws, data_ws.max_column, data_ws.max_row)
    return ws, bool(changed_cells)
