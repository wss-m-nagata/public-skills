#!/usr/bin/env python3
"""入力シートの項目の正本（items.toml）から、Excelのひな形と記入要領を作る。

作るもの:
  assets/project-intake/プロジェクト入力シート.xlsx  利用者が記入するExcelのひな形
  references/intake-guide.md                         AIが読む記入要領（項目の意味、既定値、扱い、反映先）

- 項目を変えるときは、items.toml を直してから、このスクリプトを実行する。Excelと記入要領を手で直さない。
- 項目の表には、項目を見分けるための「ID」列を、隠して置く。read_intake.py と write_intake.py は、この列で項目を探す。
- アプリ構成シートの図は、assets/project-intake/ の画像を貼る（make_service_figure.py で作る）。
- openpyxl が要る。

使い方（スキルのディレクトリで実行する）:
  python scripts/project-intake/build_intake.py
  python scripts/project-intake/build_intake.py --xlsx <出力先.xlsx> --guide <出力先.md>
"""

import argparse
import math
import tomllib
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink

# スキル直下のディレクトリ
_SKILL = Path(__file__).resolve().parents[2]
_ASSETS = _SKILL / "assets" / "project-intake"
_ITEMS = _ASSETS / "items.toml"
_XLSX = _ASSETS / "プロジェクト入力シート.xlsx"
_GUIDE = _SKILL / "references" / "intake-guide.md"

# 必須・任意の値
REQ = "必須"
COND = "条件付き必須"
OPT = "任意"

# 書式
_FONT = "Meiryo UI"
_F_BASE = Font(name=_FONT, size=10)
_F_BOLD = Font(name=_FONT, size=10, bold=True)
_F_HEAD = Font(name=_FONT, size=10, bold=True, color="FFFFFF")
_F_TITLE = Font(name=_FONT, size=14, bold=True)
_F_SECTION = Font(name=_FONT, size=12, bold=True)
_F_EX = Font(name=_FONT, size=10, italic=True, color="808080")
_F_LINK = Font(name=_FONT, size=10, color="0563C1", underline="single")
_FILL_HEAD = PatternFill("solid", fgColor="1F4E79")
_FILL_INPUT = PatternFill("solid", fgColor="FFF2CC")
_FILL_REQ = PatternFill("solid", fgColor="FCE4D6")
_FILL_EX = PatternFill("solid", fgColor="F2F2F2")
_FILL_PROMPT = PatternFill("solid", fgColor="EDF3FB")
_THIN = Side(style="thin", color="A6A6A6")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_WRAP = Alignment(wrap_text=True, vertical="top")

# 見出しはA列、中身はB列（C0）から書く（階段状にするため）
C0 = 2
_INDENT_WIDTH = 3
# 図の下の行の高さ（ポイント）と、図と表の間に空ける行数
_ROW_PT = 15
_IMAGE_MARGIN_ROWS = 4

# 項目の表の列（見出し、幅）。最後の「ID」列は隠す
ITEM_HEADERS = ["No", "項目", "説明", "記入例", "必須・任意", "既定値（空欄のときに使う値）", "記入欄", "ID"]
_ITEM_WIDTHS = [5, 26, 52, 34, 12, 34, 44, 20]
COL_NAME = C0 + 1  # 項目
COL_REQ = C0 + 4  # 必須・任意
COL_INPUT = C0 + 6  # 記入欄
COL_ID = C0 + 7  # ID（隠す）


def load_items(path: Path = _ITEMS) -> dict:
    """items.toml を読む。read_intake.py と write_intake.py からも使う。"""
    with path.open("rb") as f:
        return tomllib.load(f)


def _col(n: int) -> str:
    """列番号を列の文字（A、B、…）にする。"""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _title(ws, title: str, lead: list[str]) -> int:
    """シートの見出しをA列に、説明文をB列に書き、次に書く行番号を返す。"""
    ws.column_dimensions["A"].width = _INDENT_WIDTH
    ws["A1"] = title
    ws["A1"].font = _F_TITLE
    row = 2
    for line in lead:
        ws.cell(row=row, column=C0, value=line).font = _F_BASE
        row += 1
    return row + 1


def _header(ws, row: int, headers: list[str], widths: list[int], freeze: bool = True) -> None:
    """表の見出し行を、B列から書く。"""
    for col, (h, w) in enumerate(zip(headers, widths), start=C0):
        c = ws.cell(row=row, column=col, value=h)
        c.font = _F_HEAD
        c.fill = _FILL_HEAD
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = _BORDER
        ws.column_dimensions[c.column_letter].width = w
    if freeze:
        ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _note(cell, text: str) -> None:
    """セルに補足のコメントを付ける。"""
    lines = text.count("\n") + 1 + len(text) // 40
    cm = Comment(text, "入力シート")
    cm.width = 360
    cm.height = max(80, 20 * lines)
    cell.comment = cm


def _list_validation(ws, choices: list[str], ref: str) -> None:
    """セルにプルダウンを付ける。"""
    dv = DataValidation(type="list", formula1='"' + ",".join(choices) + '"', allow_blank=True)
    dv.error = "一覧から選ぶか、空欄にしてください。"
    dv.showErrorMessage = True
    ws.add_data_validation(dv)
    dv.add(ref)


def _item_sheet(wb, sheet: dict) -> tuple[int, int]:
    """項目の表のシートを作り、項目の最初と最後の行番号を返す。"""
    ws = wb.create_sheet(sheet["name"])
    row = _title(ws, sheet["name"], sheet["lead"])
    figure = sheet.get("figure")
    if figure:
        # 図を表の上に貼る。高解像度で描いた画像を、半分の大きさで表示する
        pic = XlImage(str(_ASSETS / figure))
        pic.width, pic.height = pic.width // 2, pic.height // 2
        ws.add_image(pic, f"B{row}")
        # 図の下の行の高さを固定し、図が表にかからないよう余白の行を足す
        pic_rows = math.ceil(pic.height * 0.75 / _ROW_PT) + _IMAGE_MARGIN_ROWS
        for r in range(row, row + pic_rows):
            ws.row_dimensions[r].height = _ROW_PT
        row += pic_rows
    # 図ごと固定すると表が見えなくなるため、図があるシートは固定しない
    _header(ws, row, ITEM_HEADERS, _ITEM_WIDTHS, freeze=not figure)
    ws.column_dimensions[_col(COL_ID)].hidden = True
    items = sheet["items"]
    for no, item in enumerate(items, start=1):
        r = row + no
        values = [no, item["name"], item["description"], item["example"], item["required"],
                  item.get("default", ""), None, item["id"]]
        for col, v in enumerate(values, start=C0):
            c = ws.cell(row=r, column=col, value=v)
            c.font = _F_BASE
            c.alignment = _WRAP
            c.border = _BORDER
        if item["required"] != OPT:
            ws.cell(row=r, column=COL_REQ).fill = _FILL_REQ
        ws.cell(row=r, column=COL_INPUT).fill = _FILL_INPUT
        if item.get("note"):
            _note(ws.cell(row=r, column=COL_NAME), item["note"])
        if item.get("choices"):
            _list_validation(ws, item["choices"], ws.cell(row=r, column=COL_INPUT).coordinate)
    return row + 1, row + len(items)


def _list_sheet(wb, sheet: dict) -> tuple[int, int]:
    """1行に1件を書く一覧のシートを作り、記入する行の最初と最後の行番号を返す。先頭の行は記入例。"""
    ws = wb.create_sheet(sheet["name"])
    row = _title(ws, sheet["name"], sheet["lead"])
    columns = sheet["columns"]
    _header(ws, row, ["No"] + [c["name"] for c in columns], [5] + [c["width"] for c in columns])
    # 記入例の行
    r = row + 1
    for col, v in enumerate(["例"] + [c["example"] for c in columns], start=C0):
        c = ws.cell(row=r, column=col, value=v)
        c.font = _F_EX
        c.fill = _FILL_EX
        c.alignment = _WRAP
        c.border = _BORDER
    # 記入する行
    first, last = r + 1, r + sheet["rows"]
    for i, rr in enumerate(range(first, last + 1), start=1):
        ws.cell(row=rr, column=C0, value=i).font = _F_BASE
        for col in range(C0, C0 + 1 + len(columns)):
            c = ws.cell(row=rr, column=col)
            c.border = _BORDER
            c.alignment = _WRAP
            c.font = _F_BASE
            if col > C0:
                c.fill = _FILL_INPUT
    # 選択肢のある列にプルダウンを付ける
    for i, column in enumerate(columns, start=C0 + 1):
        if column.get("choices"):
            letter = _col(i)
            _list_validation(ws, column["choices"], f"{letter}{first}:{letter}{last}")
    return first, last


def _list_col(sheet: dict, column_id: str) -> str:
    """一覧シートの列IDから、列の文字を返す（B列は No）。"""
    ids = [c["id"] for c in sheet["columns"]]
    return _col(C0 + 1 + ids.index(column_id))


def _guide_sheet(ws, data: dict, sheets: list[dict], ranges: dict) -> None:
    """はじめにシート（使い方、記入した人、シートの一覧と未記入の数、AIへの相談のしかた）を作る。"""
    guide = data["guide"]
    ws.title = "はじめに"
    for letter, width in zip("ABCD", [_INDENT_WIDTH, 28, 90, 14]):
        ws.column_dimensions[letter].width = width
    ws["A1"] = guide["title"]
    ws["A1"].font = _F_TITLE

    # 使い方
    r = 3
    ws.cell(row=r, column=1, value="使い方").font = _F_SECTION
    r += 1
    for u in guide["usage"]:
        ws.cell(row=r, column=C0, value=u["label"]).font = _F_BOLD
        c = ws.cell(row=r, column=C0 + 1, value=u["text"])
        c.font = _F_BASE
        c.alignment = _WRAP
        ws.row_dimensions[r].height = 15 * (u["text"].count("\n") + 1) + 4
        r += 1

    # 記入した人
    r += 1
    ws.cell(row=r, column=1, value="記入した人").font = _F_SECTION
    r += 1
    for label in ["記入日", "記入者"]:
        ws.cell(row=r, column=C0, value=label).font = _F_BOLD
        ws.cell(row=r, column=C0 + 1).fill = _FILL_INPUT
        r += 1

    # シートの一覧と、未記入の数
    r += 1
    ws.cell(row=r, column=1, value="シートの一覧").font = _F_SECTION
    r += 1
    for col, h in enumerate(["シート", "内容", "未記入の数"], start=C0):
        c = ws.cell(row=r, column=col, value=h)
        c.font = _F_HEAD
        c.fill = _FILL_HEAD
        c.border = _BORDER
    req_col, input_col = _col(COL_REQ), _col(COL_INPUT)
    for sheet in sheets:
        r += 1
        name = sheet["name"]
        c = ws.cell(row=r, column=C0, value=name)
        c.font = _F_LINK
        # ブック内のシートへのリンク（外部リンクの形にすると、Excelが壊れたファイルと判断する）
        c.hyperlink = Hyperlink(ref=c.coordinate, location=f"'{name}'!A1", display=name)
        ws.cell(row=r, column=C0 + 1, value=sheet["summary"]).font = _F_BASE
        f, l = ranges[name]
        if sheet["kind"] == "items":
            # 必須で、記入欄が空の項目の数
            formula = (f"=COUNTIFS('{name}'!${req_col}${f}:${req_col}${l},\"{REQ}\","
                       f"'{name}'!${input_col}${f}:${input_col}${l},\"\")")
        elif sheet.get("required_with"):
            # 先頭の列を書いたのに、一緒に書く列が空の行の数
            key = f"'{name}'!${_list_col(sheet, sheet['columns'][0]['id'])}${f}:${_list_col(sheet, sheet['columns'][0]['id'])}${l}"
            empties = "+".join(f"('{name}'!${_list_col(sheet, cid)}${f}:${_list_col(sheet, cid)}${l}=\"\")"
                               for cid in sheet["required_with"])
            formula = f"=SUMPRODUCT(({key}<>\"\")*(({empties})>0))"
        else:
            # 書いた行が、必要な行数に足りないときの不足の数
            name_col = _list_col(sheet, "name")
            need = sheet.get("required_rows", 0)
            formula = f"=MAX(0,{need}-COUNTA('{name}'!${name_col}${f}:${name_col}${l}))"
        c = ws.cell(row=r, column=C0 + 2, value=formula)
        c.font = _F_BASE
        for col in range(C0, C0 + 3):
            ws.cell(row=r, column=col).border = _BORDER
    notes = [
        "※ 項目のシートは、必須で記入欄が空の項目を数えます。条件付き必須は数えません。",
        "※ インプット資料は任意です。資料名を書いたのに、場所か見てほしいシート・ページが空の行を数えます。",
        "※ 画面とメニューは、画面が1行も書かれていなければ1と数えます。",
    ]
    r += 1
    for t in notes:
        ws.cell(row=r, column=C0, value=t).font = _F_EX
        r += 1

    # 分からないときの聞き方（AIへの指示のテンプレート）
    consult = guide["consult"]
    r += 1
    ws.cell(row=r, column=1, value="分からないときの聞き方").font = _F_SECTION
    r += 1
    for t in consult["lead"]:
        ws.cell(row=r, column=C0, value=t).font = _F_BASE
        r += 1
    r += 1
    for col, h in enumerate(["やりたいこと", "AIへの指示（【】を書き換えて貼る）"], start=C0):
        c = ws.cell(row=r, column=col, value=h)
        c.font = _F_HEAD
        c.fill = _FILL_HEAD
        c.border = _BORDER
    for p in consult["prompts"]:
        r += 1
        a = ws.cell(row=r, column=C0, value=p["purpose"])
        a.font = _F_BOLD
        a.alignment = _WRAP
        a.border = _BORDER
        b = ws.cell(row=r, column=C0 + 1, value=p["text"])
        b.font = _F_BASE
        b.fill = _FILL_PROMPT
        b.alignment = _WRAP
        b.border = _BORDER
        ws.row_dimensions[r].height = 16 * (p["text"].count("\n") + 1) + 8
    ws.cell(row=r + 1, column=C0, value=consult["footnote"]).font = _F_EX


def build_xlsx(data: dict, out: Path) -> None:
    """Excelのひな形を作る。"""
    wb = Workbook()
    sheets = data["sheets"]
    ranges = {}
    for sheet in sheets:
        if sheet["kind"] == "items":
            ranges[sheet["name"]] = _item_sheet(wb, sheet)
        else:
            ranges[sheet["name"]] = _list_sheet(wb, sheet)
    _guide_sheet(wb.active, data, sheets, ranges)
    # はじめにシートを先頭にし、ほかは items.toml の順に並べる
    wb._sheets = [wb["はじめに"]] + [wb[s["name"]] for s in sheets]
    wb.active = 0
    # 未記入の数の式を、Excelで開いたときに計算させる
    wb.calculation.fullCalcOnLoad = True
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)


def _md(text: str) -> str:
    """表のセルに入れるため、改行を <br/> にし、| をエスケープする。"""
    return text.replace("|", "\\|").replace("\n", "<br/>")


def build_guide(data: dict, out: Path) -> None:
    """記入要領（Markdown）を作る。"""
    lines = [
        "<!-- このファイルは scripts/project-intake/build_intake.py で assets/project-intake/items.toml から作る。手で直さない。 -->",
        "",
        "# 入力シートの記入要領",
        "",
        "入力シート（`assets/project-intake/プロジェクト入力シート.xlsx`）の項目ごとに、意味、選択肢、既定値、反映先を示す。",
        "利用者に項目の意味を聞かれたとき、下書きを作るとき、記入漏れを確かめるとき、環境を作るときに読む。",
        "入力シートの値は、`scripts/project-intake/read_intake.py` で読む（項目は、隠した「ID」列で見分ける）。",
        "",
        "## 値の扱い",
        "",
        "| 状態 | 意味 | 扱い |",
        "| --- | --- | --- |",
        "| 記入 | 記入欄に値がある | その値を使う |",
        "| 既定値 | 任意の項目で、記入欄が空 | 「既定値」を使う |",
        "| 未決定 | 「未定」「不明」と書かれている | 推測で埋めない。説明に書いた「未定・不明のとき」の扱いに従い、未決定事項として報告する |",
        "| 空欄 | 必須の項目、または条件に当てはまる条件付き必須の項目で、記入欄が空 | 環境は作らず、空欄の一覧を利用者に返す |",
        "",
        "- 条件付き必須は、「条件」の項目の値（既定値を当てた値）が一致するときだけ必須になる。",
        "- 「既定のまま」と書かれた記入欄は、空欄と同じに扱う。",
        "- 秘密情報（パスワード、トークン、接続文字列）は、入力シートにも、反映先にも書かない。",
        "",
    ]
    for sheet in data["sheets"]:
        lines += [f"## {sheet['name']}", "", sheet["summary"], ""]
        if sheet["kind"] == "items":
            lines += ["| ID | 項目 | 必須・任意 | 既定値 | 説明 | 補足 | 反映先 |", "| --- | --- | --- | --- | --- | --- | --- |"]
            for item in sheet["items"]:
                req = item["required"]
                cond = item.get("required_if")
                if cond:
                    req += f"（`{cond['id']}` が「{cond['equals']}」のとき）"
                desc = item["description"]
                if item.get("choices"):
                    desc += "\n選択肢：" + "／".join(item["choices"])
                lines.append(
                    f"| `{item['id']}` | {_md(item['name'])} | {_md(req)} | {_md(item.get('default', '')) or '—'} "
                    f"| {_md(desc)} | {_md(item.get('note', '')) or '—'} | {_md(item['reflect'])} |"
                )
        else:
            lines += [f"1行に1件を書く一覧（最大{sheet['rows']}行）。列は次のとおり。", "",
                      "| ID | 列 | 記入例 |", "| --- | --- | --- |"]
            for c in sheet["columns"]:
                ex = c["example"]
                if c.get("choices"):
                    ex += "（選択肢：" + "／".join(c["choices"]) + "）"
                lines.append(f"| `{c['id']}` | {_md(c['name'])} | {_md(ex)} |")
            if sheet.get("required_with"):
                cols = "、".join(f"`{c}`" for c in sheet["required_with"])
                lines += ["", f"任意のシートである。行を書いたときは、{cols} も書く。"]
            if sheet.get("required_rows"):
                lines += ["", f"少なくとも{sheet['required_rows']}行を書く。"]
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(("\n".join(lines).rstrip("\n") + "\n").encode("utf-8"))


def main() -> None:
    """引数を読み、Excelと記入要領を作る。"""
    parser = argparse.ArgumentParser(description="items.toml から、入力シートのExcelと記入要領を作る。")
    parser.add_argument("--items", type=Path, default=_ITEMS, help="項目の正本（既定：assets/project-intake/items.toml）")
    parser.add_argument("--xlsx", type=Path, default=_XLSX, help="Excelの出力先")
    parser.add_argument("--guide", type=Path, default=_GUIDE, help="記入要領の出力先")
    args = parser.parse_args()
    data = load_items(args.items)
    build_xlsx(data, args.xlsx)
    build_guide(data, args.guide)
    print(f"作成: {args.xlsx}")
    print(f"作成: {args.guide}")


if __name__ == "__main__":
    main()
