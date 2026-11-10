# -*- coding: utf-8 -*-
"""
画面遷移図テンプレートに、JSON の定義から画面遷移図を組み立てるスクリプト。

画面遷移図のテンプレートは、機能ごとのシート（1機能＝1シート。シート名は『1.  機能名 (機能ID)』）に
凡例の図形（箱・矢印）だけを持ち、遷移図の本体は空白の領域に描く作りになっている。
openpyxl では図形を作れないため、遷移図は Graphviz（dot）で画像（PNG）にしてシートに貼る。

【やること】
1. JSON の定義（機能、画面、遷移）から、Graphviz の .dot ソースを作る。
   - トップ画面は黒丸、表示画面（メインウィンドウ）は実線の箱「画面名／【画面ID】」、
     サブウィンドウは点線の箱、遷移は「ボタン／リンク名」付きの矢印で描く。
   - 画面設計書の記載範囲（水色の角丸の枠）は、groups で指定した枠として描く（枠の見出しは「画面設計書ID／名」）。
2. dot で PNG を作り、シートに貼る。
   貼り付けは、openpyxl の add_image() ではなく、シートの drawing の XML に
   <xdr:oneCellAnchor> として直接追記する（凡例の図形と共存させるため。insert_flow_diagram.py と同じ方式）。
3. 機能が複数あるときは、テンプレートのシートを複製して機能の数だけ作り、『目次』を同期する。
4. 画像の元になる .dot のソースを、シートの余白のセル（既定は AL5 から下）にテキストで残す。
5. 画像が凡例の図形と重なるときは、凡例の図形を下へずらす（画像の大きさは、印刷範囲の幅に収める）。

【前提】
- Graphviz の dot が PATH にあること（無い場合は --dot で実行ファイルのパスを指定する）。
- 入力の xlsx に、テンプレートのシート『1.  機能名 (機能ID)』（凡例の図形つき）があること。
  このシートは、1件目の機能のシートに改名して使い、2件目以降はこれを複製して作る。
- 画面遷移図の既存のシート（機能名のシート）を作り直すときは、元のテンプレートから実行し直す。

【JSON の形式】
    {
      "functions": [
        {
          "function_id": "11AA",
          "function_name": "企業情報管理",
          "rankdir": "LR",
          "groups": [
            {"id": "SW11AA01", "name": "企業情報照会"}
          ],
          "screens": [
            {"id": "ENTRY1", "name": "企業情報一覧照会", "kind": "top"},
            {"id": "W11AA0101", "name": "企業情報一覧照会", "kind": "main", "group": "SW11AA01"},
            {"id": "W91AA0101", "name": "住所情報検索", "kind": "sub"}
          ],
          "transitions": [
            {"from": "ENTRY1", "to": "W11AA0101"},
            {"from": "W11AA0101", "to": "W11AA0101", "label": "検索"},
            {"from": "W11AA0101", "to": "W91AA0101", "label": "住所検索"}
          ]
        }
      ]
    }

  - kind は top（トップ画面。黒丸。name はトップ画面の入口の名称）・main（表示画面）・sub（サブウィンドウ）のいずれか。
  - top の id は、遷移の from にだけ使う（画面一覧の画面IDではない）。
  - group は、その画面が入る「画面設計書の記載範囲」の枠の id（省略可）。
  - label は、遷移の起点のボタン／リンク名（省略可）。
  - rankdir は LR（左から右、既定）または TB（上から下）。
  - nodesep（箱どうしの間隔。既定 0.3）と ranksep（段どうしの間隔。既定 0.65）は、インチで指定する（省略可）。矢印のラベルが近いときに広げる。
  - anchor（省略可。既定は B7）は、画像を貼る位置のセル。source_anchor（省略可。既定は AL5）は dot ソースを書く先頭セル。
  - functions を使わず、機能1件の定義をそのまま JSON の最上位に書いてもよい。

使い方:
    python build_screen_flow.py <元xlsxパス> <JSONパス> <出力xlsxパス> [--dot dotのパス] [--font フォント名] [--dot-out dotソースの出力フォルダ]

例:
    python build_screen_flow.py 画面遷移図_(サブシステムID)_(サブシステム名).xlsx flow.json 出力.xlsx --dot-out dot_src

検証の方針:
    この出力は verify_layout.py の対象外（シート名の変更・凡例の図形の扱い・図形の個数で、必ず差分が出る）。
    代わりに、終了コード 0、標準出力の警告の確認、export_sheet_preview.py での見た目の確認を行う。

終了コード:
    0 = 成功（警告があるときは標準出力に表示）
    1 = 失敗（JSON の誤り、dot が無い、テンプレートのシートが無い 等）
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.worksheet.pagebreak import Break
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.utils.cell import coordinate_from_string
from PIL import Image as PILImage

sys.path.insert(0, str(Path(__file__).parent))
from restore_shapes import (
    restore_shapes,
    _sheet_name_to_target,
    _find_drawing_for_sheet,
    NS_R,
)
from xlsx_common import ensure_utf8_stdio

# テンプレートの機能シートの名前
TEMPLATE_SHEET = "1.  機能名 (機能ID)"
# 目次シートの名前と、最初の機能名を書くセル（以降2行おき）
TOC_SHEET = "目次"
TOC_FIRST_ROW = 7
TOC_ROW_STEP = 2
TOC_COL = 2
TOC_LAST_ROW = 35
# 既定の画像の貼り付け位置と、dot ソースの書き出し位置
DEFAULT_IMAGE_ANCHOR = "B7"
DEFAULT_SOURCE_ANCHOR = "AL5"
# 図を貼ってよい右端の列（AI列。ヘッダーの結合セルの右端に合わせる）
RIGHT_LIMIT_COL = column_index_from_string("AI")
# 画像と凡例の間にあけておく行数
GAP_ROWS = 2
# 凡例をずらす行数がこれ以下なら、改ページを入れない（0＝ずらさないときだけ。1行でもずらすと凡例の下端が1ページ目からはみ出すことがある）
MAX_SHIFT_WITHOUT_BREAK = 0
# 画像の下端を、この行（1始まり）までに収める（1ページに収まる行数の見積もり。
# 画像が改ページをまたがないようにするため）
MAX_IMAGE_BOTTOM_ROW = 46
# 画面の種類
KINDS = ("top", "main", "sub")
# 画像の元の解像度（dpi）。表示の大きさは別に計算するので、これは鮮明さだけに効く
RENDER_DPI = 200
EMU_PER_PIXEL = 9525
DEFAULT_FONT = "MS Gothic"
# 縮小率がこれを下回ったら、文字が読みにくいとして警告する
MIN_READABLE_SCALE = 0.55
# Excel のシート名の最大文字数と、使えない文字
SHEET_NAME_MAX = 31
SHEET_NAME_FORBIDDEN = re.compile(r"[\[\]:*?/\\]")


def _quote(text):
    """dot の文字列リテラルとして使えるよう、バックスラッシュ・ダブルクォート・改行を退避する"""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "")
        .replace("\n", "\\n")
    )


def _normalize_functions(spec):
    """JSON の最上位から、機能の定義のリストを取り出す"""
    if "functions" in spec:
        funcs = spec["functions"]
        if not isinstance(funcs, list) or not funcs:
            raise ValueError("functions は1件以上のリストで指定してください。")
        return funcs
    return [spec]


def _validate_function(func, index):
    """機能1件の定義が、仕様どおりかを調べる（仕様外の値は、補正せずエラーにする）"""
    label = f"functions[{index}]"
    for key in ("function_id", "function_name", "screens", "transitions"):
        if key not in func:
            raise ValueError(f"{label} に {key} がありません。")
    if func.get("rankdir", "LR") not in ("LR", "TB"):
        raise ValueError(f"{label}.rankdir は LR か TB を指定してください。")
    for key in ("nodesep", "ranksep"):
        v = func.get(key, 0.3)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.1 <= v <= 3:
            raise ValueError(f"{label}.{key} は 0.1 以上 3 以下の数値（インチ）で指定してください。")

    group_ids = set()
    for g in func.get("groups", []):
        if "id" not in g or "name" not in g:
            raise ValueError(f"{label}.groups の各要素には id と name が必要です。")
        if g["id"] in group_ids:
            raise ValueError(f"{label}.groups の id が重複しています: {g['id']}")
        group_ids.add(g["id"])

    screen_ids = set()
    for s in func["screens"]:
        for key in ("id", "name", "kind"):
            if key not in s:
                raise ValueError(f"{label}.screens の各要素には {key} が必要です: {s}")
        if s["kind"] not in KINDS:
            raise ValueError(
                f"{label}.screens の kind は {KINDS} のいずれかです: {s['id']} = {s['kind']}"
            )
        if s["id"] in screen_ids:
            raise ValueError(f"{label}.screens の id が重複しています: {s['id']}")
        screen_ids.add(s["id"])
        if s.get("group") is not None and s["group"] not in group_ids:
            raise ValueError(
                f"{label}: 画面 {s['id']} の group が groups に定義されていません: {s['group']}"
            )
        if s["kind"] == "top" and s.get("group") is not None:
            raise ValueError(
                f"{label}: トップ画面 {s['id']} には group を指定できません。"
            )

    for t in func["transitions"]:
        for key in ("from", "to"):
            if key not in t:
                raise ValueError(
                    f"{label}.transitions の各要素には {key} が必要です: {t}"
                )
            if t[key] not in screen_ids:
                raise ValueError(
                    f"{label}.transitions が、screens に無い画面を参照しています: {t[key]}"
                )
        kinds = {s["id"]: s["kind"] for s in func["screens"]}
        if kinds[t["to"]] == "top":
            raise ValueError(f"{label}: トップ画面 {t['to']} を遷移先にはできません。")


def build_dot(func, font):
    """
    機能1件の定義から、Graphviz の dot ソースを作る。
    引数: func=機能の定義（検証済み）、font=図中の文字のフォント名
    戻り値: dot ソースの文字列
    """
    rankdir = func.get("rankdir", "LR")
    # 箱どうし（nodesep）と段どうし（ranksep）の間隔（インチ）
    nodesep = func.get("nodesep", 0.3)
    ranksep = func.get("ranksep", 0.65)
    q = _quote

    # 画面IDから dot のノード名への対応（ID に記号があっても壊れないよう連番にする）
    node_names = {s["id"]: f"n{i}" for i, s in enumerate(func["screens"])}

    lines = [
        "digraph G {",
        f"    graph [rankdir={rankdir}, splines=polyline, nodesep={nodesep}, ranksep={ranksep}, "
        f'forcelabels=true, pad=0.2, fontname="{q(font)}", fontsize=10];',
        f'    node [fontname="{q(font)}", fontsize=10, shape=box, margin="0.12,0.08", '
        f"width=1.5, height=0.6];",
        f'    edge [fontname="{q(font)}", fontsize=10, arrowsize=0.8];',
    ]

    # 画面設計書の記載範囲の枠（水色の角丸）。枠に入る画面をまとめて書く
    for gi, g in enumerate(func.get("groups", [])):
        members = [s for s in func["screens"] if s.get("group") == g["id"]]
        lines.append(f"    subgraph cluster_{gi} {{")
        lines.append(f'        label="{q(g["id"] + "/" + g["name"])}";')
        lines.append(
            '        labelloc=t; style="rounded,filled"; fillcolor="#DDFFFF"; '
            'color="#2DC9C9"; margin=14;'
        )
        for s in members:
            lines.append(f"        {node_names[s['id']]};")
        lines.append("    }")

    # 画面のノード
    for s in func["screens"]:
        name = node_names[s["id"]]
        if s["kind"] == "top":
            # トップ画面は黒丸。入口の名称は黒丸の外側のラベルにする
            lines.append(
                f"    {name} [shape=circle, style=filled, fillcolor=black, color=black, "
                f'width=0.18, height=0.18, label="", xlabel="{q(s["name"])}"];'
            )
        else:
            style = "dashed" if s["kind"] == "sub" else "solid"
            # 左寄せで「画面名／【画面ID】」の2行にする
            label = f'{q(s["name"])}\\l【{q(s["id"])}】\\l'
            lines.append(f'    {name} [style={style}, label="{label}"];')

    # 遷移の矢印
    for t in func["transitions"]:
        attrs = ""
        if t.get("label"):
            attrs = f' [label="{q(t["label"])}"]'
        lines.append(f"    {node_names[t['from']]} -> {node_names[t['to']]}{attrs};")

    lines.append("}")
    return "\n".join(lines) + "\n"


def render_png(dot_source, out_png, dot_exe):
    """dot ソースから PNG を作る。dot が失敗したときは、dot のメッセージを添えて例外にする"""
    result = subprocess.run(
        [dot_exe, "-Tpng", f"-Gdpi={RENDER_DPI}", "-o", out_png],
        input=dot_source.encode("utf-8"),
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "dot の実行に失敗しました。画面・遷移の定義を確認してください。\n"
            + result.stderr.decode("utf-8", errors="replace")
        )


def _row_height_px(ws, row):
    """行の高さ（ピクセル）。個別の指定が無ければシートの既定値を使う"""
    pt = ws.row_dimensions[row].height or ws.sheet_format.defaultRowHeight or 15
    return pt * 96 / 72


def _col_width_px(ws, col):
    """列の幅（ピクセル）。個別の指定が無ければシートの既定値を使う"""
    letter = get_column_letter(col)
    width = None
    if letter in ws.column_dimensions:
        width = ws.column_dimensions[letter].width
    if not width:
        width = ws.sheet_format.defaultColWidth or 8.43
    # 既定フォント（最大数字幅5px）での、列幅（文字数）からピクセルへの換算
    return int(width * 5 + 5)


def compute_layout(ws, anchor_cell, png_path, legend_top_row0):
    """
    画像の貼り付け位置・表示の大きさと、凡例をずらす行数を求める。
    引数: ws=機能シート、anchor_cell=画像の左上のセル、png_path=PNG、legend_top_row0=凡例の最上端の行（0始まり）
    戻り値: dict（width_emu, height_emu, scale, shift_rows, bottom_row0）
    """
    col_letter, row = coordinate_from_string(anchor_cell)
    col = column_index_from_string(col_letter)

    # 右端（AI列）までの幅に収める。dot の PNG は、実寸（インチ）× 96 で表示の大きさにする
    with PILImage.open(png_path) as img:
        w_px, h_px = img.size
    natural_w = w_px / RENDER_DPI * 96
    natural_h = h_px / RENDER_DPI * 96
    avail_w = sum(_col_width_px(ws, c) for c in range(col, RIGHT_LIMIT_COL + 1))
    # 下端が MAX_IMAGE_BOTTOM_ROW を超えないよう、高さでも縮小率を決める
    avail_h = sum(_row_height_px(ws, r) for r in range(row, MAX_IMAGE_BOTTOM_ROW + 1))
    scale = min(1.0, avail_w / natural_w, avail_h / natural_h)
    width_px = natural_w * scale
    height_px = natural_h * scale

    # 画像の下端の行を、行の高さを足して求める
    cum = 0.0
    r = row
    while cum < height_px:
        cum += _row_height_px(ws, r)
        r += 1
    bottom_row0 = r - 1  # 画像が最後にかかる行（0始まり）

    # 凡例の上端より下にはみ出すなら、その分だけ凡例を下へずらす
    shift_rows = max(0, bottom_row0 + GAP_ROWS + 1 - legend_top_row0)
    return {
        "width_emu": int(width_px * EMU_PER_PIXEL),
        "height_emu": int(height_px * EMU_PER_PIXEL),
        "scale": scale,
        "shift_rows": shift_rows,
        "bottom_row0": bottom_row0,
    }


def _legend_rows(drawing_xml):
    """凡例の drawing の XML から、図形の位置の行（0始まり）の最小値と最大値を返す"""
    rows = [int(x) for x in re.findall(r"<xdr:row>(\d+)</xdr:row>", drawing_xml)]
    return min(rows), max(rows)


def _shift_rows(drawing_xml, delta, row_emu):
    """
    drawing の XML の、図形の位置を delta 行ずらす。
    アンカー（<xdr:row>）だけでなく、図形自身の絶対位置（最初の <a:off> の y）も同じ量だけずらす
    （グループ図形の中の子図形は、グループからの相対位置なので、触らない）。
    引数: row_emu=1行の高さ（EMU）。凡例の行は既定の高さなので、既定の行の高さを渡す。
    """
    if delta == 0:
        return drawing_xml

    def shift_anchor(m):
        body = re.sub(
            r"<xdr:row>(\d+)</xdr:row>",
            lambda r: f"<xdr:row>{int(r.group(1)) + delta}</xdr:row>",
            m.group(0),
        )
        return re.sub(
            r'<a:off x="(-?\d+)" y="(-?\d+)"/>',
            lambda o: f'<a:off x="{o.group(1)}" y="{int(o.group(2)) + delta * row_emu}"/>',
            body,
            count=1,
        )

    return re.sub(
        r"<xdr:(twoCellAnchor|oneCellAnchor)\b.*?</xdr:\1>",
        shift_anchor,
        drawing_xml,
        flags=re.S,
    )


def _picture_xml(shape_id, rid, col0, row0, width_emu, height_emu):
    """画像1枚分の <xdr:oneCellAnchor> の XML を作る"""
    return (
        f"<xdr:oneCellAnchor>"
        f"<xdr:from><xdr:col>{col0}</xdr:col><xdr:colOff>0</xdr:colOff>"
        f"<xdr:row>{row0}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>"
        f'<xdr:ext cx="{width_emu}" cy="{height_emu}"/>'
        f"<xdr:pic>"
        f"<xdr:nvPicPr>"
        f'<xdr:cNvPr id="{shape_id}" name="画面遷移図"/>'
        f'<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr>'
        f"</xdr:nvPicPr>"
        f"<xdr:blipFill>"
        f'<a:blip xmlns:r="{NS_R}" r:embed="{rid}"/>'
        f"<a:stretch><a:fillRect/></a:stretch>"
        f"</xdr:blipFill>"
        f"<xdr:spPr>"
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f"</xdr:spPr>"
        f"</xdr:pic>"
        f"<xdr:clientData/>"
        f"</xdr:oneCellAnchor>"
    )


def attach_flow_drawings(xlsx_in, xlsx_out, legend_xml, sheet_jobs, row_emu):
    """
    機能シートごとに drawing（凡例の図形＋画像）を新しく作り、シートに結びつける。
    引数:
      xlsx_in/xlsx_out=入出力のパス
      legend_xml=テンプレートの凡例の drawing の XML（文字列）
      sheet_jobs=[{"sheet", "png", "anchor", "width_emu", "height_emu", "shift_rows"}]
    """
    with zipfile.ZipFile(xlsx_in) as zin:
        names = zin.namelist()
        sheet_map = _sheet_name_to_target(zin)
        content_types = zin.read("[Content_Types].xml").decode("utf-8")
        updated = {}
        added = {}

        media_nums = [
            int(m.group(1))
            for n in names
            for m in [re.match(r"xl/media/image(\d+)\.\w+$", n)]
            if m
        ]
        next_media = max(media_nums, default=0) + 1
        drawing_nums = [
            int(m.group(1))
            for n in names
            for m in [re.match(r"xl/drawings/flowDrawing(\d+)\.xml$", n)]
            if m
        ]
        next_drawing = max(drawing_nums, default=0) + 1

        for job in sheet_jobs:
            sheet_target = sheet_map[job["sheet"]]

            # 凡例の図形をずらした drawing に、画像を足す
            drawing_xml = _shift_rows(legend_xml, job["shift_rows"], row_emu)
            ids = [int(x) for x in re.findall(r'<xdr:cNvPr id="(\d+)"', drawing_xml)]
            media_name = f"image{next_media}.png"
            next_media += 1
            col_letter, row = coordinate_from_string(job["anchor"])
            pic = _picture_xml(
                max(ids, default=0) + 1,
                "rId1",
                column_index_from_string(col_letter) - 1,
                row - 1,
                job["width_emu"],
                job["height_emu"],
            )
            if "</xdr:wsDr>" not in drawing_xml:
                raise ValueError("凡例の drawing XML のルート要素が見つかりません。")
            drawing_xml = drawing_xml.replace("</xdr:wsDr>", pic + "</xdr:wsDr>")

            drawing_name = f"flowDrawing{next_drawing}.xml"
            next_drawing += 1
            drawing_path = f"xl/drawings/{drawing_name}"
            added[drawing_path] = drawing_xml.encode("utf-8")
            added[f"xl/drawings/_rels/{drawing_name}.rels"] = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                f'Target="../media/{media_name}"/></Relationships>'
            ).encode("utf-8")
            with open(job["png"], "rb") as f:
                added[f"xl/media/{media_name}"] = f.read()
            content_types = content_types.replace(
                "</Types>",
                f'<Override PartName="/{drawing_path}" '
                'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/></Types>',
            )

            # シートの rels に drawing への関係を足す
            sheet_dir = "/".join(sheet_target.split("/")[:-1])
            sheet_file = sheet_target.split("/")[-1]
            rels_path = f"{sheet_dir}/_rels/{sheet_file}.rels"
            if rels_path in names:
                rels_xml = zin.read(rels_path).decode("utf-8")
            else:
                rels_xml = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    "</Relationships>"
                )
            rid_nums = [int(x) for x in re.findall(r'Id="rId(\d+)"', rels_xml)]
            rid = f"rId{max(rid_nums, default=0) + 1}"
            rels_xml = rels_xml.replace(
                "</Relationships>",
                f'<Relationship Id="{rid}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                f'Target="../drawings/{drawing_name}"/></Relationships>',
            )
            updated[rels_path] = rels_xml.encode("utf-8")

            # シートの XML に <drawing r:id="..."/> を足す
            sheet_xml = zin.read(sheet_target).decode("utf-8")
            if re.search(r"<drawing\b", sheet_xml):
                raise ValueError(
                    f"シート『{job['sheet']}』には既に drawing があります。"
                )
            if "xmlns:r=" not in sheet_xml.split(">", 1)[0]:
                sheet_xml = sheet_xml.replace(
                    "<worksheet ", f'<worksheet xmlns:r="{NS_R}" ', 1
                )
            drawing_el = f'<drawing r:id="{rid}"/>'
            for tag in ("<legacyDrawing", "<tableParts", "<extLst>"):
                if tag in sheet_xml:
                    sheet_xml = sheet_xml.replace(tag, drawing_el + tag, 1)
                    break
            else:
                sheet_xml = sheet_xml.replace(
                    "</worksheet>", drawing_el + "</worksheet>"
                )
            updated[sheet_target] = sheet_xml.encode("utf-8")

        if 'Extension="png"' not in content_types:
            content_types = content_types.replace(
                "</Types>", '<Default Extension="png" ContentType="image/png"/></Types>'
            )
        updated["[Content_Types].xml"] = content_types.encode("utf-8")

        with zipfile.ZipFile(xlsx_out, "w", zipfile.ZIP_DEFLATED) as zout:
            written = set()
            for item in zin.infolist():
                zout.writestr(item, updated.get(item.filename, zin.read(item.filename)))
                written.add(item.filename)
            for path, data in list(added.items()) + list(updated.items()):
                if path not in written:
                    zout.writestr(path, data)
                    written.add(path)


def _sheet_title(index, func):
    """機能シートの名前（兼 シート内の見出し）。例: 『1. 企業情報管理(11AA)』"""
    title = f"{index}. {func['function_name']}({func['function_id']})"
    if len(title) > SHEET_NAME_MAX:
        raise ValueError(
            f"シート名が{SHEET_NAME_MAX}文字を超えます（{len(title)}文字）: {title}\n"
            "機能名を短くしてください。"
        )
    if SHEET_NAME_FORBIDDEN.search(title):
        raise ValueError(f"シート名に使えない文字が含まれています: {title}")
    return title


def _build_sheets(wb, funcs):
    """
    テンプレートの機能シートを、機能の数だけのシートにし、見出しと目次を書く。
    戻り値: 機能シート名のリスト（funcs と同じ順）
    """
    template = wb[TEMPLATE_SHEET]
    titles = [_sheet_title(i, f) for i, f in enumerate(funcs, start=1)]
    if len(set(titles)) != len(titles):
        raise ValueError("機能IDと機能名が同じ機能が重複しています。")
    for t in titles:
        if t in wb.sheetnames:
            raise ValueError(f"同じ名前のシートが既にあります: {t}")

    toc = wb[TOC_SHEET]
    if TOC_FIRST_ROW + TOC_ROW_STEP * (len(funcs) - 1) > TOC_LAST_ROW:
        raise ValueError("目次に書ける機能の数を超えています。")

    sheets = []
    for i, (func, title) in enumerate(zip(funcs, titles)):
        if i == 0:
            ws = template
        else:
            # 複製（セルの構造・結合・列幅は複製されるが、表示設定・フッターは複製されないので写す）
            ws = wb.copy_worksheet(template)
            ws.sheet_view.view = template.sheet_view.view
            ws.sheet_view.showGridLines = template.sheet_view.showGridLines
            ws.sheet_view.zoomScaleNormal = template.sheet_view.zoomScaleNormal
            ws.sheet_view.zoomScaleSheetLayoutView = (
                template.sheet_view.zoomScaleSheetLayoutView
            )
            ws.oddFooter = copy(template.oddFooter)
            ws.print_title_rows = "1:4"
        ws.title = title
        ws["B5"] = title
        sheets.append(title)

        # 目次に機能名を書く（書式は1件目の行から写す）
        row = TOC_FIRST_ROW + TOC_ROW_STEP * i
        cell = toc.cell(row=row, column=TOC_COL)
        if i > 0:
            src = toc.cell(row=TOC_FIRST_ROW, column=TOC_COL)
            cell.font = copy(src.font)
            cell.alignment = copy(src.alignment)
            cell.border = copy(src.border)
            cell.number_format = src.number_format
        cell.value = title

    # 複製したシートは末尾に並ぶので、1件目の直後に、順番どおりに並べ直す
    base = wb.sheetnames.index(sheets[0])
    for offset, name in enumerate(sheets):
        current = wb.sheetnames.index(name)
        wb.move_sheet(name, offset=(base + offset) - current)
    return sheets


def build_screen_flow(xlsx_path, spec, output_path, dot_exe, font, dot_out=None):
    """
    画面遷移図を組み立てて出力する。
    引数: xlsx_path=元（テンプレート）、spec=JSON の内容、output_path=出力、dot_exe=dot のパス、
          font=フォント名、dot_out=dot ソースを別ファイルでも残すフォルダ（省略可）
    戻り値: 結果の dict（sheets の一覧と、警告のリスト）
    """
    funcs = _normalize_functions(spec)
    for i, f in enumerate(funcs):
        _validate_function(f, i)

    warnings = []
    tmp_dir = tempfile.mkdtemp(prefix="screen_flow_")
    try:
        # 入力のテンプレートの機能シートから、凡例の drawing を取り出す
        with zipfile.ZipFile(xlsx_path) as z:
            sheet_map = _sheet_name_to_target(z)
            if TEMPLATE_SHEET not in sheet_map:
                raise ValueError(
                    f"シート『{TEMPLATE_SHEET}』が見つかりません。"
                    "元のテンプレートから実行してください。"
                )
            legend_path = _find_drawing_for_sheet(z, sheet_map[TEMPLATE_SHEET])
            if legend_path is None:
                raise ValueError(
                    f"シート『{TEMPLATE_SHEET}』に凡例の図形がありません。"
                    "元のテンプレートから実行してください。"
                )
            legend_xml = z.read(legend_path).decode("utf-8")
        legend_top0, legend_bottom0 = _legend_rows(legend_xml)

        # 凡例をずらすときの、1行の高さ（EMU。1pt=12700EMU）
        # シートを作り、見出し・目次を書く
        wb = openpyxl.load_workbook(xlsx_path)
        row_emu = int(float(wb[TEMPLATE_SHEET].sheet_format.defaultRowHeight or 15) * 12700)
        sheets = _build_sheets(wb, funcs)

        jobs = []
        for func, title in zip(funcs, sheets):
            ws = wb[title]
            dot_source = build_dot(func, font)
            png = os.path.join(tmp_dir, f"flow_{len(jobs)}.png")
            render_png(dot_source, png, dot_exe)

            anchor = func.get("anchor", DEFAULT_IMAGE_ANCHOR)
            layout = compute_layout(ws, anchor, png, legend_top0)
            if layout["scale"] < MIN_READABLE_SCALE:
                warnings.append(
                    f"『{title}』: 図を幅に収めるため {layout['scale']:.0%} に縮小しました。"
                    "文字が読みにくいときは、rankdir を TB にするか、機能を分けてください。"
                )

            # dot ソースを余白のセルに残す
            src_col_letter, src_row = coordinate_from_string(
                func.get("source_anchor", DEFAULT_SOURCE_ANCHOR)
            )
            src_col = column_index_from_string(src_col_letter)
            ws.cell(row=src_row, column=src_col, value="【dotソース】")
            for k, line in enumerate(dot_source.splitlines(), start=1):
                ws.cell(row=src_row + k, column=src_col, value=line)

            # 印刷範囲は、凡例の下端（ずらした後）までにする
            ws.print_area = f"A1:AI{legend_bottom0 + layout['shift_rows'] + 2}"
            # 凡例を大きくずらしたときは、凡例が改ページで分断されないよう、凡例の直前で改ページする
            if layout["shift_rows"] > MAX_SHIFT_WITHOUT_BREAK:
                ws.row_breaks.append(Break(id=legend_top0 + layout["shift_rows"]))

            if dot_out:
                os.makedirs(dot_out, exist_ok=True)
                safe = re.sub(r'[\\/:*?"<>|]', "_", title)
                with open(
                    os.path.join(dot_out, f"{safe}.dot"),
                    "w",
                    encoding="utf-8",
                    newline="\n",
                ) as f:
                    f.write(dot_source)

            jobs.append(
                {
                    "sheet": title,
                    "png": png,
                    "anchor": anchor,
                    "width_emu": layout["width_emu"],
                    "height_emu": layout["height_emu"],
                    "shift_rows": layout["shift_rows"],
                }
            )

        # 1. openpyxl で保存（図形は消える）→ 表紙などの既存の図形を復元
        stage1 = os.path.join(tmp_dir, "stage1.xlsx")
        stage2 = os.path.join(tmp_dir, "stage2.xlsx")
        wb.save(stage1)
        restore_shapes(xlsx_path, stage1, stage2)

        # 2. 機能シートに、凡例＋画像の drawing を結びつける
        attach_flow_drawings(stage2, output_path, legend_xml, jobs, row_emu)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return {"sheets": sheets, "warnings": warnings, "jobs": jobs}


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("xlsx_path")
    parser.add_argument("json_path")
    parser.add_argument("output_path")
    parser.add_argument(
        "--dot", default=None, help="dot の実行ファイルのパス（既定は PATH から探す）"
    )
    parser.add_argument(
        "--font", default=DEFAULT_FONT, help=f"図中のフォント名（既定 {DEFAULT_FONT}）"
    )
    parser.add_argument(
        "--dot-out", default=None, help="dot ソースを別ファイルでも残すフォルダ"
    )
    args = parser.parse_args()

    dot_exe = args.dot or shutil.which("dot")
    if not dot_exe:
        print(
            "エラー: Graphviz の dot が見つかりません。PATH に通すか --dot で指定してください。"
        )
        sys.exit(1)
    try:
        with open(args.json_path, encoding="utf-8") as f:
            spec = json.load(f)
        result = build_screen_flow(
            args.xlsx_path, spec, args.output_path, dot_exe, args.font, args.dot_out
        )
    except (ValueError, RuntimeError, json.JSONDecodeError) as e:
        print(f"エラー: {e}")
        sys.exit(1)

    print(f"=== 画面遷移図の組み立て結果: {args.output_path} ===")
    for job in result["jobs"]:
        w = job["width_emu"] // EMU_PER_PIXEL
        h = job["height_emu"] // EMU_PER_PIXEL
        print(
            f"シート『{job['sheet']}』: 画像 {w}x{h}px（{job['anchor']} から）、凡例を {job['shift_rows']} 行ずらしました。"
        )
    for w in result["warnings"]:
        print(f"【注意】{w}")
    print(
        "次に、警告の確認と、export_sheet_preview.py での見た目の確認を行ってください（この出力は verify_layout.py の対象外です）。"
    )


if __name__ == "__main__":
    main()
