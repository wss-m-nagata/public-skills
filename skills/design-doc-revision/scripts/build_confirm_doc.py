# -*- coding: utf-8 -*-
"""レビュー担当者への確認資料（xlsx）を、仕様のJSONから作る。

使い方:
    python build_confirm_doc.py <仕様JSON> <出力xlsx>

仕様JSON（assets/examples/confirm_doc.example.json を参照）:
    title, subtitle   : 概要シートのタイトルと、何についての資料か
    purpose           : 「この資料の目的」の文章（改行は、JSON の改行の書き方で）
    folder_name       : レビュー用の置き場の、今回のフォルダ名
    change_list_file  : 変更箇所一覧のファイル名（変更履歴フォルダの下）
    recipient         : 確認先の呼び名（省略時は、設定の「レビュー担当者の呼び名」）
    server_root       : 段階（区分）を使うとき、置き場の親フォルダ（設計書のルートからの相対パス）
    reflect_note      : 段階（区分）を使うとき、概要の「反映」の行に書く文（省略時は、一般の文）
    doc_title         : 各シートのサブタイトルに使う資料名（例：「○○ 設計書の確認資料」）
    sheets            : 論点ごとのシート（下記）

    sheets の1件:
      type      : 確認 | 依頼 | 共有 | 報告
      name      : シート名の後半（「確認① 」などは、種別ごとの通し番号で自動に付く）
      title     : シートのタイトル
      overview  : 概要シートの「確認したいこと」に載せる文
      targets   : [{path, note}]  対象の設計書。path は正本の中の相対パス
      refs      : [{text, link}]  確認済みの資料（過去の確認資料など）。text は、ファイル名・シート・回答を、省略せずに書く。
                  link は、この確認資料から見た相対パス（省略可）。見出しは refs_heading で変える（既定：「■ 確認済みの資料」）
      purpose   : 「このシートで確認したい内容」の文章
      code      : {heading, text}  定義（DDL など）を、等幅で、そのまま載せる。purpose の下に置く
      request   : 依頼のときの「お願いしたいこと」（赤・太字）
      table     : [[見出し3つ], [行3つ], ...]  変更前・変更後などの表（省略可）
      resolved  : true にすると、【解決済み】の帯を付け、タブをグレーにする

種別ごとの決まり（確認資料の作り方メモのとおり）:
    確認 : 確認欄は「問題なし／要修正／要相談」。
    依頼 : 確認欄は「対応します／対応不要／要相談」。
    共有 : 判断・対応は要らない。帯「【共有のみ】…」を付け、タブをグレーにする。
    報告 : 回答は要らない。確認欄を置かない。
"""

import json
import math
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

sys.path.insert(0, str(Path(__file__).parent))
from common import ensure_utf8, load_config, local_relative  # noqa: E402

FONT = "Meiryo UI"
FILL = PatternFill("solid", fgColor="E8EEF7")
GRAY = PatternFill("solid", fgColor="E7E6E6")
THIN = Side(style="thin")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
UNIT = 8.43  # 既定の列幅
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"
OPTIONS = {
    "確認": "□ 問題なし\n□ 要修正\n□ 要相談",
    "依頼": "□ 対応します\n□ 対応不要\n□ 要相談",
    "共有": "□ 問題なし\n□ 要修正\n□ 要相談",
}
# 帯の文。{who} は確認先の呼び名（仕様JSONの recipient。既定は、設定の「レビュー担当者の呼び名」）
BANNER = {
    "共有": "【共有のみ】{who}に、判断・対応していただくことはありません。ご承知おきください。",
    "解決済み": "【解決済み】{who}と相談済みです。判断・対応は不要です。",
}


def lines_needed(text, units):
    """折り返しの行数（全角を2、半角を1として数える）。"""
    n = 0
    for line in str(text).split("\n"):
        w = sum(2 if ord(c) > 0x7F else 1 for c in line)
        n += max(1, math.ceil(w / max(units - 1, 1)))
    return n


def put(
    ws,
    ref,
    text,
    size=10,
    bold=False,
    fill=None,
    border=False,
    wrap=True,
    link=None,
    color=None,
):
    c = ws[ref]
    c.value = text
    c.font = Font(
        name=FONT,
        size=size,
        bold=bold,
        color="0563C1" if link else color,
        underline="single" if link else None,
    )
    c.alignment = Alignment(wrap_text=wrap, vertical="top")
    if fill:
        c.fill = fill
    if border:
        c.border = BOX
    if link:
        c.hyperlink = link
    return c


def merge(ws, rng, text, units, **kw):
    """範囲を結合して書く（値と書式を先に書き、結合は、そのあと）。戻り値は、必要な行数。"""
    cells = [c for row in ws[rng] for c in row]
    put(ws, rng.split(":")[0], text, **kw)
    for c in cells:
        if kw.get("border"):
            c.border = BOX
        if kw.get("fill"):
            c.fill = kw["fill"]
    ws.merge_cells(rng)
    return lines_needed(text, units)


def setup(ws, gray_tab=False):
    ws.sheet_view.showGridLines = False
    for k, v in {"A": 2.0, "B": 14.0, "C": 12.0}.items():
        ws.column_dimensions[k].width = v
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    if gray_tab:
        ws.sheet_properties.tabColor = "BFBFBF"


def heading(ws, row, text):
    put(ws, f"B{row}", text, size=11, bold=True, fill=FILL, wrap=False)
    for c in ws[f"B{row}:P{row}"][0]:
        c.fill = FILL
    ws.merge_cells(f"B{row}:P{row}")
    ws.row_dimensions[row].height = 15.75


CODE_FILL = PatternFill("solid", fgColor="F2F2F2")


def code_block(ws, row, text):
    """定義（DDL など）を、等幅・1行1セルで、そのまま書く。次に使える行を返す。"""
    for line in text.split(chr(10)):
        cell = ws[f"B{row}"]
        cell.value = line
        cell.font = Font(name="Consolas", size=10)
        cell.alignment = Alignment(wrap_text=False, vertical="center")
        for c in ws[f"B{row}:P{row}"][0]:
            c.border = BOX
            c.fill = CODE_FILL
        ws.merge_cells(f"B{row}:P{row}")
        ws.row_dimensions[row].height = 15
        row += 1
    return row + 1


def para(ws, row, text, **kw):
    n = merge(ws, f"B{row}:P{row}", text, 14 + 12 + 13 * UNIT, **kw)
    ws.row_dimensions[row].height = 15 * n + 3
    return row + 1


def title_rows(ws, title, subtitle):
    put(ws, "B2", title, size=16, bold=True, wrap=False)
    ws.merge_cells("B2:P2")
    ws.row_dimensions[2].height = 21
    put(ws, "B3", subtitle, size=9, wrap=False)


def table3(ws, row, rows):
    """項目（B:C）・変更前（D:I）・変更後（J:P）の表。次に使える行を返す。"""
    for i, (a, b, c) in enumerate(rows):
        hdr = i == 0
        kw = dict(bold=hdr, fill=FILL if hdr else None, border=True)
        n = max(
            merge(ws, f"B{row + i}:C{row + i}", a, 26, **kw),
            merge(ws, f"D{row + i}:I{row + i}", b, 6 * UNIT, **kw),
            merge(ws, f"J{row + i}:P{row + i}", c, 7 * UNIT, **kw),
        )
        ws.row_dimensions[row + i].height = 18 if hdr else 15 * n + 3
    return row + len(rows)


def _spans(count, total=13):
    """total 個の列を count 個のセルに分けたときの、各セルの列数（余りは、先頭のセルから1列ずつ足す）。"""
    base, extra = divmod(total, count)
    return [base + (1 if i < extra else 0) for i in range(count)]


def grid_example(ws, row, ex):
    """実際の CSV のように、列名と内容を横に並べた例を書く。次に使える行を返す。

    ex: {"caption": 見出し（省略可）, "columns": [列名…], "per_row": 1段に並べる列の数（既定5）,
         "header_label": 列名の行の名前（既定「1行目：列名」）,
         "rows": [{"label": 行の名前（例：2行目：山田さん（回答済み））, "values": [値…]}…], "note": 補足（省略可）}
      ファイルを開いたときの見え方（1行目が列名、2行目以降がスタッフ1人ずつ）が、そのまま伝わるようにする。
      - columns・values に "…" を書くと、省略（…（省略））として、灰色で表示する。
      - values の "" は「（空欄）」として、灰色で表示する。
      - 列が per_row より多いときは、折り返して、段に分ける（段ごとに、列名の行と内容の行が付く）。
    """
    if ex.get("caption"):
        row = para(ws, row, ex["caption"], bold=True)
    per_row = ex.get("per_row", 5)
    columns = ex["columns"]
    widths = _spans(per_row)
    letter = get_column_letter
    for start in range(0, len(columns), per_row):
        chunk = columns[start : start + per_row]
        lines = [(ex.get("header_label", "1行目：列名"), chunk, True)] + [
            (r["label"], r["values"][start : start + per_row], False)
            for r in ex["rows"]
        ]
        for label, cells, header in lines:
            kw = dict(bold=header, fill=FILL if header else None, border=True)
            n = merge(ws, f"B{row}:C{row}", label, 26, **kw)
            col = 4  # D 列から
            for width, text in zip(widths, cells):
                shown, color = text, None
                if text == "":
                    shown, color = "（空欄）", "808080"
                elif text == "…":
                    shown, color = "…\n（省略）", "808080"
                c1, c2 = letter(col), letter(col + width - 1)
                n = max(
                    n,
                    merge(
                        ws,
                        f"{c1}{row}:{c2}{row}",
                        shown,
                        width * UNIT,
                        color=color,
                        **kw,
                    ),
                )
                col += width
            ws.row_dimensions[row].height = 18 if header else 15 * n + 3
            row += 1
        row += 1  # 段の間の空き
    if ex.get("note"):
        row = para(ws, row, ex["note"], color="595959")
    return row + 1


def confirm_box(ws, row, options):
    heading(ws, row, "■ 確認欄")
    put(ws, f"B{row + 2}", "回答", bold=True, fill=FILL, border=True)
    merge(
        ws,
        f"C{row + 2}:P{row + 2}",
        "コメント",
        10 * UNIT,
        bold=True,
        fill=FILL,
        border=True,
    )
    put(ws, f"B{row + 3}", options, border=True)
    merge(ws, f"C{row + 3}:P{row + 3}", None, 10 * UNIT, border=True)
    ws.row_dimensions[row + 2].height = 18
    ws.row_dimensions[row + 3].height = 48
    para(
        ws, row + 5, "該当する□を☑に書き換え、必要に応じてコメント欄にご記入ください。"
    )


def build(spec, out_path):
    cfg = load_config(Path(out_path).parent)
    source_name = Path(cfg["source_dir"]).name
    # 確認先の呼び名を入れた、帯の文
    banners = {
        k: v.format(who=spec.get("recipient", cfg["recipient"]))
        for k, v in BANNER.items()
    }
    sheets = spec["sheets"]
    counters, names = {}, []
    for s in sheets:
        counters[s["type"]] = counters.get(s["type"], 0) + 1
        names.append(f'{s["type"]}{CIRCLED[counters[s["type"]] - 1]} {s["name"]}')
    total = len(sheets)

    wb = Workbook()
    ov = wb.active
    ov.title = "概要"
    sheet_objs = [wb.create_sheet(n) for n in names]
    setup(ov)

    # ---- 概要
    title_rows(ov, spec["title"], spec["subtitle"])
    heading(ov, 5, "■ この資料の目的")
    para(ov, 7, spec["purpose"])
    heading(ov, 9, "■ 確認していただく資料")
    # server_root があるときは、作業フォルダそのものが設計書の置き場である（正本とは別に作る）
    staged = "server_root" in spec
    place = str(
        Path(cfg["design_root"])
        / spec.get("server_root", cfg["review_dir"])
        / spec["folder_name"]
    ) + chr(92)
    rows = [
        ("項目", "内容"),
        ("置き場所", place),
        (
            "変更箇所の一覧",
            f'変更履歴{chr(92)}{spec["change_list_file"]}\n（変更したすべての箇所と、変更前・変更後を載せています）',
        ),
    ]
    if staged:
        rows.append(
            (
                "反映",
                spec.get("reflect_note", "合意をいただいてから、正本へ反映します。"),
            )
        )
    else:
        rows.append(("反映", f"{source_name} には、合意をいただいてから反映します。"))
    for i, (a, b) in enumerate(rows):
        kw = dict(bold=i == 0, fill=FILL if i == 0 else None, border=True)
        n = max(
            merge(ov, f"B{11 + i}:D{11 + i}", a, 34, **kw),
            merge(ov, f"E{11 + i}:P{11 + i}", b, 11 * UNIT, **kw),
        )
        ov.row_dimensions[11 + i].height = 18 if i == 0 else 15 * n + 3
    heading(ov, 16, "■ 各シートの見方")
    kinds = {s["type"] for s in sheets}
    guide = ["1シートにつき1つの論点を記載しています。"]
    if "確認" in kinds:
        guide.append(
            "「確認」のシートは、確認欄に、問題なし・要修正・要相談のいずれかをご記入ください。"
        )
    if "依頼" in kinds:
        guide.append(
            "「依頼」のシートは、お願いしたい対応を書いています。確認欄に、対応します・対応不要・要相談のいずれかをご記入ください。"
        )
    if "共有" in kinds:
        guide.append(
            "「共有」のシートは、弊社の方針や状況をお伝えするものです。判断・対応は不要です。"
        )
    if "報告" in kinds:
        guide.append("「報告」のシートは、ご報告のみです。ご回答は不要です。")
    para(ov, 18, "\n".join(guide))
    heading(ov, 20, "■ シート一覧")
    r = 22
    for i, row in enumerate(
        [("No", "シート", "確認したいこと")]
        + [
            (
                str(k + 1),
                names[k],
                (
                    banners["共有"][:6]
                    if s["type"] == "共有"
                    else banners["解決済み"][:6] if s.get("resolved") else ""
                )
                + s["overview"],
            )
            for k, s in enumerate(sheets)
        ]
    ):
        hdr = i == 0
        gray = (not hdr) and (
            sheets[i - 1]["type"] == "共有" or sheets[i - 1].get("resolved")
        )
        kw = dict(
            bold=hdr,
            fill=FILL if hdr else None,
            border=True,
            color="808080" if gray else None,
        )
        put(ov, f"B{r}", row[0], **kw)
        n = max(
            1,
            merge(ov, f"C{r}:H{r}", row[1], 6 * UNIT, **kw),
            merge(ov, f"I{r}:P{r}", row[2], 8 * UNIT, **kw),
        )
        ov.row_dimensions[r].height = 18 if hdr else 15 * n + 3
        r += 1
    heading(ov, r + 1, "■ ご確認のお願い")
    ask = []
    if kinds & {"確認", "依頼"}:
        ask.append("確認欄に、ご記入いただけると助かります。")
    ask.append(
        "変更箇所の一覧には、変更したすべての箇所を載せています。お時間があれば、ご確認ください。"
    )
    para(ov, r + 3, "\n".join(ask))

    # ---- 論点のシート
    for k, (ws, s) in enumerate(zip(sheet_objs, sheets), 1):
        gray = s["type"] == "共有" or s.get("resolved")
        setup(ws, gray_tab=gray)
        title_rows(
            ws,
            f'{names[k - 1].split(" ")[0]}　{s["title"]}',
            f'{spec["doc_title"]}（{k}/{total}）',
        )
        banner = (
            banners["共有"]
            if s["type"] == "共有"
            else banners["解決済み"] if s.get("resolved") else None
        )
        if banner:
            merge(
                ws,
                "B4:P4",
                banner,
                14 + 12 + 13 * UNIT,
                bold=True,
                fill=GRAY,
                color="595959",
            )
        row = 5
        if s.get("targets"):
            heading(ws, row, "■ 対象の設計書")
            row += 2
            for t in s["targets"]:
                text = Path(t["path"]).name + t.get("note", "")
                put(ws, f"B{row}", text, link="../" + local_relative(t["path"], cfg))
                ws.merge_cells(f"B{row}:P{row}")
                ws.row_dimensions[row].height = (
                    15 * lines_needed(text, 14 + 12 + 13 * UNIT) + 3
                )
                row += 1
            row += 1
        if s.get("refs"):
            heading(ws, row, s.get("refs_heading", "■ 確認済みの資料"))
            row += 2
            for t in s["refs"]:
                put(ws, f"B{row}", t["text"], link=t.get("link"))
                ws.merge_cells(f"B{row}:P{row}")
                ws.row_dimensions[row].height = (
                    15 * lines_needed(t["text"], 14 + 12 + 13 * UNIT) + 3
                )
                row += 1
            row += 1
        heading(
            ws,
            row,
            (
                "■ このシートの内容"
                if s["type"] == "報告"
                else "■ このシートで確認したい内容"
            ),
        )
        purpose = s["purpose"] + (
            "\nご報告です。ご回答は不要です。" if s["type"] == "報告" else ""
        )
        row = para(ws, row + 2, purpose) + 1
        if s.get("code"):
            heading(ws, row, s["code"].get("heading", "■ 定義"))
            row = code_block(ws, row + 2, s["code"]["text"])
        if s.get("examples"):
            heading(ws, row, s.get("examples_heading", "■ 実際のデータのイメージ"))
            row += 2
            for ex in s["examples"]:
                row = grid_example(ws, row, ex)
        if s.get("table"):
            heading(ws, row, s.get("table_heading", "■ 変更の内容"))
            row = table3(ws, row + 2, s["table"]) + 1
        if s["type"] == "依頼" and s.get("request"):
            heading(ws, row, "■ お願いしたいこと")
            row = para(ws, row + 2, s["request"], bold=True, color="C00000") + 1
        if s["type"] != "報告":
            confirm_box(ws, row, OPTIONS[s["type"]])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


if __name__ == "__main__":
    ensure_utf8()
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    build(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2])
    print("OK:", sys.argv[2])
