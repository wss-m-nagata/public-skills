# -*- coding: utf-8 -*-
"""
外部インタフェース設計書(JSON)を、電文の定義ファイル(JSON)から組み立てるスクリプト。

このテンプレートは他の様式と違い、座標の計算を間違えやすい。
- 『【レコード名】』シートはテンプレート原本の状態では3ブロック構成で、1ブロックのデータ行は
  7行しかない。項目数が7を超えると行の挿入が要り、挿入すると下のブロックとデータ構成サンプルの
  行がずれる。4ブロック目以降(records4件目以降)が必要な場合は、ブロック3(ヘッダ行を持たない
  中間ブロック)のパターンをBLOCK_SPACING間隔で複製し、ブロックそのものを新設する
  (3ブロックという数はテンプレート原本がそう配布されているだけで、記入要領等に上限の明記は
  無いため)。
- 選択欄はチェックボックスではなくセル文字列(□/☑)であり、書き換える位置が決まっている。

これらを毎回マッピングJSONへ手で起こすと間違えるため、本スクリプトへ寄せる。

使い方:
    python build_external_if_json.py <テンプレートxlsx> <電文定義json> <出力xlsx>

電文定義JSONの形式:
{
  "msg_id": "EV0101R",                         # 電文ID。ファイル名・U8に入る
  "msg_name": "評価依頼受付（回答評価）要求",   # 電文名。表紙・目次・変更履歴に入る
  "io": "入力",                                 # 入力 / 出力
  "peer": "アンケート実施サブシステム",          # 相手先
  "tx": "EV0101／評価依頼受付（回答評価）",      # 入出力取引ID/名称
  "purpose": "…",                              # 目的・概要
  "condition": "…",                            # 作成条件
  "cycle": "随時",                              # 日次/週次/月次/年次/随時/その他
  "cycle_detail": "回答が確定した都度",
  "transfer": "Lambda Invoke（同期）",          # 授受方式
  "charset": "UTF-8",
  "encrypted": "無し",                          # 無し / 有り
  "remarks": ["なし。"],                        # 特記事項。1要素=1行(E28から連番セルへ)。
                                                #   意味のまとまり(句点等)で呼び出し側が分割する。
                                                #   最大4行(E28:E31の罫線内)。文字列1個でも可（後方互換）。
  "header": {"pj": "…", "system": "…", "author": "…", "date": 46279,
             "company": "…", "dept": "…"},      # date はExcelのシリアル値
  "records": [                                  # 先頭がルートレコード。4件目以降は新設ブロックとして対応
    {"name": "評価依頼", "rec_id": "-", "rec_type": "単一",
     "items": [
       {"name": "スタッフ識別子", "id": "staffNo", "type": "半角英数字",
        "size": "7", "required": "○", "multi": "1",
        "note": "", "sample": "\\"1000123\\"",
        "changed": true}                        # 省略可(既定false)。trueにすると
                                                  #   その項目行(No.〜備考)の文字色を赤にする。
                                                  #   新設計へのレビュー時に変更箇所を
                                                  #   一目で分かるようにするためのフラグであり、
                                                  #   電文の意味には影響しない。
     ]}
  ]
}

記入の決まりは `記入要領_外部インタフェース設計書_JSON.md` を参照。特に次の2点を守る。
- 構成イメージはレコードが2件以上のときだけ書く。書く場所はレコードを定義する『3.1.〜』シート。
- 該当しない欄は空欄にせず「-」を書く。まだ決まっていない欄は「T.B.D（後ほど記載）」と書き分ける。

例(空テンプレートに、電文定義ファイルEV0101R.jsonの内容を反映する場合):
    python build_external_if_json.py "外部インタフェース設計書_(電文ID)_(電文名)_(JSON).xlsx" EV0101R.json 出力.xlsx
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from apply_mapping import apply_mapping  # noqa: E402
from insert_rows import insert_rows_keep_layout  # noqa: E402
from xlsx_common import (  # noqa: E402
    save_with_shapes,
    ensure_utf8_stdio,
    get_merge_anchor,
)

TEMPLATE_RECORD_SHEET = "【レコード名】"
SPEC_SHEET = "1. 外部インタフェース仕様"
STRUCT_SHEET = "2. レコード構成"

# 『【レコード名】』のブロック（レコード名行, レコードID行, データ先頭行）と1ブロックの行数。
# テンプレート原本(Nablarch開発標準の公式配布物)には3ブロック分の罫線・結合セル・入力規則しか
# 用意されていないが、これはテンプレートが「そう配布されている」という事実であって、
# 記入要領等のどこにも「4ブロック目を作ってはいけない」とは書かれていない。
# 3ブロックという上限は、以前の本スクリプトの実装(BLOCKSのリスト長)がそう決めていただけの
# 制約だったため、4ブロック目以降はBLOCK_SPACING間隔でブロック3(ヘッダ行を持たない中間ブロック)
# のパターンを複製して新設できるようにした(block_base参照)。
BLOCKS_BASE = [(7, 8, 10), (18, 19, 20), (28, 29, 30)]
BLOCK_ROWS = 7
# 新設ブロック1つが実際に消費する行数(レコード名行+レコードID行+データ7行。間隔行は挿入しない)。
# prepare()が新設時に挿入する行数(1+1+BLOCK_ROWS)と必ず一致させること。ここがズレると
# データ構成サンプル欄の位置が、新設ブロックの実際の物理シフト量とスクリプト内部の計算上の
# シフト量とで食い違う(実際に1ブロック分ズレて検証した際に発覚した不具合)。
BLOCK_SPACING = 2 + BLOCK_ROWS


def block_base(i):
    """i番目(0始まり)のブロックの、そのブロック自身のneeds(7行超の追加分)を考慮しない
    基準位置(name_row, id_row, data_row)を返す。

    テンプレートに実在するのはBLOCKS_BASEの3ブロックのみ。4ブロック目以降は、
    ヘッダ行を持たない中間ブロック(ブロック2・3のパターン)をBLOCK_SPACING間隔で
    外挿して新設する(prepareで実際に行・書式を複製する)。
    """
    if i < len(BLOCKS_BASE):
        return BLOCKS_BASE[i]
    last_name, last_id, last_data = BLOCKS_BASE[-1]
    shift = (i - (len(BLOCKS_BASE) - 1)) * BLOCK_SPACING
    return (last_name + shift, last_id + shift, last_data + shift)


# 『1. 外部インタフェース仕様』シートの特記事項欄。E28を先頭に、罫線がE31までしか無いため最大4行
REMARKS_MAX_LINES = 4
SAMPLE_LABEL_ROW = 39  # データ構成サンプル／データ構成イメージの見出し行
IMAGE_COL = "Y"  # データ構成イメージ欄の左端の列

STRUCT_FIRST_ROW = 9
# 『2. レコード構成』の列（結合セルの左上）
STRUCT_COLS = {
    "name": "B",
    "rec_type": "G",
    "identify": "J",
    "length": "Q",
    "repeat": "S",
    "unit": "V",
    "sort_key": "AD",
    "sort_order": "AH",
}
# 『【レコード名】』の列
ITEM_COLS = {
    "no": "A",
    "name": "B",
    "id": "G",
    "domain": "L",
    "required": "Q",
    "type": "R",
    "size": "V",
    "multi": "X",
    "default": "Z",
    "format": "AB",
    "note": "AE",
}
# 選択欄（□を☑へ書き換える位置）
IO_CELL = {"入力": "E7", "出力": "I7"}
ENCRYPT_CELL = {"無し": "E22", "有り": "E23"}
CYCLE_CELL = {
    "日次": ("E25", "H25"),
    "週次": ("R25", "U25"),
    "月次": ("E26", "H26"),
    "年次": ("R26", "U26"),
    "随時": ("E27", "H27"),
    "その他": ("R27", "U27"),
}

# 該当しない欄の表し方。記入要領がJSON電文の長さを「-」としており、様式全体でこれに揃える。
# 「未定」は T.B.D と書き分ける。
NA = "-"


def layout(records):
    """項目数から、行を広げたあとの各ブロックの位置と、全体のずれ幅を求める。"""
    needs = [max(0, len(r["items"]) - BLOCK_ROWS) for r in records]
    blocks, offset = [], 0
    for i in range(len(records)):
        name_row, id_row, data_row = block_base(i)
        blocks.append((name_row + offset, id_row + offset, data_row + offset))
        offset += needs[i]
    # データ構成サンプル欄など、ブロック群より後ろにある内容のずれ幅。
    # 3ブロック以内ならneeds分のoffsetだけで済む(未使用ブロックは行を消さずクリアするだけのため、
    # サンプル欄の基準位置は動かない)。4ブロック目以降を新設した場合は、その分の基本行数
    # (BLOCK_SPACING、block_baseが決める新設ブロック同士の間隔と同じ)も加える。
    extra_blocks = max(0, len(records) - len(BLOCKS_BASE))
    total = offset + extra_blocks * BLOCK_SPACING
    return blocks, needs, total


def record_tree(records):
    """レコード間の入れ子関係。(深さ, 表示文字列) の並びで返す。"""
    out = [(0, records[0]["name"])]
    for rec in records[1:]:
        out.append(
            (1, "└ %s（%s：%s）" % (rec["name"], rec["rec_id"], rec["rec_type"]))
        )
    return out


def json_sample(records):
    """実データの例。配列は1要素だけ書く。各項目の sample を使う。

    子レコードは rec_id で親の項目IDと結び付く。rec_type が「繰り返し」なら配列、
    「単一」ならオブジェクトとして展開する。孫レコード(子のさらに子)も再帰的に解決するため、
    root→rows→rank のような多段のネストも表現できる。
    """
    by_rec_id = {r["rec_id"]: r for r in records[1:]}

    def value(it):
        if it.get("sample"):
            return it["sample"]
        if it["type"] == "真偽値":
            return "true"
        if it["type"] in ("符号無数値", "符号付数値"):
            return "0"
        return '"..."'

    def render_items(items, indent):
        pad = "  " * indent
        lines = []
        for n, it in enumerate(items):
            tail = "," if n < len(items) - 1 else ""
            child = by_rec_id.get(it["id"])
            if child is None:
                lines.append('%s"%s": %s%s' % (pad, it["id"], value(it), tail))
                continue
            if child["rec_type"] == "繰り返し":
                lines.append('%s"%s": [' % (pad, it["id"]))
                lines.append("%s  {" % pad)
                lines.extend(render_items(child["items"], indent + 2))
                lines.append("%s  }" % pad)
                lines.append("%s]%s" % (pad, tail))
            else:
                lines.append('%s"%s": {' % (pad, it["id"]))
                lines.extend(render_items(child["items"], indent + 1))
                lines.append("%s}%s" % (pad, tail))
        return lines

    lines = ["{"]
    lines.extend(render_items(records[0]["items"], 1))
    lines.append("}")
    return lines


def prepare(template, out_path, sheet_name, records):
    """シート名を変え、ブロックを広げる/新設し、使わないブロックを空にする。"""
    from insert_rows import clear_rows

    wb = openpyxl.load_workbook(template)
    wb[TEMPLATE_RECORD_SHEET].title = sheet_name
    ws = wb[sheet_name]

    _, needs, total = layout(records)
    n_physical = len(BLOCKS_BASE)
    # テンプレートに実在しない4ブロック目以降を新設する際の書式見本。
    # ヘッダ行を持たない中間ブロック(ブロック3。BLOCKS_BASEの最後)のパターンを複製する。
    tmpl_name_row, tmpl_id_row, tmpl_data_row = BLOCKS_BASE[-1]

    # 下のブロックから処理する。先に上のブロックを広げる/新設すると下の行位置がずれるため。
    # ここで使う行番号は、まだ何も挿入していない「元の(拡張前の)」位置であることに注意。
    # 下から処理するため、i番目を処理する時点で i より上は誰も触っていない。
    for i in range(len(records) - 1, -1, -1):
        name_row, id_row, data_row = block_base(i)
        if i >= n_physical:
            # 4ブロック目以降はテンプレートに物理的に存在しないため、ブロックそのものを新設する
            # (レコード名行→レコードID行→データ行の順に、隣接する行番号へ1件ずつ挿入する)。
            # insert_rows_keep_layoutは書式(_style)だけを複製し、A列の見出し文字列
            # 「レコード名」「レコードID」はテンプレート実在ブロックの静的な値なので複製されない。
            # そのため見出し文字列は別途明示的に書き込む。
            insert_rows_keep_layout(ws, name_row, 1, tmpl_name_row)
            ws.cell(row=name_row, column=1).value = "レコード名"
            insert_rows_keep_layout(ws, id_row, 1, tmpl_id_row)
            ws.cell(row=id_row, column=1).value = "レコードID"
            insert_rows_keep_layout(ws, data_row, BLOCK_ROWS + needs[i], tmpl_data_row)
        elif needs[i] > 0:
            # 既存ブロックの項目数が7件を超える場合、データ行を広げる
            insert_rows_keep_layout(ws, data_row + BLOCK_ROWS, needs[i], data_row)

    if len(records) < n_physical:
        start = BLOCKS_BASE[len(records)][0] + total
        end = BLOCKS_BASE[-1][2] + BLOCK_ROWS - 1 + total
        clear_rows(ws, range(start, end + 1))

    save_with_shapes(wb, template, out_path)


def build_mapping(d, sheet_name):
    records = d["records"]
    blocks, _, total = layout(records)
    h = d["header"]

    spec = {
        IO_CELL[d["io"]]: "☑" + d["io"],
        "U7": d["peer"],
        "E8": d["tx"],
        "U8": d["msg_id"],
        "E9": d["purpose"],
        "E14": d["condition"],
        "E21": d["transfer"],
        ENCRYPT_CELL[d["encrypted"]]: "☑" + d["encrypted"],
        "E24": d["charset"],
    }
    cyc_cell, cyc_detail = CYCLE_CELL[d["cycle"]]
    spec[cyc_cell] = "☑" + d["cycle"]
    spec[cyc_detail] = d["cycle_detail"]

    # 特記事項(E28)は、テンプレートの罫線がE28〜E31の4行分しか無い。
    # 文字列(従来形式)ならE28の1行、配列(1要素=1行)ならE28から連番セルへ展開する。
    # 意味のまとまり(句点等)での分割は呼び出し側(電文定義JSON)の責務とし、
    # ここでは機械的な文字列処理(句点split等)を行わない。
    remarks = d["remarks"]
    if isinstance(remarks, str):
        remarks = [remarks]
    if len(remarks) > REMARKS_MAX_LINES:
        raise ValueError(
            "remarksは最大%d行までです（テンプレートのE28:E%dの罫線内）。"
            "現在%d行あります。電文定義JSON側で行数を減らしてください。"
            % (REMARKS_MAX_LINES, 27 + REMARKS_MAX_LINES, len(remarks))
        )
    for i, line in enumerate(remarks):
        spec["E%d" % (28 + i)] = line

    # レコード構成はルートレコード1行だけ。該当しない欄は「-」で表す
    root = records[0]
    struct_vals = {
        "name": root["name"],
        "rec_type": root["rec_type"],
        "identify": root.get("identify") or NA,
        # JSON電文では長さ（Byte）を使わない（記入要領）
        "length": NA,
        "repeat": root.get("repeat") or NA,
        "unit": root.get("unit") or NA,
        "sort_key": root.get("sort_key") or NA,
        "sort_order": root.get("sort_order") or NA,
    }
    struct = {
        "%s%d" % (STRUCT_COLS[k], STRUCT_FIRST_ROW): v for k, v in struct_vals.items()
    }

    cells = {"A5": sheet_name}
    for i, rec in enumerate(records):
        name_row, id_row, data_row = blocks[i]
        cells["D%d" % name_row] = rec["name"]
        cells["D%d" % id_row] = rec["rec_id"]
        for j, it in enumerate(rec["items"]):
            r = data_row + j
            vals = {
                "no": j + 1,
                "name": it["name"],
                "id": it["id"],
                # ドメイン定義書が無い場合は項目名をそのまま使う
                "domain": it.get("domain") or it["name"],
                "required": it["required"],
                "type": it["type"],
                "size": it.get("size", ""),
                "multi": it.get("multi", "1"),
            }
            for k, v in vals.items():
                if v != "":
                    cells["%s%d" % (ITEM_COLS[k], r)] = v
            if it.get("note"):
                cells["%s%d" % (ITEM_COLS["note"], r)] = it["note"]

    # データ構成サンプルは必ず書く。1行につき1セル（セル内改行は表示されないため）
    first = SAMPLE_LABEL_ROW + total + 1
    for k, line in enumerate(json_sample(records)):
        cells["A%d" % (first + k)] = line
    # 構成イメージはレコードが2件以上のときだけ。階層は列をずらして表す
    if len(records) > 1:
        for k, (depth, text) in enumerate(record_tree(records)):
            cells["%s%d" % (chr(ord(IMAGE_COL) + depth), first + k)] = text

    return {
        "sheets": {
            "変更履歴": {
                "E1": h["pj"],
                "E2": h["system"],
                "E3": d["msg_name"],
                "A8": 1,
                "B8": "第1.0版",
                "D8": h["date"],
                "G8": "新規",
                "J8": "-",
                "Q8": "新規作成",
                "AF8": h["author"],
            },
            "表紙": {
                "J12": h["pj"],
                "J16": d["msg_name"],
                "J28": h["company"],
                "J30": h["dept"],
            },
            "目次": {"B7": "1. " + d["msg_name"]},
            SPEC_SHEET: spec,
            STRUCT_SHEET: struct,
            sheet_name: cells,
        }
    }


def collect_red_cells(d, sheet_name):
    """ "changed": true の項目行について、書き込み済みセルの座標一覧を返す。"""
    records = d["records"]
    blocks, _, _ = layout(records)
    red = []
    for i, rec in enumerate(records):
        _, _, data_row = blocks[i]
        for j, it in enumerate(rec["items"]):
            if not it.get("changed"):
                continue
            r = data_row + j
            for col in ITEM_COLS.values():
                red.append("%s%d" % (col, r))
    return red


def mark_changed_red(path, out_path, red_cells_by_sheet):
    """
    指定セルの文字色だけを赤(FF0000)にする。
    apply_mapping.pyは値のみを書き換える方針(フォント等の書式は一切変更しない)だが、
    レビュー時に変更箇所を一目で分かるようにするため、本スクリプトに限りこの用途の
    赤字マーキングだけを例外的に許可する。文字色以外のフォント属性(フォント名・サイズ・
    太字等)は元のまま維持する。
    """
    wb = openpyxl.load_workbook(path)
    for sheet_name, coords in red_cells_by_sheet.items():
        ws = wb[sheet_name]
        for coordinate in coords:
            anchor = get_merge_anchor(ws, coordinate)
            cell = ws[anchor]
            if cell.value in (None, ""):
                continue
            f = cell.font
            cell.font = openpyxl.styles.Font(
                name=f.name,
                size=f.size,
                bold=f.bold,
                italic=f.italic,
                vertAlign=f.vertAlign,
                underline=f.underline,
                strike=f.strike,
                color="FFFF0000",
            )
    save_with_shapes(wb, path, out_path)


def ungray_struct_row(path, out_path):
    """レコード構成で記入した行のグレーアウト（記入不要の表現）を解除する。"""
    from openpyxl.styles import PatternFill
    from openpyxl.utils import column_index_from_string

    wb = openpyxl.load_workbook(path)
    ws = wb[STRUCT_SHEET]
    for c in range(column_index_from_string("B"), column_index_from_string("AI") + 1):
        ws.cell(row=STRUCT_FIRST_ROW, column=c).fill = PatternFill(fill_type=None)
    save_with_shapes(wb, path, out_path)


# テンプレート側の仕様上、罫線設定範囲(bbox)の外にあるが正当な書き込み先のセル。
# 表紙のJ28(会社名)・J30(部門名)、目次のB7(電文名見出し)は、他のテンプレートと違い
# bboxの外側に配置された静的テキストセルであり、SKILL.mdの「ローカル実行の手順」にも
# 同様の記載がある(表紙のJ12・J16・J28・J30は数式ではなく別途セル指定が必要)。
# これ以外の座標をここに追加してはいけない -- 追加するとJSON定義や座標計算の誤りを
# 見逃すようになる(allow_outside_borderを全体へ一律適用していたことによる過検出漏れ)。
OUTSIDE_BORDER_EXCEPTIONS = {
    "表紙": {"J28", "J30"},
    "目次": {"B7"},
}


def _split_mapping_by_bbox_exception(mapping):
    """mappingを、bboxの外への書き込みを許可してよいセルとそれ以外に分ける。"""
    strict_sheets = {}
    loose_sheets = {}
    for sheet_name, cell_map in mapping.get("sheets", {}).items():
        exceptions = OUTSIDE_BORDER_EXCEPTIONS.get(sheet_name, set())
        strict_cells = {k: v for k, v in cell_map.items() if k not in exceptions}
        loose_cells = {k: v for k, v in cell_map.items() if k in exceptions}
        if strict_cells:
            strict_sheets[sheet_name] = strict_cells
        if loose_cells:
            loose_sheets[sheet_name] = loose_cells
    return {"sheets": strict_sheets}, {"sheets": loose_sheets}


def build(template, definition_path, output):
    d = json.load(open(definition_path, encoding="utf-8"))
    records = d["records"]

    sheet_name = "3.1. %s" % records[0]["name"]
    work = output + ".work.xlsx"
    prepare(template, work, sheet_name, records)

    mapping = build_mapping(d, sheet_name)
    strict_mapping, loose_mapping = _split_mapping_by_bbox_exception(mapping)

    # 1回目: OUTSIDE_BORDER_EXCEPTIONS以外は罫線設定範囲を厳格に検証する
    # (JSON定義や座標計算の誤りで範囲外へ書こうとした場合はここでエラーになる)。
    tmp1 = output + ".tmp1.xlsx"
    report = apply_mapping(work, strict_mapping, tmp1, allow_outside_border=False)
    if report["errors"]:
        for e in report["errors"]:
            print("ERROR:", e)
        raise SystemExit(1)

    # 2回目: 既知の正当な例外セルのみ、罫線設定範囲の外への書き込みを許可する。
    tmp = output + ".tmp.xlsx"
    report2 = apply_mapping(tmp1, loose_mapping, tmp, allow_outside_border=True)
    if report2["errors"]:
        for e in report2["errors"]:
            print("ERROR:", e)
        raise SystemExit(1)
    report["warnings"].extend(report2["warnings"])
    report["written"].extend(report2["written"])

    red_cells = collect_red_cells(d, sheet_name)
    if red_cells:
        tmp2 = output + ".tmp2.xlsx"
        ungray_struct_row(tmp, tmp2)
        mark_changed_red(tmp2, output, {sheet_name: red_cells})
        os.remove(tmp2)
    else:
        ungray_struct_row(tmp, output)

    for p in (work, tmp1, tmp):
        if os.path.exists(p):
            os.remove(p)
    return output


def main():
    ensure_utf8_stdio()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("template")
    ap.add_argument("definition")
    ap.add_argument("output")
    a = ap.parse_args()
    print("created:", build(a.template, a.definition, a.output))


if __name__ == "__main__":
    main()
