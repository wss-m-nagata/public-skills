# -*- coding: utf-8 -*-
"""機能別ER図（.drawio）が決まりどおりかを検査する。

生成直後の図だけでなく、人が drawio で動かしたあとの図にも使う。
エラーは決まりに反するもの、警告は人が判断するものである。

  1. XMLとして読めるか。セルIDがページ内で重なっていないか。
  2. 線の両端が実在する図形につながっているか。自分自身への線が無いか。
  3. 図形どうしが重なっていないか（帯の中の廃止テーブル、線のラベルは除く）。
  4. 出力用の枠が残っていないか。最背面（id="1" の直後）にある、文字の無い塗りの無い四角を枠とみなす。決まりで置かない。
     最背面以外にある枠・塗りのある枠は、ほかの図形との重なりのエラーとして出る。
  5. テーブルの箱の色と見出しの接頭辞（［変更］など）が合っているか。
     ★・✕が変更の箱にだけ付いているか。廃止の箱に線が付いていないか。
  6. テーブルのあるページに凡例があるか。
     決めた日・確認した日（「YYYY-MM-DD 決定」など）を書いていないか。
  7. 線が箱を横切っていないか。線どうしが同じ線上で重なっていないか。ラベルが箱に重なっていないか（見積もり）。
  8. --ddl-dir を付けたとき、箱の中身が現行DDLと合っているか（付けなければ DDL との照合はしない）。
  9. --spec を付けたとき、図の中身（テーブル・列）が spec から作った図と同じか。

使い方:
    py validate_feature_er.py <ER図.drawio> [--ddl-dir <DDLのフォルダ> [--alter-file-pattern <正規表現>]] [--spec <spec.json>]
"""

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry as G  # noqa: E402
import styles as S  # noqa: E402

# 箱の見出しから物理名を取り出す
_TABLE_RE = re.compile(r"（([a-z_]+\.[a-z_0-9]+)）")
# 列の行から物理列名を取り出す（最初の「（英小文字_数字）」）
_COL_RE = re.compile(r"（([a-z_][a-z0-9_]*)）")


def _style_map(style):
    """style 文字列を辞書にする。"""
    out = {}
    for part in (style or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
        elif part:
            out[part] = ""
    return out


def _abs_geom(cell, by_id):
    """図形の (x, y, w, h) をページ上の座標で返す。グループの中の図形は親の座標を足す。座標が無ければ None。"""
    g = cell.find("mxGeometry")
    if g is None or g.get("relative") == "1":
        return None
    x, y = float(g.get("x", 0)), float(g.get("y", 0))
    parent = by_id.get(cell.get("parent"))
    while parent is not None and parent.get("vertex") == "1":
        pg = parent.find("mxGeometry")
        if pg is not None:
            x += float(pg.get("x", 0))
            y += float(pg.get("y", 0))
        parent = by_id.get(parent.get("parent"))
    return (x, y, float(g.get("width", 0)), float(g.get("height", 0)))


def _inside(inner, outer):
    """inner が outer の内側にあるかを返す。"""
    return (inner[0] >= outer[0] and inner[1] >= outer[1]
            and inner[0] + inner[2] <= outer[0] + outer[2] and inner[1] + inner[3] <= outer[1] + outer[3])


def _entity_lines(value):
    """テーブルの箱の値から、見出しと列の行を取り出す。"""
    parts = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
             for p in re.split(r"</div>|<br\s*/?>", value)]
    return [p for p in parts if p]


def _status_of(style):
    """箱の塗りと枠の色から変更区分を判定する。どれにも当たらなければ None。"""
    sm = _style_map(style)
    for key, st in S.STATUS.items():
        if sm.get("fillColor", "").upper() == st["fill"] and sm.get("strokeColor", "").upper() == st["stroke"]:
            return key
    return None


def _is_entity(cell):
    """テーブルの箱かを返す（見出しが太字・中央寄せで「（スキーマ.物理名）」を含む）。"""
    value = cell.get("value") or ""
    return "font-weight:bold;text-align:center" in value.replace(" ", "") and bool(_TABLE_RE.search(value))


def _is_under_edge(cell, by_id):
    """線のラベル（線を親に持つ図形）かを返す。"""
    parent = by_id.get(cell.get("parent"))
    while parent is not None:
        if parent.get("edge") == "1":
            return True
        parent = by_id.get(parent.get("parent"))
    return False


def read_entities(diagram):
    """ページの中のテーブルの箱を [(セル, 物理名, 区分, 列の行)] で返す。--spec の比較にも使う。"""
    cells = list(diagram.find("mxGraphModel/root"))
    out = []
    for c in cells:
        if c.get("vertex") == "1" and _is_entity(c):
            lines = _entity_lines(c.get("value"))
            out.append((c, _TABLE_RE.search(c.get("value")).group(1), _status_of(c.get("style")), lines[2:]))
    return out


def _edge_path(edge, by_id):
    """線の通り道を、出口・折れ点・入口を結んだ直交の折れ線として見積もる。"""
    src, tgt = by_id.get(edge.get("source")), by_id.get(edge.get("target"))
    if src is None or tgt is None:
        return None
    sg, tg = _abs_geom(src, by_id), _abs_geom(tgt, by_id)
    if sg is None or tg is None:
        return None
    style = _style_map(edge.get("style"))

    def port(geom, prefix, other):
        """出入り口の座標と、縦に出入りするかを返す。指定が無ければ箱の中心と相手の向きで決める。"""
        fx, fy = float(style.get(f"{prefix}X", 0.5)), float(style.get(f"{prefix}Y", 0.5))
        point = (geom[0] + geom[2] * fx, geom[1] + geom[3] * fy)
        if f"{prefix}X" in style and fx in (0.0, 1.0):
            vertical = False
        elif f"{prefix}Y" in style and fy in (0.0, 1.0):
            vertical = True
        else:
            ocx, ocy = other[0] + other[2] / 2, other[1] + other[3] / 2
            vertical = abs(ocy - point[1]) > abs(ocx - point[0])
        return point, vertical

    (start, ev), (end, nv) = port(sg, "exit", tg), port(tg, "entry", sg)
    arr = edge.find("mxGeometry/Array")
    mids = [(float(p.get("x", 0)), float(p.get("y", 0))) for p in arr.findall("mxPoint")] if arr is not None else []
    return G.orthogonal_path(start, end, ev, nv, mids)


def _edge_labels(edge, by_id):
    """線のラベルを [(文字, 線の上の位置 t)] で返す（線の値と、線を親に持つラベル図形の値）。

    drawio はラベルの位置を mxGeometry の x（-1〜1、0が中央）で持つ。t=(x+1)/2 に直す。
    """
    def plain(v):
        return html.unescape(re.sub(r"<[^>]+>", "", v or "")).strip()

    def t_of(cell):
        g = cell.find("mxGeometry")
        return (float(g.get("x", 0)) + 1) / 2 if g is not None else 0.5

    out = []
    if plain(edge.get("value")):
        out.append((plain(edge.get("value")), t_of(edge)))
    for c in by_id.values():
        if c.get("parent") == edge.get("id") and plain(c.get("value")):
            out.append((plain(c.get("value")), t_of(c)))
    return out


def check_page(diagram, errors, warnings, entities_out):
    """1ページ分を検査する。"""
    pname = diagram.get("name")
    cells = list(diagram.find("mxGraphModel/root"))
    ids = [c.get("id") for c in cells]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"[{pname}] セルIDが重なっている: {sorted(dup)}")
    by_id = {c.get("id"): c for c in cells}

    # --- 出力用の枠（決まりで置かない）。id="1" の直後にある、文字の無い塗りの無い四角を枠とみなす ---
    frame = None
    if len(cells) > 2 and cells[1].get("id") == "1":
        cand = cells[2]
        if (_style_map(cand.get("style")).get("fillColor") == "none" and cand.get("vertex") == "1"
                and not (cand.get("value") or "").strip()):
            frame = cand
    if frame is not None:
        errors.append(f"[{pname}] 最背面に、文字の無い塗りの無い四角（id={frame.get('id')}）がある。"
                      "出力用の枠は置かない決まりのため、消す（前の版で作った図なら spec から作り直す）")

    # --- 図形を分類する（グループの中の図形も含め、線のラベルは除く） ---
    vertices = [c for c in cells if c.get("vertex") == "1" and c is not frame and not _is_under_edge(c, by_id)]
    groups = [c for c in vertices if "group" in _style_map(c.get("style"))]
    if groups:
        warnings.append(f"[{pname}] グループにした図形がある（{len(groups)} 個）。検査は中の図形を個別に見る")
    vertices = [c for c in vertices if c not in groups]
    edges = [c for c in cells if c.get("edge") == "1"]
    entities = {c.get("id"): c for c in vertices if _is_entity(c)}
    band = next((c for c in vertices if (c.get("value") or "").startswith("<b>削除予定のテーブル</b>")), None)
    geoms = {c.get("id"): _abs_geom(c, by_id) for c in vertices}

    # --- 線の両端 ---
    for e in edges:
        for end in ("source", "target"):
            ref = e.get(end)
            if not ref:
                errors.append(f"[{pname}] 線 {e.get('id')} の {end} がどこにもつながっていない")
            elif ref not in by_id:
                errors.append(f"[{pname}] 線 {e.get('id')} の {end} が存在しない図形 {ref} を指している")
        if e.get("source") and e.get("source") == e.get("target"):
            warnings.append(f"[{pname}] 線 {e.get('id')} は自分自身につながっている。箱を貫いて描かれるため、注記に書く")

    # --- 重なり ---
    band_geom = geoms.get(band.get("id")) if band is not None else None
    boxes = [(cid, g) for cid, g in geoms.items()
             if g is not None and (band is None or cid != band.get("id")) and not (band_geom and _inside(g, band_geom))]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if G.boxes_overlap(boxes[i][1], boxes[j][1]):
                errors.append(f"[{pname}] 図形が重なっている: {boxes[i][0]} と {boxes[j][0]}")

    # --- テーブルの箱 ---
    edge_ends = {e.get("source") for e in edges} | {e.get("target") for e in edges}
    for cid, c in entities.items():
        lines = _entity_lines(c.get("value"))
        table = _TABLE_RE.search(c.get("value")).group(1)
        status = _status_of(c.get("style"))
        header = lines[0] if lines else ""
        if status is None:
            errors.append(f"[{pname}] {table}: 箱の色が決まりの4種類のどれでもない")
            continue
        prefix = S.STATUS[status]["prefix"]
        if prefix and not header.startswith(prefix):
            errors.append(f"[{pname}] {table}: 箱の色は「{status}」だが、見出しに {prefix} が無い")
        for other, st in S.STATUS.items():
            if other != status and st["prefix"] and header.startswith(st["prefix"]):
                errors.append(f"[{pname}] {table}: 見出しは {st['prefix']} だが、箱の色が「{status}」になっている")
        cols = lines[2:]
        starred = [x for x in cols if x.startswith("★")]
        crossed = [x for x in cols if x.startswith("✕")]
        if status in ("unchanged", "new", "abolished") and (starred or crossed):
            errors.append(f"[{pname}] {table}: ★・✕は［変更］の箱にだけ付ける（{status} の箱に付いている）")
        if status == "changed" and not (starred or crossed):
            warnings.append(f"[{pname}] {table}: ［変更］の箱に★・✕の列が無い。変更箇所が読み手に分からない")
        if status == "abolished" and cid in edge_ends:
            errors.append(f"[{pname}] {table}: 廃止するテーブルに線が付いている")
        entities_out.append((pname, table, status, cols))

    if entities and not any((c.get("value") or "") == "凡例" for c in vertices):
        errors.append(f"[{pname}] 凡例が無い")

    # --- 決めた日・確認した日（「YYYY-MM-DD 決定」など）を書いていないか。線のラベルも含めて全セルを見る ---
    # 生成スクリプトと同じ関数で見る（見る範囲と判定をそろえるため）
    for c in cells:
        for line in S.plain_lines(c.get("value")):
            found = S.find_dated_decision(line)
            if found:
                errors.append(f"[{pname}] 決めた日・確認した日は書かない（{c.get('id')}：「{found}」）")

    # --- 線と箱・線どうし・ラベルの重なり（見積もり） ---
    paths = {e.get("id"): _edge_path(e, by_id) for e in edges}
    label_rects = []    # (線のID, 文字, 範囲)
    for e in edges:
        path = paths[e.get("id")]
        if path is None:
            continue
        for cid, c in entities.items():
            g = geoms.get(cid)
            if g and cid not in (e.get("source"), e.get("target")) and G.path_hits_box(path, g):
                warnings.append(f"[{pname}] 線 {e.get('id')} がテーブル "
                                f"{_TABLE_RE.search(c.get('value')).group(1)} の上を横切っている")
        for label, t in _edge_labels(e, by_id):
            lb = G.label_box(path, label, t=t)
            label_rects.append((e.get("id"), label, lb))
            for cid, c in entities.items():
                g = geoms.get(cid)
                if g and G.boxes_overlap(lb, g):
                    warnings.append(f"[{pname}] 線 {e.get('id')} のラベル「{label}」がテーブル "
                                    f"{_TABLE_RE.search(c.get('value')).group(1)} に重なっているおそれがある")
    for i in range(len(label_rects)):
        for j in range(i + 1, len(label_rects)):
            (ea, la, ra), (eb, lb_, rb) = label_rects[i], label_rects[j]
            if ea != eb and G.boxes_overlap(ra, rb):
                warnings.append(f"[{pname}] 線 {ea} のラベル「{la}」と、線 {eb} のラベル「{lb_}」が重なっているおそれがある")
    ekeys = [k for k in paths if paths[k]]
    for i in range(len(ekeys)):
        for j in range(i + 1, len(ekeys)):
            if G.collinear_overlap(paths[ekeys[i]], paths[ekeys[j]]):
                warnings.append(f"[{pname}] 線 {ekeys[i]} と {ekeys[j]} が同じ線上で重なっていて、見分けられないおそれがある")


def check_ddl(ddl_dir, alter_file_pattern, entities, errors, warnings):
    """箱の中身を現行DDLと照らし合わせる。"""
    from ddl_entities import load_tables  # noqa: E402
    # DDLが読めないときも、図の検査の結果は出したいため、止めずにエラーとして並べる
    try:
        tables = load_tables(ddl_dir, alter_file_pattern)
    except SystemExit as error:
        errors.append(f"[DDL] {str(error).removeprefix('エラー: ')}（DDLとの照らし合わせはしていない）")
        return
    for pname, table, status, cols in entities:
        if status == "new":
            if table in tables:
                warnings.append(f"[{pname}] {table}: ［新規］だが、すでにDDLにある（{tables[table].source}）。"
                                "DDLへ反映済みなら「変更なし」に直すか、合意の記録として残すかを決める")
            continue
        if table not in tables:
            if status == "abolished":
                warnings.append(f"[{pname}] {table}: ［廃止］だが、DDLに無い。削除がDDLへ反映済みなら、"
                                "図から外すか、合意の記録として残すかを決める")
            else:
                errors.append(f"[{pname}] {table}: DDLに無い。物理名の誤りか、新しく作るなら［新規］にする")
            continue
        ddl_cols = {c.name for c in tables[table].columns}
        for line in cols:
            body = line.lstrip("★✕ ")
            if body.startswith("U（") or not _COL_RE.search(line):
                continue
            name = _COL_RE.search(line).group(1)
            if line.startswith("★"):
                changed_mark = "（変更" in line or "今回変更" in line
                if name in ddl_cols and not changed_mark:
                    warnings.append(f"[{pname}] {table}.{name}: ★（追加）だが、すでにDDLにある列である。"
                                    "追加がDDLへ反映済みなら★を外す。既存の列を直す★なら「（変更：…）」か「← 今回変更」を添える")
                elif name not in ddl_cols and changed_mark:
                    errors.append(f"[{pname}] {table}.{name}: ★（変更）だが、DDLに無い列である。物理名を確かめる")
                continue
            if line.startswith("✕"):
                if name not in ddl_cols:
                    warnings.append(f"[{pname}] {table}.{name}: ✕（削除）だが、DDLに無い列である。"
                                    "削除がDDLへ反映済みなら行を消す。そうでなければ物理名を確かめる")
                continue
            if name not in ddl_cols:
                errors.append(f"[{pname}] {table}.{name}: 列がDDLに無い（物理名の誤り、または★の付け忘れ）")


def read_edges(diagram):
    """ページの中の線を、(親の物理名, 子の物理名, 線の種類, ラベル) の並びで返す。"""
    cells = {c.get("id"): c for c in diagram.find("mxGraphModel/root")}
    table_of = {cid: t for c, t, _, _ in read_entities(diagram) for cid in [c.get("id")]}
    out = []
    for c in cells.values():
        if c.get("edge") != "1":
            continue
        sm = _style_map(c.get("style"))
        kind = next((k for k, v in S.EDGE_KIND.items()
                     if v["end"] == sm.get("endArrow") and v["dashed"] == (sm.get("dashed") == "1")), "不明")
        if kind in ("value", "simplified"):
            kind = "value/simplified"
        label = html.unescape(re.sub(r"<[^>]+>", "", c.get("value") or "")).strip()
        out.append((table_of.get(c.get("source"), c.get("source")), table_of.get(c.get("target"), c.get("target")),
                    kind, label))
    return sorted(out)


def read_notes(diagram):
    """ページの中の注記を、(種類, 見出し) の並びで返す。"""
    style_to_kind = {}
    for k, v in S.NOTE_STYLE.items():
        style_to_kind.setdefault(v, k)
    out = []
    for c in diagram.find("mxGraphModel/root"):
        kind = style_to_kind.get(c.get("style") or "")
        if kind:
            m = re.match(r"<b>(.*?)</b>", c.get("value") or "")
            out.append((kind, html.unescape(m.group(1)) if m else ""))
    return sorted(out)


def check_spec(spec_path, diagrams, errors):
    """図の中身（テーブル・区分・列・線・注記の見出し）が、spec から作った図と同じかを見る。

    座標・見た目・注記の本文は比べない。drawio で人が中身を直したのに spec に写していない、
    あるいは spec が古い、という食い違いを見つけるためのものである。
    """
    from build_feature_er import SpecError, build  # noqa: E402
    try:
        built = build(json.loads(Path(spec_path).read_text(encoding="utf-8")))
    except SpecError as exc:
        errors.append(f"spec から図を作れない: {exc}")
        return

    def contents(diags):
        """ページ名ごとに、{物理名: (区分, 列の並び)} を作る。"""
        return {d.get("name"): {t: (s, c) for _, t, s, c in read_entities(d)}
                for d in diags if d.find("mxGraphModel") is not None}

    want, have = contents(built.findall("diagram")), contents(diagrams)
    for page in sorted(set(want) | set(have)):
        if page not in have:
            errors.append(f"[spec] ページ「{page}」が図に無い")
            continue
        if page not in want:
            errors.append(f"[spec] ページ「{page}」が spec に無い")
            continue
        for table in sorted(set(want[page]) | set(have[page])):
            if table not in have[page]:
                errors.append(f"[spec] [{page}] {table} が図に無い（spec にはある）")
                continue
            if table not in want[page]:
                errors.append(f"[spec] [{page}] {table} が spec に無い（図にはある）")
                continue
            (ws, wc), (hs, hc) = want[page][table], have[page][table]
            if ws != hs:
                errors.append(f"[spec] [{page}] {table} の区分が違う（spec: {ws}、図: {hs}）")
            for line in [x for x in wc if x not in hc]:
                errors.append(f"[spec] [{page}] {table}: spec にある行が図に無い「{line}」")
            for line in [x for x in hc if x not in wc]:
                errors.append(f"[spec] [{page}] {table}: 図にある行が spec に無い「{line}」")
            if [x for x in wc if x in hc] != [x for x in hc if x in wc]:
                errors.append(f"[spec] [{page}] {table}: 行の並び順が spec と違う")

    # 線と注記（T.B.D の枠を含む）も比べる
    built_by_name = {d.get("name"): d for d in built.findall("diagram")}
    have_by_name = {d.get("name"): d for d in diagrams if d.find("mxGraphModel") is not None}
    for page in sorted(set(built_by_name) & set(have_by_name)):
        we, he = read_edges(built_by_name[page]), read_edges(have_by_name[page])
        for x in [x for x in we if x not in he]:
            errors.append(f"[spec] [{page}] spec にある線が図に無い: {x[0]} → {x[1]}（{x[2]}）{x[3]}")
        for x in [x for x in he if x not in we]:
            errors.append(f"[spec] [{page}] 図にある線が spec に無い: {x[0]} → {x[1]}（{x[2]}）{x[3]}")
        wn, hn = read_notes(built_by_name[page]), read_notes(have_by_name[page])
        for x in [x for x in wn if x not in hn]:
            errors.append(f"[spec] [{page}] spec にある注記が図に無い: （{x[0]}）{x[1]}")
        for x in [x for x in hn if x not in wn]:
            errors.append(f"[spec] [{page}] 図にある注記が spec に無い: （{x[0]}）{x[1]}")


def main():
    """コマンドラインから呼ぶ入口。"""
    ap = argparse.ArgumentParser(description="機能別ER図が決まりどおりかを検査する")
    ap.add_argument("drawio", help="検査する .drawio")
    ap.add_argument("--ddl-dir", help="DDL（*.sql）のフォルダ。指定したときだけ、DDLとの照合を行う")
    ap.add_argument("--alter-file-pattern", help="ALTER TABLE を置いてよいファイル名の正規表現（ddl_entities.py と同じ）。省くと ALTER TABLE はエラーで止める")
    ap.add_argument("--spec", help="図を作った spec JSON。指定すると、図の中身が spec と同じかを見る")
    args = ap.parse_args()

    try:
        root = ET.parse(args.drawio).getroot()
    except ET.ParseError as exc:
        print(f"エラー: XMLとして読めない: {exc}")
        return 1
    errors, warnings, entities = [], [], []
    diagrams = root.findall("diagram")
    if not diagrams:
        errors.append("ページが1枚も無い")
    for d in diagrams:
        if d.find("mxGraphModel") is None:
            errors.append(f"[{d.get('name')}] 圧縮形式で保存されているため読めない（drawio の「ファイル」→「プロパティ」で"
                          "圧縮を外して保存し直す）")
            continue
        check_page(d, errors, warnings, entities)
    if args.ddl_dir and entities:
        check_ddl(args.ddl_dir, args.alter_file_pattern, entities, errors, warnings)
    if args.spec:
        check_spec(args.spec, diagrams, errors)

    for w in warnings:
        print(f"警告: {w}")
    for e in errors:
        print(f"エラー: {e}")
    print(f"結果: {len(diagrams)} ページ、テーブル {len(entities)} 箱、エラー {len(errors)} 件、警告 {len(warnings)} 件")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
