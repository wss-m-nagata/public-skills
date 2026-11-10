# -*- coding: utf-8 -*-
"""
Nablarch開発標準の画面系テンプレート（原本）から、このスキルの `assets/templates/フォーマット/` を作る。

【なぜ作り直すのか】
原本の「表紙」は、プロジェクト名・成果物名・サブシステム名を、テキストボックス（図形）で描いている。
図形は、openpyxl で保存すると消え、値も入れられない。
そこで、表紙の主要情報をセルベースのレイアウトに作り直す。
レイアウトは、バックエンド用スキル（nablarch-basic-design-excel）の `フォーマット/` の表紙と同じにする（J12・J14・J16・J19・J28・J30）。

【やること】
1. 原本から、表題のテキストボックス（「[プロジェクト名]…[サブシステム名]」を含むもの）だけを取り除いた「図形の元」を作る。
   「関係者外秘」「PJ関係者限り」の図形は残す。
2. 原本の「表紙」シートの内容を消し、見本（バックエンド用テンプレートの表紙）の内容に置き換える。
   成果物名（J14）は、ファイル名から取る。
3. openpyxl で保存し、図形の元から図形を戻す（restore_shapes.py）。

画面遷移図の「図形」（箱・矢印）は、本体のシートにある。
本体のシートの図形も、restore_shapes.py が戻すため、この処理で消えない。

使い方:
    python build_formats.py <原本のフォルダ> <出力フォルダ> <見本のテンプレート(表紙)> <見本の単体テスト仕様書(表紙)>

例:
    python build_formats.py assets/templates/原本 assets/templates/フォーマット \\
        ../nablarch-basic-design-excel/assets/templates/フォーマット/テーブル一覧.xlsx \\
        "../nablarch-basic-design-excel/assets/templates/フォーマット/単体テスト仕様書(Webサービス)_(取引ID)_(取引名).xlsx"
"""

import re
import shutil
import sys
import tempfile
import warnings
import zipfile
from copy import copy
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from restore_shapes import restore_shapes  # noqa: E402
from xlsx_common import ensure_utf8_stdio  # noqa: E402

warnings.filterwarnings("ignore")

TITLE_BOX_KEYWORD = "プロジェクト名"


def make_shape_source(original: Path, out: Path) -> int:
    """表題のテキストボックスだけを取り除いた xlsx を作る。取り除いた図形の数を返す。"""
    removed = 0
    with zipfile.ZipFile(original) as zin, zipfile.ZipFile(
        out, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.fullmatch(r"xl/drawings/drawing\d+\.xml", item.filename):
                text = data.decode("utf-8")

                # アンカー（<xdr:twoCellAnchor> / <xdr:oneCellAnchor> / <xdr:absoluteAnchor>）単位で、表題の図形を取り除く
                def drop(m):
                    nonlocal removed
                    block = m.group(0)
                    runs = "".join(re.findall(r"<a:t>(.*?)</a:t>", block))
                    if TITLE_BOX_KEYWORD in runs and "<xdr:sp" in block:
                        removed += 1
                        return ""
                    return block

                text = re.sub(
                    r"<xdr:(twoCellAnchor|oneCellAnchor|absoluteAnchor)\b.*?</xdr:\1>",
                    drop,
                    text,
                    flags=re.S,
                )
                data = text.encode("utf-8")
            zout.writestr(item, data)
    return removed


def copy_cover(src_ws, dst_ws, product_name: str, name_cell: str) -> None:
    """見本の表紙の内容（値・書式・結合・行高・列幅）を、対象の表紙に写す。"""
    # 1. 対象の表紙を空にする
    for rng in list(dst_ws.merged_cells.ranges):
        dst_ws.unmerge_cells(str(rng))
    for row in dst_ws.iter_rows():
        for c in row:
            c.value = None
            c.style = "Normal"
    # 2. 列幅・行高
    (
        dst_ws.column_dimensions.clear()
        if hasattr(dst_ws.column_dimensions, "clear")
        else None
    )
    for key, dim in src_ws.column_dimensions.items():
        dst_ws.column_dimensions[key].width = dim.width
        dst_ws.column_dimensions[key].hidden = dim.hidden
    for key, dim in src_ws.row_dimensions.items():
        dst_ws.row_dimensions[key].height = dim.height
    # 3. セルの値と書式
    for row in src_ws.iter_rows():
        for c in row:
            d = dst_ws.cell(row=c.row, column=c.column)
            d.value = c.value
            if c.has_style:
                d.font = copy(c.font)
                d.fill = copy(c.fill)
                d.border = copy(c.border)
                d.alignment = copy(c.alignment)
                d.number_format = c.number_format
                d.protection = copy(c.protection)
    # 4. 結合
    for rng in src_ws.merged_cells.ranges:
        dst_ws.merge_cells(str(rng))
    # 5. 成果物名
    dst_ws[name_cell].value = product_name
    dst_ws.sheet_view.showGridLines = src_ws.sheet_view.showGridLines
    if src_ws.print_area:
        dst_ws.print_area = src_ws.print_area


def product_name_of(path: Path) -> str:
    """ファイル名から成果物名を取る（例：画面一覧_(サブシステムID)_… → 画面一覧）。"""
    stem = path.stem
    return re.split(r"_\(|_サンプル", stem)[0]


def main():
    ensure_utf8_stdio()
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    src_dir, out_dir, sample_cover, sample_ut_cover = map(Path, sys.argv[1:5])
    out_dir.mkdir(parents=True, exist_ok=True)
    cover_wb = openpyxl.load_workbook(sample_cover)
    ut_wb = openpyxl.load_workbook(sample_ut_cover)
    for original in sorted(src_dir.glob("*.xlsx")):
        is_ut = original.name.startswith("単体テスト仕様書")
        sample_ws = (ut_wb if is_ut else cover_wb)["表紙"]
        name_cell = "J14"
        if is_ut:
            # 単体テスト仕様書の表紙は、見本（バックエンド用）の成果物名のセルを使う
            name_cell = next(
                (
                    c.coordinate
                    for r in sample_ws.iter_rows()
                    for c in r
                    if isinstance(c.value, str)
                    and c.value.startswith("単体テスト仕様書")
                ),
                "J14",
            )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shape_src = tmp / "shape_source.xlsx"
            removed = make_shape_source(original, shape_src)
            wb = openpyxl.load_workbook(original)
            copy_cover(sample_ws, wb["表紙"], product_name_of(original), name_cell)
            saved = tmp / "saved.xlsx"
            wb.save(saved)
            out = out_dir / original.name
            restore_shapes(str(shape_src), str(saved), str(out))
        print(f"作成: {original.name}（表題の図形を {removed} 個、取り除いた）")


if __name__ == "__main__":
    main()
