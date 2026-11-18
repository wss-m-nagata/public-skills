# -*- coding: utf-8 -*-
"""機能別ER図の中身（JSON）から .drawio を生成する。

見た目（配色・書式・凡例・線の通り道）はこのスクリプトで固定し、
どのテーブル・どの列・どの線・どの注記を載せるかだけを JSON に書く。
JSON の書き方は references/spec_format.md にある。

使い方:
    py build_feature_er.py <spec.json> --out <ER図_件名.drawio>

終了コード: 0＝警告なし、1＝エラー（図を作らない）、2＝警告あり（図は作る）。
"""

import argparse
import html
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry as G  # noqa: E402
import router as R  # noqa: E402
import styles as S  # noqa: E402

# 丸数字（ページ番号）。21ページ以上は作れない
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

# 配置の寸法
MARGIN_X = 60          # ページ左端からの余白
TITLE_Y = 30           # 見出しの上端
TITLE_LINE_H = 32      # 見出し1行の高さ（fontSize=22）
DESC_LINE_H = 20       # 説明1行の高さ（fontSize=13）
GAP_X = 100            # 横に並べる箱どうしの間隔（線を通すため広めに取る）
GAP_Y = 100            # 段どうしの間隔（rows 配置）
COLUMN_GAP_Y = 70      # 縦に積む箱どうしの間隔（columns 配置）
SECTION_H = 30         # 区分見出しの高さ（見出しと箱の間を含む）
LEGEND_CHIP_W = 240    # 凡例の見本の幅
LEGEND_CHIP_H = 30     # 凡例の見本の高さ
LEGEND_CHIP_STEP = 34  # 凡例の見本の間隔
NOTE_W = 820           # 注記の既定の幅
NOTE_GAP = 20          # 注記どうしの間隔
MIN_CONTENT_W = 1200   # 図の最小の幅（見出し・説明を置くため）
# 既定の並べ方。左から右へ、土台のマスタ → 業務のデータの順に、グループごとに列として並べる
DEFAULT_LAYOUT = "columns"

# JSON に書いてよいキー。書き間違いを黙って無視しないために使う。
_TOP_KEYS = {"entities", "pages", "changes"}
_PAGE_KEYS = {"subject", "description", "auto_description", "layout", "groups", "overrides", "edges",
              "notes", "legend_extra"}
_ENTITY_KEYS = {"table", "logical", "status", "pk", "cols", "width", "pos"}
_EDGE_KEYS = {"from", "to", "kind", "label", "exit", "entry", "points"}
_NOTE_KEYS = {"kind", "title", "lines", "width", "pos", "ai"}
_GROUP_KEYS = {"label", "entities"}
_CHANGES_KEYS = {"lead", "schema_owner", "rows"}
_ROW_KEYS = {"file", "table", "kind", "lines"}

# 変更点の表の「区分」と、箱の区分の対応
_KIND_TO_STATUS = {"変更": "changed", "新規": "new", "廃止": "abolished", "変更なし": "unchanged"}


class SpecError(ValueError):
    """JSON の書き方が仕様に合わないことを表す。"""


# ---------------------------------------------------------------------------
# 入力の検査
# ---------------------------------------------------------------------------

def _check_keys(obj, allowed, where):
    """dict であることと、未知のキーが無いことを確かめる。"""
    if not isinstance(obj, dict):
        raise SpecError(f"{where}: オブジェクト（{{...}}）で書く")
    unknown = set(obj) - allowed
    if unknown:
        raise SpecError(f"{where}: 未知のキー {sorted(unknown)}（使えるキー: {sorted(allowed)}）")


def _require(obj, keys, where):
    """必須のキーがそろっていることを確かめる。"""
    for key in keys:
        if key not in obj:
            raise SpecError(f"{where}: {key} が無い")


def _check_entity(key, ent, where):
    """箱の定義を確かめる。"""
    _check_keys(ent, _ENTITY_KEYS, where)
    _require(ent, ("table", "logical", "status", "pk"), where)
    if ent["status"] not in S.STATUS:
        raise SpecError(f"{where}: status は {list(S.STATUS)} のどれか（{ent['status']!r}）")
    if not re.fullmatch(r"[a-z_]+\.[a-z_0-9]+", ent["table"]):
        raise SpecError(f"{where}: table は「スキーマ.物理名」で書く（{ent['table']!r}）")
    if not ent["pk"]:
        raise SpecError(f"{where}: pk が空")
    if ent["status"] == "abolished" and "pos" in ent:
        raise SpecError(f"{where}: 廃止の箱は下部の帯に自動で並べるため、pos は指定できない")
    if "width" in ent:
        # 物理名は英字が続くため drawio は途中で折り返さず、見出しより狭いと切れて見える
        need = int(G.text_px(f"（{ent['table']}）", S.ENTITY_FONT_PX * 1.05) + 24)
        if ent["width"] < need:
            raise SpecError(f"{where}: width が見出しの物理名より狭い（{ent['width']}px）。{need}px 以上にするか、width を省く")


def validate_spec(spec):
    """JSON 全体を確かめる。図を作る前に、書き間違いをすべてここで止める。"""
    _check_keys(spec, _TOP_KEYS, "（最上位）")
    _require(spec, ("entities", "pages"), "（最上位）")
    if not spec["pages"]:
        raise SpecError("pages が空")
    total_pages = len(spec["pages"]) + (1 if spec.get("changes") else 0)
    if total_pages > len(CIRCLED):
        raise SpecError(f"ページは {len(CIRCLED)} 枚まで（{total_pages} 枚ある）。ファイルを分ける")

    # --- 箱（どのページでも使わない箱も確かめる） ---
    for key, ent in spec["entities"].items():
        _check_entity(key, ent, f"entities.{key}")

    # --- ページ ---
    for pi, page in enumerate(spec["pages"]):
        where = f"pages[{pi}]"
        _check_keys(page, _PAGE_KEYS, where)
        _require(page, ("subject", "description", "groups"), where)
        if page.get("layout", DEFAULT_LAYOUT) not in ("rows", "columns"):
            raise SpecError(f"{where}: layout は rows か columns（{page['layout']!r}）")
        seen = []
        for gi, group in enumerate(page["groups"]):
            _check_keys(group, _GROUP_KEYS, f"{where}.groups[{gi}]")
            _require(group, ("entities",), f"{where}.groups[{gi}]")
            if not group["entities"]:
                raise SpecError(f"{where}.groups[{gi}]: entities が空")
            for key in group["entities"]:
                if key not in spec["entities"]:
                    raise SpecError(f"{where}.groups[{gi}]: entities に無い箱 {key!r}")
                if key in seen:
                    raise SpecError(f"{where}: 箱 {key!r} を同じページに2回置いている")
                seen.append(key)
        for key, ov in page.get("overrides", {}).items():
            if key not in spec["entities"]:
                raise SpecError(f"{where}.overrides: entities に無い箱 {key!r}")
            merged = dict(spec["entities"][key])
            merged.update(ov)
            _check_entity(key, merged, f"{where}.overrides.{key}")
        statuses = {k: dict(spec["entities"][k], **page.get("overrides", {}).get(k, {}))["status"] for k in seen}
        for ei, e in enumerate(page.get("edges", [])):
            ew = f"{where}.edges[{ei}]"
            _check_keys(e, _EDGE_KEYS, ew)
            _require(e, ("from", "to"), ew)
            for end in ("from", "to"):
                if e[end] not in seen:
                    raise SpecError(f"{ew}: {end} の箱 {e[end]!r} がこのページに無い")
                if statuses[e[end]] == "abolished":
                    raise SpecError(f"{ew}: 廃止するテーブル {e[end]!r} には線を引かない")
            if e["from"] == e["to"]:
                raise SpecError(f"{ew}: 自分自身を参照する線は描けない。point の注記に「自己参照」として書く")
            kind = e.get("kind", "fk")
            if kind not in S.EDGE_KIND:
                raise SpecError(f"{ew}: kind は {list(S.EDGE_KIND)} のどれか（{kind!r}）")
            if kind == "simplified" and not e.get("label"):
                raise SpecError(f"{ew}: simplified の線には、実際の関係を label に書く")
        notes = page.get("notes", [])
        for ni, n in enumerate(notes):
            nw = f"{where}.notes[{ni}]"
            _check_keys(n, _NOTE_KEYS, nw)
            if n.get("kind") not in S.NOTE_STYLE:
                raise SpecError(f"{nw}: kind は {list(S.NOTE_STYLE)} のどれか")
            if not n.get("title"):
                raise SpecError(f"{nw}: title が無い")
            if n["kind"] == "tbd" and not n["title"].startswith("T.B.D"):
                raise SpecError(f"{nw}: T.B.D の枠の見出しは「T.B.D　〇〇に確認」で始める（処理フロー図と同じ書き方）")
            if "ai" in n and n["kind"] != "tbd":
                raise SpecError(f"{nw}: ai は T.B.D の枠（kind=tbd）にだけ書ける")
        if not any(n["kind"] == "scope" for n in notes):
            raise SpecError(f"{where}: 「この図に載せていないもの」（kind=scope）の注記が無い。載せないものが無ければ、そう書く")

    # --- 変更点の表 ---
    if spec.get("changes"):
        _check_changes(spec)


def _check_no_dated_decision(root):
    """出来上がった図の全セルに、決めた日・確認した日（「YYYY-MM-DD 決定」など）が無いかを見る。

    JSON の項目ごとではなく図の全セルを見るのは、検査スクリプトと見る範囲をそろえるためである。
    root: build で組み立てた mxfile 要素。
    """
    for diagram in root.iter("diagram"):
        for cell in diagram.iter("mxCell"):
            for line in S.plain_lines(cell.get("value")):
                found = S.find_dated_decision(line)
                if found:
                    raise SpecError(f"[{diagram.get('name')}] 決めた日・確認した日は書かない（「{found}」。行：「{line[:60]}」）。"
                                    "いつ決めたかは変更箇所一覧・課題管理票・処理フロー図に残す。"
                                    "基準日なら「（YYYY-MM-DD 時点）」と書く")


def _check_changes(spec):
    """変更点の表を確かめ、箱の区分と食い違っていないかを見る。"""
    ch = spec["changes"]
    _check_keys(ch, _CHANGES_KEYS, "changes")
    _require(ch, ("lead", "rows"), "changes")
    rows_by_table = {}
    for r, row in enumerate(ch["rows"]):
        _check_keys(row, _ROW_KEYS, f"changes.rows[{r}]")
        _require(row, ("table", "kind", "lines"), f"changes.rows[{r}]")
        if row["kind"] not in S.CHANGE_KIND_FILL:
            raise SpecError(f"changes.rows[{r}]: kind は {list(S.CHANGE_KIND_FILL)} のどれか")
        tables = row["table"] if isinstance(row["table"], list) else [row["table"]]
        for t in tables:
            if re.fullmatch(r"[a-z_]+\.[a-z_0-9]+", t):
                rows_by_table[t] = row["kind"]


    # 箱の区分（ページごとの上書きを含む）を集める
    statuses = {}
    for page in spec["pages"]:
        for group in page["groups"]:
            for key in group["entities"]:
                ent = dict(spec["entities"][key], **page.get("overrides", {}).get(key, {}))
                statuses.setdefault(ent["table"], set()).add(ent["status"])
    # ページによって区分が違ってよい（例：画面表示のページでは［変更］、CSV出力のページでは変更なし）。
    # 表の区分が、どのページの区分とも合わないときだけ食い違いとする
    for table, kind in rows_by_table.items():
        want = _KIND_TO_STATUS.get(kind)
        if want and table in statuses and want not in statuses[table]:
            raise SpecError(f"changes: {table} は表では「{kind}」だが、どのページの箱の区分とも合わない（{sorted(statuses[table])}）")
    for table, sts in statuses.items():
        if sts - {"unchanged"} and table not in rows_by_table:
            raise SpecError(f"changes: 変更のある {table} が、変更点の表に無い")


# ---------------------------------------------------------------------------
# 図形の値（HTML）と大きさ
# ---------------------------------------------------------------------------

def _rows_html(lines):
    """列の並びを <div> の並びにする。"""
    return "".join(f"<div>{html.escape(line, quote=False)}</div>" for line in lines)


def _entity_value(ent):
    """テーブルの箱の中身（見出し・主キー・そのほかの列）を作る。"""
    st = S.STATUS[ent["status"]]
    head = (f'<div style="font-weight:bold;text-align:center;padding:5px 8px;'
            f'border-bottom:1px solid {st["stroke"]};background:{st["header_bg"]};">'
            f'{st["prefix"]}{html.escape(ent["logical"], quote=False)}<br>（{ent["table"]}）</div>')
    pk_border = f'border-bottom:1px solid {st["stroke"]};' if ent["cols"] else ""
    pk = f'<div style="padding:5px 8px;{pk_border}">{_rows_html(ent["pk"])}</div>'
    body = f'<div style="padding:5px 8px;">{_rows_html(ent["cols"])}</div>' if ent["cols"] else ""
    return head + pk + body


def _entity_size(ent):
    """テーブルの箱の幅と高さを見積もる。幅を指定した場合は、折り返した行数で高さを出す。"""
    font = S.ENTITY_FONT_PX
    heads = [ent["logical"] + S.STATUS[ent["status"]]["prefix"], f"（{ent['table']}）"]
    lines = ent["pk"] + ent["cols"]
    header_w = max(G.text_px(t, font * 1.05) for t in heads)
    body_w = max([G.text_px(x, font) for x in lines] or [0])
    width = ent.get("width") or int(max(150, header_w, body_w) + 24)
    usable = width - 18
    head_lines = sum(G.wrapped_lines(t, usable, font * 1.05) for t in heads)
    body_lines = sum(G.wrapped_lines(t, usable, font) for t in lines)
    sections = 2 if ent["cols"] else 1
    height = (head_lines + body_lines) * S.LINE_HEIGHT + 10 + sections * 10 + 6
    return width, height


def _tbd_footer(note):
    """AIが書いた T.B.D の枠なら、末尾の定型文を返す。人が書いた枠（ai=false）や T.B.D 以外は空。"""
    return S.TBD_AI_FOOTER if note["kind"] == "tbd" and note.get("ai", True) else ""


def _note_value(note):
    """注記の中身を作る。行の中の **…** は太字にする。AIが書いた T.B.D には定型文を添える。"""
    parts = [f"<b>{html.escape(note['title'], quote=False)}</b>"]
    for line in note.get("lines", []):
        escaped = html.escape(line, quote=False)
        parts.append(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped))
    footer = _tbd_footer(note)
    if footer:
        parts.append(f'<span style="font-size:10px;color:#4D4D4D;">{html.escape(footer, quote=False)}</span>')
    return "<br>".join(parts)


def _note_size(note):
    """注記の幅と高さを見積もる。"""
    width = note.get("width", NOTE_W)
    font = S.NOTE_FONT_SIZE[note["kind"]]
    text_w = width - 24
    lines = G.wrapped_lines(note["title"], text_w, font)
    for line in note.get("lines", []):
        lines += G.wrapped_lines(line.replace("**", ""), text_w, font)
    if _tbd_footer(note):
        lines += G.wrapped_lines(_tbd_footer(note), text_w, 10)
    return width, lines * (font + 5) + 22


def _edge_label(e):
    """線のラベルを返す。省いたときは種類ごとの既定。"""
    label = e.get("label")
    if label is None:
        label = S.EDGE_KIND[e.get("kind", "fk")]["default_label"] or ""
    return label


# ---------------------------------------------------------------------------
# XML の組み立て
# ---------------------------------------------------------------------------

class Page:
    """1ページ分の図形を溜めて、mxGraphModel にする。"""

    def __init__(self):
        self.cells = []      # (id, attrs, geometry, points)
        self.boxes = {}      # 図形ID → (x, y, w, h)。用紙の大きさを決めるのに使う
        self.extra = []      # 線の折れ点・ラベルなど、用紙の大きさを決めるときに含める範囲

    def vertex(self, cid, value, style, x, y, w, h):
        """図形を足す。"""
        if cid in self.boxes:
            raise SpecError(f"図形ID {cid!r} が重なった（箱のキーを見直す）")
        self.cells.append((cid, dict(value=value, style=style, vertex="1", parent="1"),
                           dict(x=x, y=y, width=w, height=h), None))
        self.boxes[cid] = (x, y, w, h)

    def edge(self, cid, value, style, source, target, points, label_rect, label_x=0.0):
        """線を足す。折れ点とラベルの範囲も、用紙の大きさを決めるときに含める。label_x は線の上のラベルの位置（-1〜1、0が中央）。"""
        self.cells.append((cid, dict(value=value, style=style, edge="1", parent="1",
                                     source=source, target=target), {"label_x": label_x}, points))
        for px, py in points:
            self.extra.append((px, py, 0, 0))
        if label_rect:
            self.extra.append(label_rect)

    def bounds(self):
        """図形・折れ点・ラベルをすべて含む範囲を返す。"""
        rects = list(self.boxes.values()) + self.extra
        return (min(r[0] for r in rects), min(r[1] for r in rects),
                max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects))

    def to_diagram(self, root, page_id, name):
        """<diagram> を作る。用紙の大きさは、全図形の右端・下端から余白を取って決める。"""
        _, _, x1, y1 = self.bounds()
        m = S.PAGE_MARGIN
        page_w = int(math.ceil((x1 + 2 * m) / 100.0) * 100)
        page_h = int(math.ceil((y1 + 2 * m) / 100.0) * 100)

        diagram = ET.SubElement(root, "diagram", id=page_id, name=name)
        model = ET.SubElement(diagram, "mxGraphModel", dict(
            dx="1600", dy="900", grid="0", gridSize="10", guides="1", tooltips="1", connect="1",
            arrows="1", fold="1", page="1", pageScale="1", pageWidth=str(page_w),
            pageHeight=str(page_h), background="#FFFFFF", math="0", shadow="0"))
        cells = ET.SubElement(model, "root")
        ET.SubElement(cells, "mxCell", id="0")
        ET.SubElement(cells, "mxCell", id="1", parent="0")

        for cid, attrs, geom, points in self.cells:
            cell = ET.SubElement(cells, "mxCell", id=cid, **attrs)
            if attrs.get("edge") != "1":
                ET.SubElement(cell, "mxGeometry", {k: _num(v) for k, v in geom.items()} | {"as": "geometry"})
            else:
                g_attrs = {"relative": "1", "as": "geometry"}
                # 線のラベルを中央からずらしたときだけ、線の上の位置（x）を書く
                if geom["label_x"]:
                    g_attrs = {"x": _num(geom["label_x"])} | g_attrs
                g = ET.SubElement(cell, "mxGeometry", g_attrs)
                if points:
                    arr = ET.SubElement(g, "Array", {"as": "points"})
                    for px, py in points:
                        ET.SubElement(arr, "mxPoint", x=_num(px), y=_num(py))


def _num(v):
    """座標を drawio の書き方（整数なら小数点なし）にする。"""
    v = round(float(v), 1)
    return str(int(v)) if v == int(v) else str(v)


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

def _label_gaps(edges):
    """ラベル付きの線でつながる箱の組ごとに、ラベルが入る間隔を返す。"""
    gaps = {}
    for e in edges:
        label = _edge_label(e)
        if label:
            pair = frozenset((e["from"], e["to"]))
            gaps[pair] = max(gaps.get(pair, 0), int(G.text_px(label, 10) + 60))
    return gaps


def _layout_entities(page, groups, ents, gap_x, gap_y, column_gap_y):
    """箱を並べ、{箱: (x, y, w, h)}・区分見出しの位置・座標を指定した箱を返す。y は 0 起点で、あとでずらす。"""
    ids = [k for g in groups for k in g["entities"]]
    sizes = {k: _entity_size(ents[k]) for k in ids}
    gaps = _label_gaps(page.get("edges", []))
    placed, sections = {}, []

    if page.get("layout", DEFAULT_LAYOUT) == "rows":
        # 段ごとに左から右へ並べ、段は上から下へ積む
        y = 0
        for group in groups:
            if group.get("label"):
                sections.append((group["label"], MARGIN_X, y))
                y += SECTION_H
            x, row_h, prev = MARGIN_X, 0, None
            for key in group["entities"]:
                w, h = sizes[key]
                if prev is not None:
                    x += max(gap_x, gaps.get(frozenset((prev, key)), 0))
                placed[key] = (x, y, w, h)
                x += w
                row_h = max(row_h, h)
                prev = key
            y += row_h + gap_y
    else:
        # 列ごとに上から下へ積み、列は左から右へ並べる。見出しの無い列も見出しの分だけ下げてそろえる
        top = SECTION_H if any(g.get("label") for g in groups) else 0
        x, prev_keys = MARGIN_X, []
        for group in groups:
            if prev_keys:
                need = max([gaps.get(frozenset((p, k)), 0) for p in prev_keys for k in group["entities"]] or [0])
                x += max(gap_x + 20, need)
            y = top
            col_w = 0
            if group.get("label"):
                sections.append((group["label"], x, 0))
                col_w = int(G.text_px(group["label"], 14) + 10)
            for key in group["entities"]:
                w, h = sizes[key]
                placed[key] = (x, y, w, h)
                y += h + column_gap_y
                col_w = max(col_w, w)
            x += col_w
            prev_keys = group["entities"]

    # 座標を指定した箱は、指定どおりに置く（自動配置より優先する）
    fixed = set()
    for key in ids:
        if "pos" in ents[key]:
            px, py = ents[key]["pos"]
            w, h = sizes[key]
            placed[key] = (px, py, w, h)
            fixed.add(key)
    return placed, sections, fixed


def _abs_port(box, frac):
    """箱に対する出入り口の割合を、ページ上の座標にする。"""
    return (box[0] + box[2] * frac[0], box[1] + box[3] * frac[1])


# ---------------------------------------------------------------------------
# ページの生成
# ---------------------------------------------------------------------------

def _legend_lines(page, ents, has_changes_page):
    """凡例の見本の下に書く説明を、ページで使っている記号・線・注記に合わせて作る。"""
    all_cols = [c for e in ents.values() for c in e["pk"] + e["cols"]]
    lines = []
    if any(c.lstrip().startswith("★") for c in all_cols):
        lines.append("★ … 追加する列や制約（既存の列を直すときは「（変更：…）」を添える）")
    if any(c.lstrip().startswith("✕") for c in all_cols):
        lines.append("✕ … 削除する列")
    lines.append("PK … 主キー／FK … 外部キー／U … 一意制約")
    kinds = {e.get("kind", "fk") for e in page.get("edges", [])}
    if kinds & {"value", "simplified"}:
        lines.append("線：灰の実線＝FK／点線＝値のみ保持（FKなし）や簡略化した関係。")
    else:
        lines.append("線：灰の実線＝FK。")
    if "zero_to_one" in kinds:
        lines.append("線の端の「0か1」の記号＝子の行が無いこともある1対1。")
    if any(n["kind"] == "readonly" for n in page.get("notes", [])):
        lines.append("読み取りのみでFKの無い関係は線を引かず、注記に一覧で示す。")
    if any(n["kind"] == "tbd" for n in page.get("notes", [])):
        lines.append("赤い破線の枠（T.B.D）＝まだ決まっていないこと。決まったら枠ごと消す。")
    if any(e["status"] == "abolished" for e in ents.values()):
        lines.append("削除予定のテーブルは図の下部にまとめ、関連線は引かない。")
    if has_changes_page:
        lines.append("変更点の一覧は最後のページにある。")
    lines.extend(page.get("legend_extra", []))
    return lines


def _auto_description(ents, has_changes_page):
    """説明の決まり文句（箱の色と記号の読み方）を作る。"""
    statuses = {e["status"] for e in ents.values()}
    if statuses == {"unchanged"}:
        return "すべて現行DDLのまま使う（変更のあるテーブルは無い）。凡例はページ右上。"
    all_cols = [c for e in ents.values() for c in e["pk"] + e["cols"]]
    marks = []
    if any(c.lstrip().startswith("★") for c in all_cols):
        marks.append("★の付いた列が追加・変更")
    if any(c.lstrip().startswith("✕") for c in all_cols):
        marks.append("✕の付いた列が削除する列")
    text = "箱の色は現行DDLからの変更の有無を示す。"
    if marks:
        text += "、".join(marks) + "である。"
    text += "凡例はページ右上。"
    if has_changes_page:
        text += "変更点の一覧は最後のページにある。"
    return text


def _build_table_page(spec, page, index, has_changes_page, warnings):
    """「使うテーブル」のページを1枚作る。"""
    overrides = page.get("overrides", {})
    ids = [k for g in page["groups"] for k in g["entities"]]
    ents = {}
    for k in ids:
        ent = dict(spec["entities"][k])
        ent.update(overrides.get(k, {}))
        ent.setdefault("cols", [])
        ents[k] = ent
    num = CIRCLED[index]
    name = f"{num}使うテーブル（{page['subject']}）"
    title = f"{num} {page['subject']}で使うテーブル"
    edges = page.get("edges", [])
    notes = page.get("notes", [])

    # --- 凡例の大きさを決める（並べ方に関係しない） ---
    legend_lines = _legend_lines(page, ents, has_changes_page)
    used = [s for s in S.STATUS_ORDER if any(e["status"] == s for e in ents.values())]
    if "unchanged" not in used:
        used.insert(0, "unchanged")
    legend_w = int(max(LEGEND_CHIP_W, max(G.text_px(t, 12) for t in legend_lines) + 20))
    legend_text_h = len(legend_lines) * 18 + 6
    legend_h = 28 + len(used) * LEGEND_CHIP_STEP + legend_text_h
    desc = list(page["description"])
    if page.get("auto_description", True):
        desc.append(_auto_description(ents, has_changes_page))

    # --- 箱を並べ、線の通り道を探す（廃止するテーブルは、あとで下部の帯に入れる） ---
    # 線どうしの重なり・見つからない経路・置けないラベルがあれば、間隔を広げて並べ直す
    live_groups = [dict(g, entities=[k for k in g["entities"] if ents[k]["status"] != "abolished"])
                   for g in page["groups"]]
    live_groups = [g for g in live_groups if g["entities"]]
    live_ids = [k for g in live_groups for k in g["entities"]]
    dead_ids = [k for k in ids if ents[k]["status"] == "abolished"]
    gap_x, gap_y, column_gap_y = GAP_X, GAP_Y, COLUMN_GAP_Y
    for attempt in range(6):
        placed, sections, fixed = _layout_entities(page, live_groups, ents, gap_x, gap_y, column_gap_y)

        # 図の幅を決め、見出し・説明・凡例の位置を決める
        auto_right = max([placed[k][0] + placed[k][2] for k in live_ids if k not in fixed] or [MARGIN_X])
        content_right = max(auto_right, MARGIN_X + MIN_CONTENT_W, MARGIN_X + legend_w + 600)
        legend_x = content_right - legend_w
        text_w = legend_x - MARGIN_X - 40
        title_h = G.wrapped_lines(title, text_w, 22) * TITLE_LINE_H + 2
        desc_y = TITLE_Y + title_h + 6
        desc_h = sum(G.wrapped_lines(d, text_w, 13) for d in desc) * DESC_LINE_H + 6
        content_top = max(desc_y + desc_h, TITLE_Y + legend_h) + 40

        # 自動配置の箱と区分見出しを、説明・凡例の下へずらす
        placed = {k: (x, y + (0 if k in fixed else content_top), w, h) for k, (x, y, w, h) in placed.items()}
        section_rects = [(sx, sy + content_top, int(G.text_px(label, 14) + 10), 22) for label, sx, sy in sections]

        # 線の通り道を探す（区分見出しも障害物にし、説明・凡例の範囲には通さない）
        ports, points, overlaps, failed = R.route(edges, placed, section_rects, content_top - 10)

        # ラベルの位置を決める。箱やほかのラベルに重なるときは、線の上で位置をずらす
        labels, label_fail = [], []
        placed_labels = []
        for i, e in enumerate(edges):
            label = _edge_label(e)
            if not label:
                labels.append((None, 0.0))
                continue
            ef, nf = ports[(i, "exit")], ports[(i, "entry")]
            path = G.orthogonal_path(_abs_port(placed[e["from"]], ef), _abs_port(placed[e["to"]], nf),
                                     R.side_of(ef) in ("top", "bottom"), R.side_of(nf) in ("top", "bottom"),
                                     points[i])
            for t in (0.5, 0.35, 0.65, 0.25, 0.75, 0.15, 0.85):
                rect = G.label_box(path, label, t=t)
                if not any(G.boxes_overlap(rect, box) for box in list(placed.values()) + placed_labels):
                    labels.append((rect, round(2 * t - 1, 2)))
                    break
            else:
                rect = G.label_box(path, label)
                labels.append((rect, 0.0))
                label_fail.append(i)
            placed_labels.append(rect)
        if not overlaps and not failed and not label_fail:
            break
        gap_x, gap_y, column_gap_y = gap_x + 24, gap_y + 24, column_gap_y + 24

    # 並べ直しても解けなかったものは、警告として知らせる
    for i in failed:
        warnings.append(f"[{name}] 線 r{i + 1:02d}（{edges[i]['from']}→{edges[i]['to']}）の通り道が見つからなかった。"
                        "groups の並び順を変えるか、points を指定する")
    if overlaps:
        warnings.append(f"[{name}] ほかの線と同じ線上で重なる線が {overlaps} 本ある。groups の並び順を変えるか、points を指定する")
    for i in label_fail:
        warnings.append(f"[{name}] 線 r{i + 1:02d} のラベル「{_edge_label(edges[i])}」を、ほかと重ならない位置に置けなかった")

    out = Page()
    out.vertex("t1", html.escape(title, quote=False), S.TITLE_STYLE, MARGIN_X, TITLE_Y, text_w, title_h)
    out.vertex("t2", "<br>".join(html.escape(d, quote=False) for d in desc), S.DESC_STYLE,
               MARGIN_X, desc_y, text_w, desc_h)

    # --- 凡例 ---
    out.vertex("lg0", "凡例", S.LEGEND_HEAD_STYLE, legend_x, TITLE_Y, 200, 22)
    for i, s in enumerate(used):
        st = S.STATUS[s]
        out.vertex(f"lgp{i + 1}", st["legend"],
                   S.LEGEND_CHIP_STYLE.format(**st) + ("dashed=1;" if st["dashed"] else ""),
                   legend_x, TITLE_Y + 28 + i * LEGEND_CHIP_STEP, LEGEND_CHIP_W, LEGEND_CHIP_H)
    out.vertex("lgt", "<br>".join(html.escape(t, quote=False) for t in legend_lines), S.LEGEND_TEXT_STYLE,
               legend_x, TITLE_Y + 28 + len(used) * LEGEND_CHIP_STEP + 2, legend_w, legend_text_h)

    # --- 箱 ---
    for k in live_ids:
        st = S.STATUS[ents[k]["status"]]
        out.vertex(f"e_{k}", _entity_value(ents[k]), S.ENTITY_STYLE.format(**st), *placed[k])

    # --- 線 ---
    for i, e in enumerate(edges):
        kind = S.EDGE_KIND[e.get("kind", "fk")]
        label = _edge_label(e)
        style = S.EDGE_BASE.format(end=kind["end"])
        if label:
            style += S.EDGE_LABEL_EXTRA
        if kind["dashed"]:
            style += "dashed=1;"
        ef, nf = ports[(i, "exit")], ports[(i, "entry")]
        style += (f"exitX={ef[0]};exitY={ef[1]};exitDx=0;exitDy=0;"
                  f"entryX={nf[0]};entryY={nf[1]};entryDx=0;entryDy=0;")
        label_rect, label_x = labels[i]
        out.edge(f"r{i + 1:02d}", html.escape(label, quote=False), style, f"e_{e['from']}", f"e_{e['to']}",
                 points[i], label_rect, label_x)

    # --- 区分見出し。drawio はあとに書いた図形ほど手前に描くため、線のあとに置いて文字を線の上に出す ---
    for i, ((label, _, _), rect) in enumerate(zip(sections, section_rects)):
        out.vertex(f"s{i + 1}", html.escape(label, quote=False), S.SECTION_STYLE, *rect)

    # --- 注記（箱と線の下に、左から右へ折り返して並べる） ---
    bottom = max([y + h for (_, y, _, h) in placed.values()] + [r[1] + r[3] for r in out.extra] + [content_top])
    y, x, row_h = bottom + 60, MARGIN_X, 0
    for i, n in enumerate(notes):
        w, h = _note_size(n)
        if "pos" in n:
            nx_, ny_ = n["pos"]
        else:
            if x > MARGIN_X and x + w > content_right:
                y, x, row_h = y + row_h + NOTE_GAP, MARGIN_X, 0
            nx_, ny_ = x, y
            x += w + NOTE_GAP
            row_h = max(row_h, h)
        out.vertex(f"n{i + 1}", _note_value(n), S.NOTE_STYLE[n["kind"]], nx_, ny_, w, h)
    y += row_h

    # --- 削除予定のテーブルの帯 ---
    if dead_ids:
        band_y = y + 60
        sizes = [_entity_size(ents[k]) for k in dead_ids]
        band_w = max(980, sum(w for w, _ in sizes) + 40 * (len(sizes) - 1) + 40)
        band_h = max(h for _, h in sizes) + 54 + 30
        out.vertex("band", S.BAND_TEXT, S.BAND_STYLE, MARGIN_X, band_y, band_w, band_h)
        bx = MARGIN_X + 20
        for k, (w, h) in zip(dead_ids, sizes):
            st = S.STATUS["abolished"]
            out.vertex(f"e_{k}", _entity_value(ents[k]), S.ENTITY_STYLE.format(**st) + "dashed=1;",
                       bx, band_y + 54, w, h)
            bx += w + 40
    return out, name


def _build_changes_page(spec, index):
    """「凡例と、現行DDLからの変更点」のページを作る。"""
    ch = spec["changes"]
    num = CIRCLED[index]
    out = Page()
    out.vertex("l1", f"{num} 凡例と、現行DDLからの変更点", S.TITLE_STYLE, MARGIN_X, TITLE_Y, 1400, 34)
    out.vertex("l2", "凡例", S.LEGEND_HEAD_STYLE, MARGIN_X, 90, 300, 20)
    for i, s in enumerate(S.STATUS_ORDER):
        st = S.STATUS[s]
        legend = "［変更］現行DDLに手を入れる" if s == "changed" else st["legend"]
        out.vertex(f"lg{i + 1}", legend, S.LEGEND_CHIP_STYLE.format(**st) + ("dashed=1;" if st["dashed"] else ""),
                   MARGIN_X, 116 + i * 40, 220, 34)
    out.vertex("l3", "★ … その列・制約が変更箇所であることを示す。<br>✕ … 削除する列であることを示す。"
                     "<br>PK … 主キー／FK … 外部キー／U … 一意制約。",
               S.LEGEND_TEXT_STYLE, 300, 120, 760, 60)
    # スキーマの持ち主の行は、spec に書いたときだけ置く
    owner = ch.get("schema_owner", [])
    if owner:
        out.vertex("l4", "<br>".join(["スキーマの持ち主"] + [html.escape(t, quote=False) for t in owner]),
                   S.LEGEND_TEXT_STYLE, 300, 186, 760, 22 + 18 * len(owner))

    out.vertex("d1", "現行DDLからの変更点", S.LEGEND_HEAD_STYLE.replace("fontSize=14", "fontSize=15"),
               MARGIN_X, 280, 600, 24)
    out.vertex("d2", html.escape(ch["lead"], quote=False), S.LEGEND_TEXT_STYLE, MARGIN_X, 306, 1400, 20)

    widths = (520, 90, 1560)
    xs = (MARGIN_X, MARGIN_X + widths[0], MARGIN_X + widths[0] + widths[1])
    y = 340
    for c, label in enumerate(("ファイル / テーブル", "区分", "変更内容")):
        out.vertex(f"h{c}", label, S.TABLE_HEAD_STYLE, xs[c], y, widths[c], 38)
    y += 38
    for r, row in enumerate(ch["rows"]):
        fill = S.CHANGE_KIND_FILL[row["kind"]]
        tables = row["table"] if isinstance(row["table"], list) else [row["table"]]
        left_lines = [t for t in [row.get("file", "")] + tables if t]
        left = "<br>".join(html.escape(t, quote=False) for t in left_lines)
        n_lines = max(sum(G.wrapped_lines(t, widths[2] - 20, 12) for t in row["lines"]),
                      sum(G.wrapped_lines(t, widths[0] - 20, 12) for t in left_lines))
        h = max(38, n_lines * 20 + 18)
        cells = (left, row["kind"], "<br>".join(html.escape(t, quote=False) for t in row["lines"]))
        for c, value in enumerate(cells):
            out.vertex(f"c{r}_{c}", value, S.TABLE_CELL_STYLE.format(fill=fill, align="center" if c == 1 else "left"),
                       xs[c], y, widths[c], h)
        y += h
    return out, f"{num}凡例・現行DDLからの変更点"


def build(spec, warnings=None):
    """JSON の中身から mxfile 要素を作る。warnings に、自動では解けなかった配置の注意を足す。"""
    warnings = [] if warnings is None else warnings
    validate_spec(spec)
    has_changes = bool(spec.get("changes"))
    root = ET.Element("mxfile", host="feature-er-diagram-drawio", version="29.6.6",
                      pages=str(len(spec["pages"]) + (1 if has_changes else 0)))
    for i, page in enumerate(spec["pages"]):
        out, name = _build_table_page(spec, page, i, has_changes, warnings)
        out.to_diagram(root, f"erp{i + 1}", name)
    if has_changes:
        index = len(spec["pages"])
        out, name = _build_changes_page(spec, index)
        out.to_diagram(root, f"erp{index + 1}", name)
    # 決めた日・確認した日を書いていないか（ER図は、いつ決めたかを書かない）
    _check_no_dated_decision(root)
    return root


def main():
    """コマンドラインから呼ぶ入口。"""
    ap = argparse.ArgumentParser(description="機能別ER図の中身（JSON）から .drawio を作る")
    ap.add_argument("spec", help="図の中身を書いた JSON")
    ap.add_argument("--out", required=True, help="出力する .drawio")
    args = ap.parse_args()

    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"エラー: JSON として読めない: {exc}", file=sys.stderr)
        return 1
    warnings = []
    try:
        root = build(spec, warnings)
    except SpecError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    ET.indent(root, space="    ")
    Path(args.out).write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=False) + b"\n")
    for w in warnings:
        print(f"警告: {w}")
    print(f"出力: {args.out}（{len(root)} ページ）")
    # 図は出力したうえで、警告があれば終了コード 2 を返す（スクリプトから呼んだときに気づけるように）
    return 2 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
