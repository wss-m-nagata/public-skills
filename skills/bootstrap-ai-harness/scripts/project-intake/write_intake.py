#!/usr/bin/env python3
"""入力シート（Excel）のコピーを作り、下書きの値を記入欄に書く。

資料から入力シートの下書きを作るときに使う。元のExcelは変更しない。

下書きの値は、次の形のJSONファイルで渡す（どれも省略できる）:
  {
    "items": {"<項目のID>": "<値>", ...},
    "lists": {"inputs": [{"<列のID>": "<値>", ...}, ...], "screens": [...]}
  }
- 項目のIDと列のIDは、references/intake-guide.md に載っている。
- 項目は、隠した「ID」列で探し、記入欄にだけ書く。
- すでに値がある記入欄は、上書きせず、スキップして表示する（利用者の記入を消さないため）。
- 一覧シートの行は、空いている行に、上から順に書く。
- 出力先に、元のExcelと同じパスは指定できない。出力先にファイルがあるときは、--overwrite を付けないと止める。
- openpyxl が要る。

使い方:
  python <スキル>/scripts/project-intake/write_intake.py <元の入力シート.xlsx> <下書きの出力先.xlsx> --values <下書き.json>
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_intake import C0, COL_ID, COL_INPUT, load_items  # noqa: E402
from read_intake import _header_row, _text  # noqa: E402


def _write_items(wb, data: dict, values: dict, skipped: list[str]) -> int:
    """項目の記入欄に値を書き、書いた数を返す。"""
    known = {i["id"] for s in data["sheets"] for i in s.get("items", [])}
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"項目のIDがありません: {', '.join(sorted(unknown))}")
    written = 0
    for sheet in data["sheets"]:
        if sheet["kind"] != "items":
            continue
        ws = wb[sheet["name"]]
        for row in range(_header_row(ws) + 1, ws.max_row + 1):
            item_id = _text(ws.cell(row=row, column=COL_ID).value)
            if item_id not in values:
                continue
            cell = ws.cell(row=row, column=COL_INPUT)
            if _text(cell.value):
                skipped.append(f"{sheet['name']}「{item_id}」：記入済みのため書かない")
                continue
            cell.value = values[item_id]
            written += 1
    return written


def _write_lists(wb, data: dict, lists: dict, skipped: list[str]) -> int:
    """一覧シートの空いている行に、上から順に書き、書いた行の数を返す。"""
    sheets = {s["key"]: s for s in data["sheets"] if s["kind"] == "list"}
    unknown = set(lists) - set(sheets)
    if unknown:
        raise ValueError(f"一覧シートのIDがありません: {', '.join(sorted(unknown))}")
    written = 0
    for key, rows in lists.items():
        sheet = sheets[key]
        ids = [c["id"] for c in sheet["columns"]]
        ws = wb[sheet["name"]]
        # 見出しの次の行は記入例のため、その次の行から、記入する行を数える
        first = _header_row(ws) + 2
        free = [r for r in range(first, first + sheet["rows"])
                if not any(_text(ws.cell(row=r, column=C0 + 1 + i).value) for i in range(len(ids)))]
        for record in rows:
            bad = set(record) - set(ids)
            if bad:
                raise ValueError(f"「{sheet['name']}」の列のIDがありません: {', '.join(sorted(bad))}")
            if not free:
                skipped.append(f"{sheet['name']}：空いている行が足りないため、残りの行を書かない")
                break
            row = free.pop(0)
            for i, cid in enumerate(ids):
                if record.get(cid):
                    ws.cell(row=row, column=C0 + 1 + i).value = record[cid]
            written += 1
    return written


def main() -> None:
    """引数を読み、元のExcelのコピーに下書きの値を書く。"""
    parser = argparse.ArgumentParser(description="入力シートのコピーを作り、下書きの値を記入欄に書く。")
    parser.add_argument("source", type=Path, help="元の入力シート（変更しない）")
    parser.add_argument("output", type=Path, help="下書きの出力先")
    parser.add_argument("--values", type=Path, required=True, help="下書きの値のJSONファイル")
    parser.add_argument("--overwrite", action="store_true", help="出力先にファイルがあっても上書きする")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    if args.source.resolve() == args.output.resolve():
        sys.exit("出力先に、元の入力シートと同じパスは指定できません。")
    if args.output.exists() and not args.overwrite:
        sys.exit(f"出力先にファイルがあります: {args.output}（上書きするときは --overwrite を付ける）")

    values = json.loads(args.values.read_text(encoding="utf-8"))
    data = load_items()
    # 元のExcelをコピーしてから、コピーを開いて書く
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.source, args.output)
    wb = load_workbook(args.output)
    skipped: list[str] = []
    n_items = _write_items(wb, data, values.get("items", {}), skipped)
    n_rows = _write_lists(wb, data, values.get("lists", {}), skipped)
    wb.save(args.output)

    print(f"作成: {args.output}")
    print(f"書いた項目: {n_items}、書いた一覧の行: {n_rows}")
    for s in skipped:
        print(f"スキップ: {s}")


if __name__ == "__main__":
    main()
