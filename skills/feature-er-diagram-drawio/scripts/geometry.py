# -*- coding: utf-8 -*-
"""線の通り道とラベルの位置の見積もり。

drawio の直交の線（orthogonalEdgeStyle）が実際に描く経路を、出入り口と折れ点から近似する。
生成スクリプトはラベルの位置（図の範囲に含めるため）に、検査スクリプトは横切り・重なりの判定に使う。
"""

import html
import math
import re
import unicodedata


def text_px(text, font_px):
    """1行の文字列を描いたときの幅（px）を見積もる。全角は1文字=font_px、半角は0.6倍とする。"""
    width = 0.0
    for ch in html.unescape(re.sub(r"<[^>]+>", "", text)):
        width += font_px if unicodedata.east_asian_width(ch) in ("W", "F", "A") else font_px * 0.6
    return width


def wrapped_lines(text, width_px, font_px):
    """指定の幅で折り返したときの行数を見積もる。"""
    usable = max(width_px, font_px * 4)
    return max(1, math.ceil(text_px(text, font_px) / usable))


def orthogonal_path(start, end, exit_vertical, entry_vertical, mids):
    """出口・折れ点・入口から、直交の折れ線を作る。

    引数:
        start, end: 出口と入口の座標。
        exit_vertical, entry_vertical: 出口・入口が箱の上下の辺にあるか（縦に出入りするか）。
        mids: 折れ点の座標の並び（無ければ空）。
    """
    if not mids:
        (sx, sy), (tx, ty) = start, end
        if not exit_vertical and not entry_vertical:
            mx = (sx + tx) / 2
            return [start, (mx, sy), (mx, ty), end]
        if exit_vertical and entry_vertical:
            my = (sy + ty) / 2
            return [start, (sx, my), (tx, my), end]
        if not exit_vertical:
            return [start, (tx, sy), end]
        return [start, (sx, ty), end]

    # 最初の区間は出る辺の向き、最後の区間は入る辺の向きで曲がるものとする
    pts = [start] + list(mids) + [end]
    path = [pts[0]]
    for i, p in enumerate(pts[1:], start=1):
        q = path[-1]
        if q[0] != p[0] and q[1] != p[1]:
            if i == 1:
                vertical_first = exit_vertical
            elif i == len(pts) - 1:
                vertical_first = not entry_vertical
            else:
                vertical_first = False
            path.append((q[0], p[1]) if vertical_first else (p[0], q[1]))
        path.append(p)
    return path


def path_point(path, t=0.5):
    """折れ線の始点から、全長の t（0〜1）の位置を返す。drawio は線のラベルを既定で t=0.5 に置く。"""
    segs = list(zip(path, path[1:]))
    total = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in segs)
    if total == 0:
        return path[0]
    rest = total * t
    for a, b in segs:
        length = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if rest <= length:
            r = rest / length if length else 0
            return (a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)
        rest -= length
    return path[-1]


def label_box(path, label, font_px=10, t=0.5):
    """線のラベルが占める矩形（x, y, w, h）を見積もる。t は線の上の位置（drawio の geometry x を (x+1)/2 にしたもの）。"""
    cx, cy = path_point(path, t)
    w = text_px(label, font_px) + 6
    h = font_px + 6
    return (cx - w / 2, cy - h / 2, w, h)


def path_hits_box(path, box, shrink=2):
    """折れ線のどれかの区間が箱の内側を通るかを返す（箱の縁を shrink px 内側に縮めて判定する）。"""
    x0, y0 = box[0] + shrink, box[1] + shrink
    x1, y1 = box[0] + box[2] - shrink, box[1] + box[3] - shrink
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        sx0, sx1 = sorted((ax, bx))
        sy0, sy1 = sorted((ay, by))
        if sx0 < x1 and x0 < sx1 + 0.01 and sy0 < y1 and y0 < sy1 + 0.01:
            return True
    return False


def boxes_overlap(a, b):
    """2つの矩形が重なっているかを返す（辺が触れているだけは重なりとしない）。"""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def collinear_overlap(path_a, path_b, min_len=6):
    """2本の折れ線に、同じ直線上で min_len px 以上重なる区間があるかを返す。"""
    for (a0, a1) in zip(path_a, path_a[1:]):
        for (b0, b1) in zip(path_b, path_b[1:]):
            # 横の区間どうし
            if a0[1] == a1[1] and b0[1] == b1[1] and abs(a0[1] - b0[1]) < 1:
                lo = max(min(a0[0], a1[0]), min(b0[0], b1[0]))
                hi = min(max(a0[0], a1[0]), max(b0[0], b1[0]))
                if hi - lo >= min_len:
                    return True
            # 縦の区間どうし
            if a0[0] == a1[0] and b0[0] == b1[0] and abs(a0[0] - b0[0]) < 1:
                lo = max(min(a0[1], a1[1]), min(b0[1], b1[1]))
                hi = min(max(a0[1], a1[1]), max(b0[1], b1[1]))
                if hi - lo >= min_len:
                    return True
    return False
