# -*- coding: utf-8 -*-
"""改訂の仕様JSON（revise_workbook.py）から、変更箇所一覧の仕様JSONを下書きする。

変更の中身は、revise_workbook.py の仕様JSONの groups に、すでに書いてある。
それを、変更箇所一覧の行に直して、同じ変更を何度も書かなくて済むようにする。
できた JSON を、build_change_list.py に渡す。確認資料は、論点を人が決めるため、これでは作らない。

使い方:
    python draft_change_list.py <メタJSON> <出力JSON>

    メタJSON の形:
    {
      "title": "<件名> 設計書の変更箇所一覧（YYYY-MM-DD）",
      "summary": "・<何のために、何を直したかを、1〜2文で>",
      "confirm_note": "今回は、<要確認の行が何についてか>です。",     // 要確認の行があるとき
      "folder_name": "<案件名>",
      "recipient": "<レビュー担当者の呼び名>",                       // 省略時は、設定の「レビュー担当者の呼び名」
      "specs": [                                                    // 直した Excel ごと
        {"spec": "revise_spec.json のパス", "target_file": "<フォルダ>/<元の設計書>.xlsx", "handling": "修正"}
      ],
      "extra_rows": [ {変更箇所一覧の行（confirm・file・sheet・spot・kind・before・after）} ]   // Excel 以外（図など）
    }

    groups の1つが、変更箇所一覧の1行になる。
      file   ＝ target_file、sheet ＝ groups の sheet、spot ＝ groups の place、kind ＝ groups の type
      confirm ＝ groups の confirm（省略時「任意」）
      before・after ＝ groups の before・after。無ければ、text の「変更前：…　変更後：…」から取る。
                      それも無いとき、追加は変更前を「（なし）」、削除は変更後を「（なし）」にする。
    表紙の版数と、変更履歴の行（版数が上がったことと、変更履歴の No.）の行を、自動で足す。
      （変更履歴の No. は、revise_workbook.py の出力 xlsx から読む。出力がまだ無いときは、No. を省く）
"""

import argparse
import json
import re
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from common import ensure_utf8  # noqa: E402

BEFORE_AFTER = re.compile(r"変更前：(.*?)　変更後：(.*)", re.DOTALL)
COVER_SHEET = "表紙"
VERSION_CELL = "J19"
HISTORY_SHEET = "変更履歴"
HISTORY_FIRST_ROW = 8
HISTORY_LAST_ROW = 33


def _before_after(group):
    """groups の1件から、変更前・変更後の文を求める。

    Args:
        group (dict): groups の1件。

    Returns:
        tuple[str, str, bool]: 変更前、変更後、決められたか（False は、text をそのまま変更後にした）。
    """
    if "before" in group or "after" in group:
        return group.get("before", "（なし）"), group.get("after", "（なし）"), True
    matched = BEFORE_AFTER.search(group["text"])
    if matched:
        return matched.group(1).strip(), matched.group(2).strip(), True
    if group["type"] == "追加":
        return "（なし）", group["text"], True
    if group["type"] == "削除":
        return group["text"], "（なし）", True
    return "－", group["text"], False


def _version_row(spec, target_file):
    """表紙の版数と、変更履歴の行の、変更箇所一覧の行を作る。

    Args:
        spec (dict): 改訂の仕様JSON。
        target_file (str): 正本の中の相対パス。

    Returns:
        dict | None: 変更箇所一覧の行。版数を読めないときは None。
    """
    old = None
    source = Path(spec["source"])
    if source.exists():
        old = openpyxl.load_workbook(source, data_only=True)[COVER_SHEET][
            VERSION_CELL
        ].value
    new = spec["history"]["version"]
    number = None
    output = Path(spec["output"])
    if output.exists():
        ws = openpyxl.load_workbook(output, data_only=True)[HISTORY_SHEET]
        for row in range(HISTORY_FIRST_ROW, HISTORY_LAST_ROW + 1):
            if ws.cell(row=row, column=2).value == new:
                number = ws.cell(row=row, column=1).value
    suffix = f"（No.{number}）" if number else ""
    return {
        "confirm": "任意",
        "file": target_file,
        "sheet": "表紙／変更履歴",
        "spot": f"{VERSION_CELL} 版数／変更履歴" + (f" No.{number}" if number else ""),
        "kind": "変更",
        "before": old or "－",
        "after": f"{new}。変更履歴に今回の変更{suffix}を追加した",
    }


def draft(meta):
    """メタJSONから、変更箇所一覧の仕様JSONを作る。

    Args:
        meta (dict): メタJSON。

    Returns:
        tuple[dict, list[str]]: 変更箇所一覧の仕様JSONと、警告。
    """
    rows, files, warnings = [], [], []
    for item in meta["specs"]:
        spec = json.loads(Path(item["spec"]).read_text(encoding="utf-8"))
        target = item["target_file"]
        files.append({"file": target, "handling": item.get("handling", "修正")})
        for group in spec["groups"]:
            before, after, decided = _before_after(group)
            if not decided:
                warnings.append(
                    f"変更前を決められませんでした（text に「変更前：…　変更後：…」が無い）: {group['sheet']} {group.get('place', '')}"
                )
            rows.append(
                {
                    "confirm": group.get("confirm", "任意"),
                    "file": target,
                    "sheet": group["sheet"],
                    "spot": group.get("place", ""),
                    "kind": group["type"],
                    "before": before,
                    "after": after,
                }
            )
        rows.append(_version_row(spec, target))

    for row in meta.get("extra_rows", []):
        rows.append(row)
        if not any(f["file"] == row["file"] for f in files):
            files.append({"file": row["file"], "handling": row.get("handling", "修正")})

    result = {
        "title": meta["title"],
        "summary": meta["summary"],
        "folder_name": meta["folder_name"],
        "rows": rows,
        "files": files,
    }
    for key in ("confirm_note", "recipient", "server_root"):
        if key in meta:
            result[key] = meta[key]
    if any(r["confirm"] == "要確認" for r in rows) and "confirm_note" not in meta:
        warnings.append(
            "「要確認」の行があるのに、メタJSONに confirm_note がありません。"
        )
    return result, warnings


def main():
    ensure_utf8()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("meta", help="メタJSON")
    parser.add_argument("output", help="出力する、変更箇所一覧の仕様JSON")
    args = parser.parse_args()

    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    result, warnings = draft(meta)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK: {args.output}（{len(result['rows'])}行）")
    for warning in warnings:
        print(f"  ! {warning}")


if __name__ == "__main__":
    main()
