# -*- coding: utf-8 -*-
"""変更箇所一覧（xlsx）を、仕様のJSONから作る。

使い方:
    python build_change_list.py <仕様JSON> <出力xlsx>

仕様JSON（assets/examples/change_list.example.json を参照）:
    title        : A1 のタイトル
    summary      : 何を直したかの1〜2文（A2）
    confirm_note : 「要確認」の行の説明に足す1文（省略時は「今回は、ありません。」）
    rows         : [{confirm, file, sheet, spot, kind, before, after}, ...]
                   confirm は「要確認」か「任意」。file は正本の中の相対パス。
    files        : [{file, handling, dest}]（省略時は rows の file から作る。handling は「修正」か「新規」。
                   dest は、合意後の反映先の説明用の名前（省略可）。段階（区分）を使うときだけ意味がある）
    recipient    : 確認先の呼び名（省略時は、設定の「レビュー担当者の呼び名」）
    server_root  : 段階（区分）を使うとき、レビュー用の置き場の親フォルダ（設計書のルートからの相対パス）。
                   書くと、作業フォルダそのものが設計書の置き場になり、反映先は files の dest で示す

決まり:
  - 「要確認」の行を上に集める（それぞれの中は、書いた順のまま）。No. は、並べ替えたあとに振る。
  - 要確認の行はオレンジ、任意の行は白。
  - 「ファイル一覧」シートに、ファイルごとの、ファイルサーバーでの扱いを書く。
"""

import json
import math
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).parent))
from common import ensure_utf8, load_config, top_folder  # noqa: E402

HEADER = PatternFill("solid", fgColor="DDEBF7")
ORANGE = PatternFill("solid", fgColor="F8CBAD")
WIDTHS = {"A": 5, "B": 8, "C": 40, "D": 22, "E": 30, "F": 10, "G": 55, "H": 60}
COLUMNS = [
    "No.",
    "確認",
    "対象ファイル",
    "シート／ページ",
    "箇所",
    "区分",
    "変更前",
    "変更後",
]


def lines_needed(text, width):
    """折り返しの行数（全角を2、半角を1として数える）。"""
    n = 0
    for line in str(text).split("\n"):
        w = sum(2 if ord(c) > 0x7F else 1 for c in line)
        n += max(1, math.ceil(w / max(width - 1, 1)))
    return n


def build(spec, out_path):
    """変更箇所一覧を作って、保存する。

    Args:
        spec (dict): 仕様JSON。
        out_path (str): 出力する xlsx のパス。
    """
    cfg = load_config(Path(out_path).parent)
    source_name = Path(cfg["source_dir"]).name
    wb = Workbook()
    ws = wb.active
    ws.title = "変更箇所一覧"
    ws["A1"] = spec["title"]
    ws["A1"].font = Font(size=12, bold=True)
    ws["A2"] = spec["summary"]
    # 確認先の呼び名（既定は、設定の「レビュー担当者の呼び名」。仕様JSONの recipient で変える）
    who = spec.get("recipient", cfg["recipient"])
    ws["A3"] = (
        f"・【凡例】オレンジの行（「確認」列が「要確認」）は、{who}に判断・対応していただくことがある箇所です。"
        + spec.get("confirm_note", "今回は、ありません。")
    )
    ws["A4"] = (
        f"・【凡例】白の行（「確認」列が「任意」）は、{who}に判断・対応していただくことが無い変更です。お時間があればご確認ください。"
    )
    # server_root があるときは、作業フォルダそのものが設計書の置き場である（正本とは別に作る）
    staged = "server_root" in spec
    ws["A5"] = (
        (
            "・対象ファイルのパスは、「ファイルサーバーの配置先」（ファイル一覧シート）からの相対パスです。"
            if staged
            else f"・対象ファイルのパスは、{source_name} からの相対パスです（このフォルダに、修正版を置きます）。"
        )
        + "Excelの設計書は、変更したセルを赤字にしています（前の版の赤字は黒に戻しました）。"
    )
    ws["A6"] = (
        "・ファイルごとのファイルサーバーでの扱いは「ファイル一覧」シートにまとめています。"
    )
    for c, name in enumerate(COLUMNS, 1):
        cell = ws.cell(8, c, name)
        cell.font = Font(bold=True)
        cell.fill = HEADER
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for k, v in WIDTHS.items():
        ws.column_dimensions[k].width = v
    ws.freeze_panes = "A9"

    # 要確認を上に集める（sorted は安定なので、それぞれの中は書いた順のまま）
    rows = sorted(spec["rows"], key=lambda r: r["confirm"] != "要確認")
    widths = list(WIDTHS.values())
    for i, r in enumerate(rows, 1):
        vals = [
            i,
            r["confirm"],
            r["file"],
            r["sheet"],
            r["spot"],
            r["kind"],
            r["before"],
            r["after"],
        ]
        row = 8 + i
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row, c, v)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if r["confirm"] == "要確認":
                cell.fill = ORANGE
        ws.row_dimensions[row].height = (
            15 * max(lines_needed(v, w) for v, w in zip(vals, widths)) + 2
        )

    # ファイル一覧
    ws2 = wb.create_sheet("ファイル一覧")
    ws2["A1"] = "今回変更したファイルと、ファイルサーバーでの扱い"
    ws2["A1"].font = Font(size=12, bold=True)
    ws2["A2"] = "ファイルサーバーの配置先：" + str(
        Path(cfg["design_root"])
        / spec.get("server_root", cfg["review_dir"])
        / spec.get("folder_name", "<作業フォルダ>")
    )
    for c, name in enumerate(
        ["No.", "ファイル", "今回の扱い", "ファイルサーバーでの扱い"], 1
    ):
        cell = ws2.cell(4, c, name)
        cell.font = Font(bold=True)
        cell.fill = HEADER
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    files = spec.get("files")
    if not files:
        seen = []
        for r in spec["rows"]:
            if r["file"] not in seen:
                seen.append(r["file"])
        files = [{"file": f, "handling": "修正"} for f in seen]
    for i, f in enumerate(files, 1):
        folder = top_folder(f["file"])
        bs = chr(92)
        if staged:
            # 合意後の反映先（正本）。files の dest に書く。無いときは、作業フォルダと同じ場所
            dest = f.get("dest") or spec.get("server_root", "").replace("/", bs) + bs + spec.get("folder_name", "<作業フォルダ>") + bs
        else:
            dest = source_name + bs + (folder + bs if "/" in f["file"] else "")
        if f["handling"] == "新規":
            how = f"レビューのため、{'この置き場' if staged else 'このフォルダ'}に置く。合意後に、{dest} に新しく置く。"
        else:
            how = f"レビューのため、{'この置き場' if staged else 'このフォルダ'}に修正版を置く。合意後に、{dest} の旧版を {dest}old{bs} へ移し、修正版を上げる。"
        for c, v in enumerate([i, f["file"], f["handling"], how], 1):
            cell = ws2.cell(4 + i, c, v)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws2.row_dimensions[4 + i].height = 32
    for k, v in {"A": 5, "B": 70, "C": 10, "D": 80}.items():
        ws2.column_dimensions[k].width = v
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


if __name__ == "__main__":
    ensure_utf8()
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    build(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2])
    print("OK:", sys.argv[2])
