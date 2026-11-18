# -*- coding: utf-8 -*-
"""線の通り道を、箱を障害物とした直交の最短経路で決める。

箱の周りに、箱から少しずつ離した縦横の候補線（通り道）を引き、その交点を結ぶ格子の上で、
「長さ＋曲がる回数＋ほかの線との重なり」が最小になる道を A* 探索で探す。
並べ方（rows / columns）や箱の組み合わせに関係なく、箱を横切らない経路を選べる。

流れ:
  1. 線ごとに、出る辺と入る辺を決める（候補の組み合わせを簡単な経路で見積もって選ぶ）。
  2. 同じ辺に付く線の出入り口を、相手の位置の順に辺の上へ散らす。
  3. 短い線から順に経路を探す。先に引いた線と重なるときは、出入り口を少しずらして探し直す。
     経路が見つからないときは、別の辺の組み合わせで探し直す。
"""

import heapq
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry as G  # noqa: E402

STUB = 18                          # 箱の辺から、最初に折れる点までの距離
LANE_STEPS = (18, 30, 42, 54, 66)  # 箱の辺から通り道までの距離の候補（箱ごとに縦横それぞれ）
INFLATE = 8                        # 箱をこの幅だけ太らせて障害物にする（線が箱の縁に沿わないように）
BEND_COST = 40                     # 1回曲がるごとの重み
OVERLAP_COST = 600                 # ほかの線と同じ線上を通るときの重み（重なりを避ける）
NUDGES = (0.0, 0.18, -0.18, 0.3, -0.3)  # 重なったときに出入り口をずらす量（辺の長さに対する割合）

_DIR = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}
_OPPOSITE = {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}


def side_of(frac):
    """出入り口の割合 (fx, fy) から、箱のどの辺かを返す。辺の上に無ければ None。"""
    fx, fy = frac
    if fx == 0:
        return "left"
    if fx == 1:
        return "right"
    if fy == 0:
        return "top"
    if fy == 1:
        return "bottom"
    return None


def _port_point(box, frac):
    """箱に対する割合を、ページ上の座標にする。"""
    return (round(box[0] + box[2] * frac[0], 1), round(box[1] + box[3] * frac[1], 1))


def _stub(point, side):
    """出入り口から辺の外へ STUB だけ出た点を返す。"""
    dx, dy = _DIR[side]
    return (round(point[0] + dx * STUB, 1), round(point[1] + dy * STUB, 1))


def _frac_on(side, f):
    """辺の上の位置 f（0〜1）を、出入り口の割合にする。"""
    f = round(min(max(f, 0.08), 0.92), 3)
    return {"top": (f, 0), "bottom": (f, 1), "left": (0, f), "right": (1, f)}[side]


def _along(frac, side):
    """出入り口の割合から、辺の上の位置（0〜1）を取り出す。"""
    return frac[0] if side in ("top", "bottom") else frac[1]


class Router:
    """障害物（箱・見出し）を避けて、線の通り道を探す。"""

    def __init__(self, boxes, extra_obstacles, top_bound):
        """boxes は {キー: (x, y, w, h)}、extra_obstacles は見出しなど線を通したくない範囲。"""
        self.obstacles = [(x - INFLATE, y - INFLATE, w + 2 * INFLATE, h + 2 * INFLATE)
                          for (x, y, w, h) in boxes.values()]
        self.obstacles += [(x - 4, y - 4, w + 8, h + 8) for (x, y, w, h) in extra_obstacles]
        self.top_bound = top_bound
        self.xs, self.ys = set(), set()
        for x, y, w, h in boxes.values():
            for d in LANE_STEPS:
                self.xs.update((round(x - d, 1), round(x + w + d, 1)))
                self.ys.update((round(y - d, 1), round(y + h + d, 1)))
        self.used_h = {}   # y → [(x0, x1)]。先に引いた線の横の区間
        self.used_v = {}   # x → [(y0, y1)]。先に引いた線の縦の区間

    def add_coords(self, points):
        """出入り口などの座標を、格子の候補線に足す。"""
        for x, y in points:
            self.xs.add(x)
            self.ys.add(y)

    def finalize(self):
        """候補線を並べ替え、座標から番号を引けるようにする。"""
        self.sx = sorted(self.xs)
        self.sy = sorted(v for v in self.ys if v >= self.top_bound)
        self.ix = {v: i for i, v in enumerate(self.sx)}
        self.iy = {v: i for i, v in enumerate(self.sy)}

    def blocked_point(self, p):
        """点が障害物の内側にあるかを返す。"""
        x, y = p
        return any(ox < x < ox + ow and oy < y < oy + oh for ox, oy, ow, oh in self.obstacles)

    def _blocked_segment(self, p, q):
        """縦か横の区間 p-q が障害物の内側を通るかを返す。"""
        x0, x1 = sorted((p[0], q[0]))
        y0, y1 = sorted((p[1], q[1]))
        for ox, oy, ow, oh in self.obstacles:
            if x0 == x1:
                if ox < x0 < ox + ow and y0 < oy + oh and oy < y1:
                    return True
            elif oy < y0 < oy + oh and x0 < ox + ow and ox < x1:
                return True
        return False

    def _overlap_len(self, p, q):
        """区間 p-q が、先に引いた線と同じ線上で重なる長さを返す。"""
        if p[1] == q[1]:
            lo, hi = sorted((p[0], q[0]))
            spans = self.used_h.get(p[1], [])
        else:
            lo, hi = sorted((p[1], q[1]))
            spans = self.used_v.get(p[0], [])
        return sum(max(0.0, min(hi, b) - max(lo, a)) for a, b in spans)

    def _neighbors(self, node):
        """格子の上で、上下左右の隣の点を返す（障害物を通る区間は除く）。"""
        i, j = self.ix.get(node[0]), self.iy.get(node[1])
        if i is None or j is None:
            return
        for di, dj, d in ((1, 0, "right"), (-1, 0, "left"), (0, 1, "bottom"), (0, -1, "top")):
            ni, nj = i + di, j + dj
            if not (0 <= ni < len(self.sx) and 0 <= nj < len(self.sy)):
                continue
            nxt = (self.sx[ni], self.sy[nj])
            if self.blocked_point(nxt) or self._blocked_segment(node, nxt):
                continue
            yield nxt, d

    def usable(self, p):
        """点が格子の上にあり、障害物の外にあるかを返す。"""
        return p[0] in self.ix and p[1] in self.iy and not self.blocked_point(p)

    def search(self, start, start_dir, goal, goal_dir):
        """start（向き start_dir で出る）から goal（向き goal_dir で入る）までの経路を探す。

        戻り値: (経路の点の並び, 重み, 重なった長さ)。見つからなければ None。
        """
        if not self.usable(start) or not self.usable(goal):
            return None
        # 重みが同じときに座標どうしを比べないよう、積んだ順の番号を2番目に入れる
        heap = [(0, 0, 0, 0.0, start, start_dir, None)]
        best = {(start, start_dir): 0}
        parent = {}
        counter = 0
        while heap:
            _, _, cost, over, node, d, prev = heapq.heappop(heap)
            if (node, d) in parent:
                continue
            parent[(node, d)] = prev
            if node == goal:
                path, key = [node], prev
                while key is not None:
                    path.append(key[0])
                    key = parent[key]
                return list(reversed(path)), cost + (0 if d == goal_dir else BEND_COST), over
            for nxt, nd in self._neighbors(node):
                if nd == _OPPOSITE[d]:
                    continue
                ov = self._overlap_len(node, nxt)
                c = cost + abs(nxt[0] - node[0]) + abs(nxt[1] - node[1])
                c += (BEND_COST if nd != d else 0) + (OVERLAP_COST if ov > 2 else 0)
                if c < best.get((nxt, nd), float("inf")):
                    best[(nxt, nd)] = c
                    counter += 1
                    h = abs(goal[0] - nxt[0]) + abs(goal[1] - nxt[1])
                    heapq.heappush(heap, (c + h, counter, c, over + (ov if ov > 2 else 0), nxt, nd, (node, d)))
        return None

    def mark(self, path):
        """経路の区間を記録する。あとの線は、ここと同じ線上を通ると重く数える。"""
        for p, q in zip(path, path[1:]):
            if p[1] == q[1]:
                self.used_h.setdefault(p[1], []).append(tuple(sorted((p[0], q[0]))))
            else:
                self.used_v.setdefault(p[0], []).append(tuple(sorted((p[1], q[1]))))


def _simplify(path):
    """一直線に並ぶ途中の点を除く。"""
    out = [path[0]]
    for p in path[1:]:
        if p == out[-1]:
            continue
        if len(out) >= 2 and (out[-2][0] == out[-1][0] == p[0] or out[-2][1] == out[-1][1] == p[1]):
            out[-1] = p
        else:
            out.append(p)
    return out


def _candidate_sides(a, b):
    """箱 a から箱 b へ向かう線の、出る辺と入る辺の候補を返す。"""
    acx, acy = a[0] + a[2] / 2, a[1] + a[3] / 2
    bcx, bcy = b[0] + b[2] / 2, b[1] + b[3] / 2
    h = ("right", "left") if bcx >= acx else ("left", "right")
    v = ("bottom", "top") if bcy >= acy else ("top", "bottom")
    return [h, v, (h[0], v[1]), (v[0], h[1]), ("bottom", "bottom"), ("right", "right"), ("left", "left")]


def _estimate(a, b, sides, boxes, skip, router):
    """出る辺・入る辺の組を、簡単な直交の経路で見積もる（小さいほどよい）。"""
    s, t = _port_point(a, _frac_on(sides[0], 0.5)), _port_point(b, _frac_on(sides[1], 0.5))
    ss, ts = _stub(s, sides[0]), _stub(t, sides[1])
    path = G.orthogonal_path(ss, ts, sides[0] in ("top", "bottom"), sides[1] in ("top", "bottom"), [])
    cost = sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(path, path[1:])) + 2 * STUB
    cost += BEND_COST * (len(path) - 2)
    cost += 1000 * sum(1 for k, box in boxes.items() if k not in skip and G.path_hits_box([s] + path + [t], box))
    # 出入り口の外の点が見出しなどにかかる組は、経路を探せないので避ける
    cost += 5000 * (router.blocked_point(ss) + router.blocked_point(ts))
    return cost


def route(edges, boxes, extra_obstacles, top_bound):
    """線の出入り口と折れ点を決める。

    引数:
        edges: [{"from", "to", ("exit"), ("entry"), ("points")}]
        boxes: {箱のキー: (x, y, w, h)}（ページ上の座標）
        extra_obstacles: 線を通したくない範囲（区分見出しなど）
        top_bound: これより上には線を通さない y

    戻り値:
        (出入り口 {(線の番号, "exit"/"entry"): (fx, fy)}, 折れ点 [[(x, y), ...]],
         重なりが残った線の数, 経路が見つからなかった線の番号)
    """
    probe = Router(boxes, extra_obstacles, top_bound)

    # --- 1. 出る辺・入る辺を決める（候補を見積もりの小さい順に並べておく） ---
    side_options = []
    for e in edges:
        a, b = boxes[e["from"]], boxes[e["to"]]
        if "exit" in e and "entry" in e:
            side_options.append([(side_of(tuple(e["exit"])), side_of(tuple(e["entry"])))])
            continue
        skip = {e["from"], e["to"]}
        side_options.append(sorted(_candidate_sides(a, b), key=lambda sd: _estimate(a, b, sd, boxes, skip, probe)))

    # --- 2. 同じ辺に付く線の出入り口を、相手の位置の順に散らす ---
    sides = [opts[0] for opts in side_options]
    ports, by_side = {}, {}
    for i, e in enumerate(edges):
        for end, key, side, other in (("exit", e["from"], sides[i][0], boxes[e["to"]]),
                                      ("entry", e["to"], sides[i][1], boxes[e["from"]])):
            if end in e:
                ports[(i, end)] = tuple(e[end])
                continue
            ox, oy, ow, oh = other
            order = (ox + ow / 2) if side in ("top", "bottom") else (oy + oh / 2)
            by_side.setdefault((key, side), []).append((order, i, end))
    for (key, side), items in by_side.items():
        items.sort()
        for j, (_, i, end) in enumerate(items):
            ports[(i, end)] = _frac_on(side, (j + 1) / (len(items) + 1))

    # 横どうしの線で、両端の辺にその線しか無く高さの範囲が重なるなら、高さをそろえて段差を無くす
    alone = {k for k, items in by_side.items() if len(items) == 1}
    for i, e in enumerate(edges):
        s0, s1 = sides[i]
        if "exit" in e or "entry" in e or {s0, s1} != {"left", "right"} or s0 == s1:
            continue
        if (e["from"], s0) not in alone or (e["to"], s1) not in alone:
            continue
        (_, ay, _, ah), (_, by, _, bh) = boxes[e["from"]], boxes[e["to"]]
        top, bottom = max(ay, by), min(ay + ah, by + bh)
        if top < bottom:
            yc = (top + bottom) / 2
            ports[(i, "exit")] = (ports[(i, "exit")][0], round((yc - ay) / ah, 3))
            ports[(i, "entry")] = (ports[(i, "entry")][0], round((yc - by) / bh, 3))

    # --- 3. 探し直しの候補（ずらした出入り口・別の辺の組）も含めて、格子の候補線を作る ---
    def variants(i):
        """線 i の、出入り口の候補を (出口の割合, 入口の割合) で、試す順に返す。"""
        e = edges[i]
        out = []
        base_e, base_n = ports[(i, "exit")], ports[(i, "entry")]
        if "exit" in e and "entry" in e:
            return [(base_e, base_n)]
        se, sn = side_of(base_e), side_of(base_n)
        for de in NUDGES:
            for dn in NUDGES:
                fe = base_e if "exit" in e else _frac_on(se, _along(base_e, se) + de)
                fn = base_n if "entry" in e else _frac_on(sn, _along(base_n, sn) + dn)
                if (fe, fn) not in out:
                    out.append((fe, fn))
        # 別の辺の組（中央の出入り口）
        for s0, s1 in side_options[i][1:]:
            out.append((base_e if "exit" in e else _frac_on(s0, 0.5), base_n if "entry" in e else _frac_on(s1, 0.5)))
        return out

    router = Router(boxes, extra_obstacles, top_bound)
    cand = {}
    for i, e in enumerate(edges):
        a, b = boxes[e["from"]], boxes[e["to"]]
        cand[i] = variants(i)
        for fe, fn in cand[i]:
            sp, tp = _port_point(a, fe), _port_point(b, fn)
            router.add_coords([sp, _stub(sp, side_of(fe)), tp, _stub(tp, side_of(fn))])
    router.finalize()

    # --- 4. 短い線から順に経路を探す ---
    def length(i):
        """線 i の出入り口どうしの距離（探す順番に使う）。"""
        e = edges[i]
        sp, tp = _port_point(boxes[e["from"]], ports[(i, "exit")]), _port_point(boxes[e["to"]], ports[(i, "entry")])
        return abs(sp[0] - tp[0]) + abs(sp[1] - tp[1])

    points = [[] for _ in edges]
    overlapped, failed = 0, []
    for i in sorted(range(len(edges)), key=length):
        e = edges[i]
        a, b = boxes[e["from"]], boxes[e["to"]]
        if "points" in e:
            points[i] = [tuple(p) for p in e["points"]]
            continue
        best = None
        for fe, fn in cand[i]:
            s0, s1 = side_of(fe), side_of(fn)
            sp, tp = _port_point(a, fe), _port_point(b, fn)
            found = router.search(_stub(sp, s0), s0, _stub(tp, s1), _OPPOSITE[s1])
            if found is None:
                continue
            path, cost, over = found
            if best is None or (over, cost) < (best[3], best[2]):
                best = (fe, fn, cost, over, [sp] + path + [tp])
            if over == 0:
                break
        if best is None:
            failed.append(i)
            continue
        fe, fn, _, over, full = best
        ports[(i, "exit")], ports[(i, "entry")] = fe, fn
        full = _simplify(full)
        router.mark(full)
        overlapped += 1 if over > 0 else 0
        # 両端（出入り口そのもの）は線の端点なので、折れ点には含めない
        points[i] = full[1:-1]
    return ports, points, overlapped, failed
