# -*- coding: utf-8 -*-
"""
設計書の『変更履歴』シートに、新しい版の行を足す（または同じ版の行を書き直す）。

【背景】変更履歴の「変更箇所」「変更内容」は、シート名・項番・変更前／変更後を、決まった形で1行ずつ書く
（記入要領_共通シート.md の「シート『変更履歴』」）。
apply_mapping.py でセルに直接書くと、書き方がぶれ、直したセルと履歴が食い違っても気づけない。
このスクリプトは、変更の一覧（シートごとに複数）から、決まった形の文を組み立てて書き込み、
さらに、赤字にしたセルと、履歴に書いたセルを突き合わせて、書き漏れを検出する。

やること:
  1. 変更の一覧から、変更箇所（J列）と変更内容（Q列）を、記入要領の形に組み立てる。
       変更箇所：シート名の行と、全角スペースで字下げした項番の行
       変更内容：1行目に対応内容。続けて、「シート名 項番」の行と、字下げした「変更　変更前：…　変更後：…」の行
  2. 版数・変更日・区分・担当者とともに、変更履歴の行に書く。
       - 同じ版数の行が既にあれば、その行を書き直す（版数は同じまま、内容を直すとき）。
       - 無ければ、最初の空き行に足す。
       - 表紙の版数（J19）を、この版数にそろえる。版数が変わるときは、「表紙 J19（版数）」の変更も、自動で書く。
  3. 変更履歴の行の高さを、表示される行数に合わせる（fit_change_history_rows と同じ処理）。
  4. 赤字のセルと、一覧の cells を突き合わせる。
       - 赤字なのに、一覧に無いセル → 履歴の書き漏れ（警告）
       - 一覧にあるのに、赤字でないセル → 赤字の付け漏れ（警告）
     --strict を付けると、警告があれば、書き込まずに終了コード1で止まる。

使い方:
    python add_change_history.py <入力xlsx> <変更履歴JSON> <出力xlsx> [--strict]

    先に、変えたセルを赤字にしておく（mark_changed_cells.py）。そのあとで流す（突き合わせるため）。
    変更履歴の行を足す前に、normalize_change_history.py で結合・書式をそろえておく（古いテンプレートの場合）。

変更履歴JSON の形式:
{
  "version": "第1.1版",            # 表紙の版数にもなる
  "date": "2026-11-13",            # 変更日（YYYY-MM-DD）
  "kind": "変更",                  # 区分。「新規」または「変更」（新規のときは changes を書かない）
  "author": "永田",                # 担当者（AF列）
  "summary": "対応内容を1行で",     # 何をしたかだけ。経緯・Issue番号・社内の名前は書かない
  "changes": [                     # 変更の一覧。シートごとに、複数書ける
    {
      "sheet": "1. 外部インタフェース仕様",       # シート名
      "place": "特記事項（E32〜E34）",            # 項番など。変更箇所と、変更内容の見出しに書く（省略可）
      "cells": ["E32:E34"],                       # 赤字にしたセル。範囲（E32:E34）も書ける。突き合わせに使う
      "type": "追加",                             # 追加・変更・削除
      "text": "変更前：〇〇　変更後：△△"          # 変更の中身（追加・削除は、何を追加・削除したか）
    }
  ]
}

終了コード:
    0 = 正常終了（警告があっても、--strict が無ければ 0）
    1 = --strict で、警告があった（書き込まない）／入力が正しくない
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import range_boundaries
from openpyxl.utils.cell import get_column_letter

sys.path.insert(0, str(Path(__file__).parent))
from fit_change_history_rows import fit_rows  # noqa: E402
from xlsx_common import (  # noqa: E402
    ensure_utf8_stdio,
    get_merge_anchor,
    save_with_shapes,
)

# 変更履歴シートの、データの先頭行・最終行と、列
HISTORY_SHEET = "変更履歴"
FIRST_ROW = 8
LAST_ROW = 33
COL = {
    "No": "A",
    "版数": "B",
    "変更日": "D",
    "区分": "G",
    "変更箇所": "J",
    "変更内容": "Q",
    "担当者": "AF",
}

# 字下げ（全角スペース）と、表紙の版数のセル
INDENT = "　"
COVER_SHEET = "表紙"
COVER_VERSION_CELL = "J19"

# 赤字（RGB）
RED = "FFFF0000"


def _expand(cells):
    """セルの指定（E32・E32:E34）を、セル座標の集合に展開する。

    Args:
        cells: セルの指定のリスト。

    Returns:
        set[str]: セル座標の集合。
    """
    result = set()
    for spec in cells:
        min_col, min_row, max_col, max_row = range_boundaries(spec)
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                result.add(f"{get_column_letter(col)}{row}")
    return result


def _red_cells(ws):
    """シートの、文字色が赤のセル（結合セルは左上のセル）を返す。

    Args:
        ws: ワークシート。

    Returns:
        set[str]: 赤字のセル座標の集合。
    """
    result = set()
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in (None, ""):
                continue
            color = cell.font.color if cell.font else None
            if color is not None and color.type == "rgb" and color.rgb == RED:
                result.add(cell.coordinate)
    return result


def _build_texts(spec, version_changed, old_version):
    """変更箇所・変更内容の文を組み立てる。

    Args:
        spec: 変更履歴JSON。
        version_changed: 版数が変わるか（変わるときは、表紙の版数の変更も書く）。
        old_version: 直前の版数。

    Returns:
        tuple[str, str]: 変更箇所（J列）の文と、変更内容（Q列）の文。セル内改行は LF。
    """
    changes = list(spec.get("changes", []))
    if version_changed:
        changes.append(
            {
                "sheet": COVER_SHEET,
                "place": f"{COVER_VERSION_CELL}（版数）",
                "type": "変更",
                "text": f"変更前：{old_version}　変更後：{spec['version']}",
            }
        )

    # 変更箇所：シート名（出てきた順）と、その下に項番（重ねない）
    places = []
    for change in changes:
        sheet = change["sheet"]
        if sheet not in [s for s, _ in places]:
            places.append((sheet, []))
        place = change.get("place")
        for s, items in places:
            if s == sheet and place and place not in items:
                items.append(place)
    place_lines = []
    for sheet, items in places:
        place_lines.append(sheet)
        place_lines.extend(INDENT + item for item in items)

    # 変更内容：対応内容、続けて「シート名 項番」の見出しごとに、字下げした変更の行
    content_lines = [spec["summary"]]
    previous_header = None
    for change in changes:
        header = change["sheet"] + (
            f" {change['place']}" if change.get("place") else ""
        )
        if header != previous_header:
            content_lines.append(header)
            previous_header = header
        content_lines.append(f"{INDENT}{change['type']}{INDENT}{change['text']}")

    return "\n".join(place_lines), "\n".join(content_lines)


def main():
    """変更履歴の行を足す（または書き直す）。"""
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="変更履歴の行を足す")
    parser.add_argument("source", help="入力xlsx")
    parser.add_argument("spec", help="変更履歴JSON")
    parser.add_argument("output", help="出力xlsx（入力と同じパスは不可）")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="赤字と履歴の食い違いがあれば、書き込まずに止まる",
    )
    args = parser.parse_args()

    if Path(args.source).resolve() == Path(args.output).resolve():
        print("エラー: 出力は、入力と別のパスにしてください。", file=sys.stderr)
        return 1

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    for key in ("version", "date", "kind", "author", "summary"):
        if not spec.get(key):
            print(f"エラー: 変更履歴JSONに「{key}」がありません。", file=sys.stderr)
            return 1
    if spec["kind"] not in ("新規", "変更"):
        print("エラー: kind は「新規」か「変更」にしてください。", file=sys.stderr)
        return 1
    if spec["kind"] == "変更" and not spec.get("changes"):
        print(
            "エラー: kind が「変更」のときは、changes（変更の一覧）が必要です。",
            file=sys.stderr,
        )
        return 1
    for change in spec.get("changes", []):
        for key in ("sheet", "type", "text"):
            if not change.get(key):
                print(
                    f"エラー: changes の要素に「{key}」がありません: {change}",
                    file=sys.stderr,
                )
                return 1
        if change["type"] not in ("追加", "変更", "削除"):
            print(
                f"エラー: type は「追加」「変更」「削除」のどれかにしてください: {change['type']}",
                file=sys.stderr,
            )
            return 1

    wb = openpyxl.load_workbook(args.source)
    history = wb[HISTORY_SHEET]
    cover = wb[COVER_SHEET]

    # 書く行を決める（同じ版数の行があれば書き直し、無ければ最初の空き行）
    target_row = None
    last_used_row = FIRST_ROW - 1
    for row in range(FIRST_ROW, LAST_ROW + 1):
        version = history[f"{COL['版数']}{row}"].value
        if version == spec["version"]:
            target_row = row
        if version not in (None, ""):
            last_used_row = row
    rewriting = target_row is not None
    if target_row is None:
        target_row = last_used_row + 1
        if target_row > LAST_ROW:
            print(f"エラー: 変更履歴は {LAST_ROW} 行までです。", file=sys.stderr)
            return 1
    if rewriting and target_row != last_used_row:
        print(
            "エラー: 書き直せるのは、最後の版の行だけです（既存の履歴は変えない）。",
            file=sys.stderr,
        )
        return 1
    # 直前の版（書く行の1つ上）の版数。直前の版と版数が違えば、表紙の版数の変更も、履歴に書く
    previous_version = (
        history[f"{COL['版数']}{target_row - 1}"].value
        if target_row > FIRST_ROW
        else None
    )
    version_changed = (
        spec["kind"] == "変更"
        and bool(previous_version)
        and previous_version != spec["version"]
    )

    # 突き合わせ：赤字のセルと、一覧のセル
    listed = {}
    for change in spec.get("changes", []):
        if change["sheet"] not in wb.sheetnames:
            print(f"エラー: シート「{change['sheet']}」がありません。", file=sys.stderr)
            return 1
        ws = wb[change["sheet"]]
        for coordinate in _expand(change.get("cells", [])):
            listed.setdefault(change["sheet"], set()).add(
                get_merge_anchor(ws, coordinate)
            )

    warnings = []
    for ws in wb.worksheets:
        if ws.title in (HISTORY_SHEET, COVER_SHEET):
            continue
        reds = _red_cells(ws)
        names = listed.get(ws.title, set())
        for coordinate in sorted(reds - names):
            warnings.append(
                f"赤字なのに、変更履歴の一覧に無い: {ws.title} {coordinate}（書き漏れ）"
            )
        for coordinate in sorted(names - reds):
            warnings.append(
                f"一覧にあるのに、赤字でない: {ws.title} {coordinate}（赤字の付け漏れ。値が空のセルなら問題なし）"
            )
    for warning in warnings:
        print(f"警告：{warning}", file=sys.stderr)
    if warnings and args.strict:
        print("--strict のため、書き込まずに止めました。", file=sys.stderr)
        return 1

    # 書き込み
    place_text, content_text = _build_texts(spec, version_changed, previous_version)
    history[f"{COL['No']}{target_row}"] = target_row - FIRST_ROW + 1
    history[f"{COL['版数']}{target_row}"] = spec["version"]
    history[f"{COL['変更日']}{target_row}"] = datetime.datetime.strptime(
        spec["date"], "%Y-%m-%d"
    )
    history[f"{COL['区分']}{target_row}"] = spec["kind"]
    history[f"{COL['変更箇所']}{target_row}"] = (
        place_text if spec["kind"] == "変更" else "-"
    )
    history[f"{COL['変更内容']}{target_row}"] = (
        content_text if spec["kind"] == "変更" else spec["summary"]
    )
    history[f"{COL['担当者']}{target_row}"] = spec["author"]
    cover[COVER_VERSION_CELL] = spec["version"]
    fit_rows(history)

    save_with_shapes(wb, args.source, args.output)
    action = "書き直しました" if rewriting else "足しました"
    print(
        f"OK: 変更履歴の{target_row}行目に、{spec['version']}を{action}（警告 {len(warnings)} 件）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
