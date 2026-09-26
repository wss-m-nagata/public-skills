# -*- coding: utf-8 -*-
"""2つの .drawio をセル単位で比べ、何がどう変わったかを出す。

改版履歴
2026/09/03: 新規作成。人とAIが交互に図を直す運用に対応するため。

既にある図を直すときは、生成スクリプトの再実行ができない（人の手直しが消える）。
そのため XML を直接いじることになるが、直接いじると「意図した以外のところまで
変えていないか」が目視では確かめられない。ここで機械的に確かめる。

出力を「削除・追加・値・スタイル・線のつなぎ先・座標」に分けているのは、
どれが致命的かが違うためである。値や座標の変更は直したい内容そのものだが、
**線のつなぎ先やスタイルが勝手に変わっていたら、まず間違いなく事故**である。

使い方:
    python diff_drawio.py <変更前>.drawio <変更後>.drawio

意図した以外の項目が出たら、人が drawio で保存したものと競合している可能性が高い。
その場合は上書きを続けず、いったん報告する。

終了コードは、差分があれば 1、無ければ 0。圧縮形式など読めない形式なら 2。

改版履歴
2026/09/04: 圧縮形式の .drawio を検出して止めるようにした。
  その形式では mxGraphModel が現れずセルが1つも取れないため、
  「差分はありません」と誤って報告していた。
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio_builder import DrawioFormatError, assert_expanded_drawio  # noqa: E402


def load(path):
    """(ページ番号, セルID) をキーに、比較したい属性だけを取り出す。"""
    cells = {}
    # 圧縮形式ではセルが1つも取れず、「差分はありません」と誤って報告してしまう
    root = assert_expanded_drawio(path)
    for index, diagram in enumerate(root.findall("diagram")):
        for cell in diagram.findall(".//mxCell"):
            # id=0/1 は drawio が必ず持つ土台。比較しても意味がない
            if cell.get("id") in ("0", "1"):
                continue
            geometry = cell.find("mxGeometry")
            cells[(index, cell.get("id"))] = {
                "value": cell.get("value"),
                "style": cell.get("style"),
                "link": (cell.get("source"), cell.get("target")),
                "geometry": (
                    tuple(geometry.get(k) for k in ("x", "y", "width", "height"))
                    if geometry is not None
                    else None
                ),
            }
    return cells


def label(cell):
    """図形の見出し。タグを落として先頭だけ出す（T.B.D などは非常に長いため）。"""
    text = re.sub(r"<[^>]+>", "", (cell or {}).get("value") or "").strip()
    return text[:34] or "(無題)"


def _key(item):
    return "page%d/%s" % (item[0] + 1, item[1])


def diff(before_path, after_path):
    before, after = load(before_path), load(after_path)
    removed = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    common = set(before) & set(after)

    # 変更の種類ごとに分ける。どれが事故に近いかが違うため
    changed = {"値": [], "スタイル": [], "線のつなぎ先": [], "座標": []}
    for item in sorted(common):
        b, a = before[item], after[item]
        if b["value"] != a["value"]:
            changed["値"].append(item)
        if b["style"] != a["style"]:
            changed["スタイル"].append(item)
        if b["link"] != a["link"]:
            changed["線のつなぎ先"].append(item)
        if b["geometry"] != a["geometry"]:
            changed["座標"].append(item)

    print("削除: %d 件" % len(removed))
    for item in removed:
        print("  - %-14s %s" % (_key(item), label(before[item])))
    print("追加: %d 件" % len(added))
    for item in added:
        print("  + %-14s %s" % (_key(item), label(after[item])))

    for kind, items in changed.items():
        print("%sが変わった: %d 件" % (kind, len(items)))
        for item in items:
            if kind == "座標":
                print(
                    "  * %-14s %-34s %s -> %s"
                    % (
                        _key(item),
                        label(after[item]),
                        before[item]["geometry"],
                        after[item]["geometry"],
                    )
                )
            else:
                print("  * %-14s %s" % (_key(item), label(after[item])))

    total = len(removed) + len(added) + sum(len(v) for v in changed.values())
    if total == 0:
        print("\n差分はありません。")
    else:
        print("\n差分は %d 件です。" % total)
        if changed["線のつなぎ先"] or changed["スタイル"]:
            print(
                "**線のつなぎ先・スタイルの変更が出ています。**\n"
                "自分で変えた覚えが無ければ、人の編集と競合している可能性が高いので、\n"
                "上書きを続けずに報告してください。"
            )
    return total


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使い方: python diff_drawio.py <変更前>.drawio <変更後>.drawio")
        sys.exit(2)
    try:
        changed = diff(sys.argv[1], sys.argv[2])
    except DrawioFormatError as e:
        print(e)
        sys.exit(2)
    sys.exit(1 if changed else 0)
