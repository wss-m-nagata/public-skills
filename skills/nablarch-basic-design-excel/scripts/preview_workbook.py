# -*- coding: utf-8 -*-
"""
Excel の全シートを、画像（PNG）にして、見た目を確認できるようにする。

export_sheet_preview.py は、1シートを PDF にする。
このスクリプトは、それをシートごとに行い、PDF を PNG にして、画像のパスを一覧にする。
出力した PNG を、Read ツールで開いて、折り返し・はみ出し・行の高さ・重なりを確かめる。

【前提・制約】
- Windows に Microsoft Excel と pywin32 が入っていること（export_sheet_preview.py と同じ）。
- PDF を PNG にするには、PyMuPDF（`pip install pymupdf`。import 名は fitz）か、pdftoppm（poppler）が要る。
  どちらも無いときは、PDF のパスだけを出す。
- 元のファイルは、読み取り専用で開き、保存しない。

使い方:
    python preview_workbook.py <xlsx> <出力フォルダ> [--sheet-prefix <前方一致> ...] [--skip <シート名> ...] [--dpi <解像度>]

    --sheet-prefix : 対象のシート名の前方一致。複数指定できる。省略時は、skip 以外のすべてのシート。
    --skip         : 対象から外すシート名。省略時は「データ」（プルダウンの選択肢だけのシート）。
    --dpi          : PNG の解像度。省略時は 90。細かい文字を見たいときは、110 など。

    出力：<出力フォルダ>/<番号>_<シート名>.pdf と、<番号>_<シート名>_<ページ>.png（ページは0から）。
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).parent))
from export_sheet_preview import export_sheet_to_pdf  # noqa: E402
from xlsx_common import ensure_utf8_stdio  # noqa: E402

DEFAULT_SKIP = ("データ",)


def _safe_name(name):
    """シート名を、ファイル名に使える文字にする。

    Args:
        name (str): シート名。

    Returns:
        str: ファイル名に使える文字列。
    """
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_")


def _pdf_to_png(pdf, dpi):
    """PDF を PNG にする（ページごとに1枚）。

    Args:
        pdf (Path): PDF のパス。
        dpi (int): 解像度。

    Returns:
        list[Path]: できた PNG のパス。PNG にできないときは、空のリスト。
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None

    if fitz is not None:
        pngs = []
        with fitz.open(pdf) as doc:
            for index, page in enumerate(doc):
                png = pdf.with_name(f"{pdf.stem}_{index}.png")
                page.get_pixmap(dpi=dpi).save(png)
                pngs.append(png)
        return pngs

    if shutil.which("pdftoppm"):
        prefix = pdf.with_name(pdf.stem)
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(prefix)], check=True
        )
        return sorted(pdf.parent.glob(f"{pdf.stem}-*.png"))
    return []


def preview(xlsx, out_dir, sheet_prefixes=(), skip=DEFAULT_SKIP, dpi=90):
    """全シート（または対象のシート）を、PDF と PNG にする。

    Args:
        xlsx (str): xlsx のパス。
        out_dir (str): 出力フォルダ。
        sheet_prefixes (tuple[str, ...]): 対象のシート名の前方一致。空なら、skip 以外のすべて。
        skip (tuple[str, ...]): 対象から外すシート名。
        dpi (int): PNG の解像度。

    Returns:
        list[tuple[str, Path, list[Path]]]: （シート名, PDF, PNG のリスト）。
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    names = openpyxl.load_workbook(xlsx, read_only=True).sheetnames
    targets = [
        n
        for n in names
        if n not in skip
        and (not sheet_prefixes or any(n.startswith(p) for p in sheet_prefixes))
    ]
    results = []
    for index, name in enumerate(targets):
        pdf = out / f"{index:02d}_{_safe_name(name)}.pdf"
        export_sheet_to_pdf(xlsx, name, str(pdf))
        results.append((name, pdf, _pdf_to_png(pdf, dpi)))
    return results


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("xlsx")
    parser.add_argument("out_dir")
    parser.add_argument("--sheet-prefix", action="append", default=[])
    parser.add_argument("--skip", action="append")
    parser.add_argument("--dpi", type=int, default=90)
    args = parser.parse_args()

    try:
        results = preview(
            args.xlsx,
            args.out_dir,
            tuple(args.sheet_prefix),
            tuple(args.skip) if args.skip else DEFAULT_SKIP,
            args.dpi,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as error:
        print(f"NG: {error}")
        sys.exit(1)

    print(f"OK: {len(results)} シートを書き出しました: {args.out_dir}")
    for name, pdf, pngs in results:
        if pngs:
            for png in pngs:
                print(f"  [{name}] {png}")
        else:
            print(
                f"  [{name}] {pdf}（PNG にできませんでした。PyMuPDF か pdftoppm を入れてください）"
            )


if __name__ == "__main__":
    main()
