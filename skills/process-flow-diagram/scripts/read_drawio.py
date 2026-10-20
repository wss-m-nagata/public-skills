# -*- coding: utf-8 -*-
"""処理フロー図・ER図（.drawio）を、読む順に並べたテキストにする。

drawio の XML から文字だけを抜き出すと、箱の並びも矢印のつながりも失われ、
「どの画面から、どの順で、何を呼び、どのテーブルを読み書きするか」が読み取れない。
このスクリプトは、次の形にそろえて出す。

- ページごとに、箱を上から下、左から右の順（座標の順）に並べる。
- 矢印は「呼び出し元 → 呼び出し先」と、ラベル（丸数字の順番）・色の意味を並べる。
  「読み取り元」のような枠が相手のときは、枠の中の箱（テーブル名）も添える。
- T.B.D の枠は、箇条書きごとに「解決済み」か「未解決」かを判定して、最後にまとめる。

使い方:
    python read_drawio.py <図>.drawio                 # 全ページの一覧（ページ名とセルの数）
    python read_drawio.py <図>.drawio --page ①        # ページ名に「①」を含むページを読む
    python read_drawio.py <図>.drawio --all           # 全ページを読む
    python read_drawio.py <図>.drawio --tbd           # 全ページの T.B.D だけを、判定つきで出す

ファイルサーバー上の図も、パスを / で区切って書けば、そのまま読める。
Windows のコンソールで文字化けするときは、環境変数 PYTHONIOENCODING=utf-8 を付けて実行する。
"""

import argparse
import base64
import html
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

# 線の色と意味（drawio_builder.py の C_* と同じ値）
EDGE_COLORS = {
    "#546E7A": "呼び出し",
    "#1976D2": "読み取り",
    "#2E7D32": "書き込み",
    "#C62828": "削除",
    "#8D6E63": "画面への戻り",
    "#5E35B1": "補助的な関係",
}

# T.B.D の枠の書き出し
TBD_HEAD = re.compile(r"T\.?B\.?D")

# 解決済みの印
RESOLVED_MARK = "（解決済み）"


def _text(value):
    """セルの value（HTML）を、改行を残したプレーンテキストにする。"""
    s = html.unescape(value or "")
    s = re.sub(r"<br\s*/?>|</div>|</p>|</li>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = s.replace(" ", " ")
    return re.sub(r"[ \t]*\n\s*", "\n", s).strip()


def _one_line(text, limit=None):
    """改行を「 / 」でつないで1行にする。"""
    s = text.replace("\n", " / ")
    return s if limit is None or len(s) <= limit else s[:limit] + "…"


def _style(cell):
    """セルの style を辞書にする。"""
    pairs = (
        item.split("=", 1)
        for item in (cell.get("style") or "").split(";")
        if "=" in item
    )
    return dict(pairs)


def _graph_model(diagram):
    """ページの mxGraphModel を返す。圧縮形式（base64 + deflate）のページも開く。"""
    model = diagram.find("mxGraphModel")
    if model is not None:
        return model
    data = (diagram.text or "").strip()
    if not data:
        return None
    xml = urllib.parse.unquote(
        zlib.decompress(base64.b64decode(data), -15).decode("utf-8")
    )
    return ET.fromstring(xml)


def _cells(diagram):
    """ページのセルを、id → セルの辞書で返す。"""
    model = _graph_model(diagram)
    if model is None:
        return {}
    return {cell.get("id"): cell for cell in model.iter("mxCell")}


def _position(cell, cells):
    """セルの絶対座標（左上の x, y）を返す。グループの中の箱は、親の座標を足す。"""
    x = y = 0.0
    while cell is not None:
        geometry = cell.find("mxGeometry")
        if geometry is not None and cell.get("vertex") == "1":
            x += float(geometry.get("x", 0))
            y += float(geometry.get("y", 0))
        cell = cells.get(cell.get("parent"))
    return x, y


def _box(cell, cells):
    """セルの絶対座標の矩形（左, 上, 右, 下）を返す。"""
    x, y = _position(cell, cells)
    geometry = cell.find("mxGeometry")
    width = float(geometry.get("width", 0)) if geometry is not None else 0.0
    height = float(geometry.get("height", 0)) if geometry is not None else 0.0
    return x, y, x + width, y + height


def _label(cell, cells):
    """矢印の端のセルの名前。枠（「読み取り元」など）なら、枠の中にある箱の名前も添える。

    枠の中の箱は、drawio の親子関係ではなく、位置で枠に重ねて置かれることが多い。
    そのため、矩形が枠の内側に収まる箱を、枠の中の箱とみなす。
    """
    if cell is None:
        return "（つながっていない）"
    name = _one_line(_text(cell.get("value")), 40)
    left, top, right, bottom = _box(cell, cells)
    inside = []
    for other in cells.values():
        if other is cell or other.get("vertex") != "1" or not _text(other.get("value")):
            continue
        o_left, o_top, o_right, o_bottom = _box(other, cells)
        if (
            left <= o_left
            and top <= o_top
            and o_right <= right
            and o_bottom <= bottom
            and (o_right - o_left) < (right - left)
        ):
            inside.append((o_top, o_left, _one_line(_text(other.get("value")), 30)))
    if not inside:
        return name
    return f"{name}［{'・'.join(text for _, _, text in sorted(inside))}］"


def _edge_label(edge, cells):
    """矢印のラベル。線の value のほか、線の子として置かれた文字も拾う。"""
    texts = [_text(edge.get("value"))]
    texts += [
        _text(c.get("value"))
        for c in cells.values()
        if c.get("parent") == edge.get("id")
    ]
    return _one_line(" ".join(t for t in texts if t))


def _tbd_items(text):
    """T.B.D の本文を箇条書き（「・」で始まる行から次の「・」の前まで）に分け、それぞれが解決済みかどうかを返す。

    最初の「・」より前の行は前置きとして扱い、判定に入れない。
    箇条書きが1つも無いときは、空のリストを返す（全文を読む必要がある）。
    """
    items, current = [], None
    for line in text.split("\n")[1:]:
        if line.startswith("※"):
            break
        if line.startswith("・"):
            if current is not None:
                items.append("\n".join(current))
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        items.append("\n".join(current))
    return [(item, RESOLVED_MARK in item) for item in items]


def read_page(name, cells):
    """1ページを、箱・矢印・T.B.D の順に出す。"""
    print(f"\n======== ページ：{name}")

    # 箱（座標の順）
    print("\n---- 箱（上から下、左から右）")
    boxes = []
    for cell in cells.values():
        text = _text(cell.get("value"))
        if (
            cell.get("vertex") == "1"
            and text
            and cells.get(cell.get("parent"), {}).get("edge") != "1"
        ):
            x, y = _position(cell, cells)
            boxes.append((round(y), round(x), cell.get("id"), text))
    for y, x, cell_id, text in sorted(boxes):
        print(f"(y={y}, x={x}) [{cell_id}] {_one_line(text)}")

    # 矢印（ラベルの丸数字の順）
    print("\n---- 矢印（呼び出し元 → 呼び出し先）")
    edges = []
    for cell in cells.values():
        if cell.get("edge") != "1":
            continue
        style = _style(cell)
        meaning = EDGE_COLORS.get(
            style.get("strokeColor", "").upper(), style.get("strokeColor", "色なし")
        )
        if style.get("dashed") == "1":
            meaning += "・点線"
        label = _edge_label(cell, cells)
        source = _label(cells.get(cell.get("source")), cells)
        target = _label(cells.get(cell.get("target")), cells)
        edges.append((label, f"{source} → {target}  〈{meaning}〉 {label}"))
    for _, line in sorted(edges):
        print(line)


def read_tbd(pages):
    """全ページの T.B.D を、箇条書きごとの判定つきで出す。"""
    unresolved = 0
    for name, cells in pages:
        for cell in cells.values():
            text = _text(cell.get("value"))
            if not TBD_HEAD.match(text):
                continue
            print(f"\n======== T.B.D：{name} [{cell.get('id')}]")
            items = _tbd_items(text)
            if not items:
                print("（箇条書きが無い。全文を読む）")
                print(text)
                continue
            for item, resolved in items:
                unresolved += 0 if resolved else 1
                print(f"{'解決済み' if resolved else '★未解決'}：{_one_line(item)}")
    print(f"\n未解決の箇条書き：{unresolved} 件")
    print(
        "「解決済み」でも、回答が「実装時に検討」のように先送りのものがある。回答の中身まで読むこと。"
    )


def main():
    """引数に従って、図を読む。"""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("path")
    parser.add_argument("--page", help="ページ名に含まれる文字")
    parser.add_argument("--all", action="store_true", help="全ページを読む")
    parser.add_argument("--tbd", action="store_true", help="T.B.D だけを出す")
    args = parser.parse_args()

    root = ET.parse(args.path).getroot()
    pages = [(d.get("name"), _cells(d)) for d in root.iter("diagram")]

    if args.tbd:
        read_tbd(pages)
        return
    if not args.page and not args.all:
        for name, cells in pages:
            print(f"{name}（セル {len(cells)}）")
        print(
            "\n--page <ページ名の一部> か --all で、ページを読む。凡例のページから読むこと。"
        )
        return
    for name, cells in pages:
        if args.all or args.page in name:
            read_page(name, cells)


if __name__ == "__main__":
    sys.exit(main())
