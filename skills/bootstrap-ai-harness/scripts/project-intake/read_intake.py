#!/usr/bin/env python3
"""記入した入力シート（Excel）を読み、項目ごとの値をJSONで出す。

出すもの:
  items   項目ごとに、ID、シート、項目名、必須・任意、記入した値、既定値を当てた値（resolved）、状態。
          状態は「記入」「既定値」「未決定」「空欄」のいずれか（意味は references/intake-guide.md）。
  lists   一覧シート（インプット資料、画面とメニュー）の、書かれた行。
  missing 空欄の必須の項目と、条件に当てはまる条件付き必須の項目、一覧シートの不足。

- 項目は、項目の表の隠した「ID」列で探す。行の位置や項目名には頼らない。
- 「既定のまま」と書かれた記入欄は、空欄と同じに扱う。
- --missing を付けると、missing だけを出し、1件でもあれば終了コード1で終わる。
- Excelは読むだけで、変更しない。openpyxl が要る。

使い方:
  python <スキル>/scripts/project-intake/read_intake.py <入力シート.xlsx>
  python <スキル>/scripts/project-intake/read_intake.py <入力シート.xlsx> --missing
  python <スキル>/scripts/project-intake/read_intake.py <入力シート.xlsx> --sheet インフラ
  python <スキル>/scripts/project-intake/read_intake.py <入力シート.xlsx> --id infra.vpc --id infra.vpc_id
"""

import argparse
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_intake import C0, COL_ID, COL_INPUT, OPT, REQ, load_items  # noqa: E402

# 空欄と同じに扱う記入
_AS_EMPTY = {"既定のまま"}
# 未決定として扱う記入の書き出し
_UNDECIDED = ("未定", "不明")


def _text(value) -> str:
    """セルの値を、前後の空白を除いた文字列にする。"""
    return "" if value is None else str(value).strip()


def _header_row(ws) -> int:
    """表の見出し行（B列が「No」の行）を探す。"""
    for row in range(1, ws.max_row + 1):
        if _text(ws.cell(row=row, column=C0).value) == "No":
            return row
    raise ValueError(f"シート「{ws.title}」に、表の見出し（No）が見つかりません。")


def _read_items(wb, data: dict) -> list[dict]:
    """項目の表のシートを読み、項目ごとの値と状態を返す。"""
    values = {}
    for sheet in data["sheets"]:
        if sheet["kind"] != "items":
            continue
        ws = wb[sheet["name"]]
        for row in range(_header_row(ws) + 1, ws.max_row + 1):
            item_id = _text(ws.cell(row=row, column=COL_ID).value)
            if item_id:
                values[item_id] = _text(ws.cell(row=row, column=COL_INPUT).value)

    result = []
    for sheet in data["sheets"]:
        for item in sheet.get("items", []):
            if item["id"] not in values and item["id"] != "infra.api_origin":
                raise ValueError(f"項目「{item['name']}」（{item['id']}）が、Excelにありません。ひな形が古いか、行が消されています。")
            # APIの公開方式の行がない旧版にも既定値を適用する。
            raw = values.get(item["id"], "")
            value = "" if raw in _AS_EMPTY else raw
            default = item.get("default", "")
            if value.startswith(_UNDECIDED):
                status, resolved = "未決定", value
            elif value:
                if item["id"] == "infra.api_origin" and value not in item["choices"]:
                    raise ValueError(f"「{item['name']}」は {' または '.join(item['choices'])} を指定してください。")
                status, resolved = "記入", value
            elif default and item["required"] == OPT:
                status, resolved = "既定値", default
            else:
                status, resolved = "空欄", ""
            result.append({
                "id": item["id"], "sheet": sheet["name"], "name": item["name"], "required": item["required"],
                "required_if": item.get("required_if"), "value": value, "resolved": resolved, "status": status,
            })
    return result


def _read_lists(wb, data: dict) -> dict:
    """一覧シートを読み、書かれた行（No 以外の列がどれか1つでも書かれた行）を返す。"""
    lists = {}
    for sheet in data["sheets"]:
        if sheet["kind"] != "list":
            continue
        ws = wb[sheet["name"]]
        header = _header_row(ws)
        rows = []
        # 見出しの次の行は記入例のため、その次の行から読む
        for row in range(header + 2, ws.max_row + 1):
            record = {c["id"]: _text(ws.cell(row=row, column=C0 + 1 + i).value) for i, c in enumerate(sheet["columns"])}
            if any(record.values()):
                rows.append(record)
        lists[sheet["key"]] = rows
    return lists


def _missing(items: list[dict], lists: dict, data: dict) -> list[dict]:
    """空欄の必須の項目、条件に当てはまる条件付き必須の項目、一覧シートの不足を返す。"""
    resolved = {i["id"]: i["resolved"] for i in items}
    missing = []
    for i in items:
        if i["status"] != "空欄":
            continue
        cond = i["required_if"]
        if i["required"] == REQ or (cond and resolved.get(cond["id"]) == cond["equals"]):
            reason = "必須" if i["required"] == REQ else f"「{cond['id']}」が「{cond['equals']}」のため必須"
            missing.append({"sheet": i["sheet"], "id": i["id"], "name": i["name"], "reason": reason})
    for sheet in data["sheets"]:
        if sheet["kind"] != "list":
            continue
        rows = lists[sheet["key"]]
        need = sheet.get("required_rows", 0)
        if len(rows) < need:
            missing.append({"sheet": sheet["name"], "id": sheet["key"], "name": sheet["name"],
                            "reason": f"{need}行以上の記入が必要"})
        names = {c["id"]: c["name"] for c in sheet["columns"]}
        for n, row in enumerate(rows, start=1):
            for cid in sheet.get("required_with", []):
                if not row[cid]:
                    missing.append({"sheet": sheet["name"], "id": f"{sheet['key']}[{n}].{cid}",
                                    "name": f"{n}行目の「{names[cid]}」", "reason": "行を書いたときは必須"})
    return missing


def read_intake(path: Path) -> dict:
    """入力シートを読み、項目・一覧・不足をまとめて返す。"""
    data = load_items()
    wb = load_workbook(path, data_only=True)
    items = _read_items(wb, data)
    lists = _read_lists(wb, data)
    return {"items": items, "lists": lists, "missing": _missing(items, lists, data)}


def main() -> None:
    """引数を読み、入力シートの値をJSONで出す。"""
    parser = argparse.ArgumentParser(description="記入した入力シートを読み、項目ごとの値をJSONで出す。")
    parser.add_argument("xlsx", type=Path, help="記入した入力シート")
    parser.add_argument("--missing", action="store_true", help="空欄の必須の項目だけを出す（あれば終了コード1）")
    parser.add_argument("--sheet", action="append", default=[], help="出すシートの名前（何度でも指定できる）")
    parser.add_argument("--id", action="append", default=[], help="出す項目のID（何度でも指定できる）")
    args = parser.parse_args()

    # Windowsのコンソールでも日本語が化けないよう、出力をUTF-8にする
    sys.stdout.reconfigure(encoding="utf-8")
    result = read_intake(args.xlsx)
    if args.missing:
        print(json.dumps(result["missing"], ensure_ascii=False, indent=2))
        sys.exit(1 if result["missing"] else 0)
    if args.sheet or args.id:
        result["items"] = [i for i in result["items"] if i["sheet"] in args.sheet or i["id"] in args.id]
        sheet_keys = {s["key"] for s in load_items()["sheets"] if s["name"] in args.sheet}
        result["lists"] = {k: v for k, v in result["lists"].items() if k in sheet_keys}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
