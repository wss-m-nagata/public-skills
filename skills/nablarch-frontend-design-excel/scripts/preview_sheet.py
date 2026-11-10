# -*- coding: utf-8 -*-
"""
指定したシートを、Excel で PDF にし、ページごとの PNG にする（見た目の確認用）。

export_sheet_preview.py（シートを PDF にする）と、PyMuPDF（PDF を PNG にする）を、続けて行う。
PNG は、Read ツールで開いて、目で確かめる。

使い方:
    python preview_sheet.py <xlsx> <出力フォルダ> <シート名> [<シート名> ...] [--dpi 80]

例:
    python preview_sheet.py 出力.xlsx prev "表紙" "2. ORD0101(受注一覧画面)" --dpi 90

出力:
    出力フォルダに、`p<シートの順番2桁>_<ページ>.png` を作る（日本語を避けた名前。順番とシート名の対応は、標準出力に出す）。

前提:
    Windows、Excel、pywin32、PyMuPDF（import fitz）が入っていること。
    シートの印刷範囲が設定済みのテンプレートでは、印刷範囲の指定は要らない。
    画面遷移図・システム機能設計書(画面)のように、ページをまたぐシートは、ページごとに PNG になる。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from export_sheet_preview import export_sheet_to_pdf  # noqa: E402
from xlsx_common import ensure_utf8_stdio  # noqa: E402


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("xlsx")
    parser.add_argument("out_dir")
    parser.add_argument("sheets", nargs="+")
    parser.add_argument("--dpi", type=int, default=80)
    args = parser.parse_args()

    try:
        import fitz  # PyMuPDF
    except ImportError:
        print(
            "PyMuPDF（import fitz）が入っていません。`pip install pymupdf` で入れてください。"
        )
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, sheet in enumerate(args.sheets, start=1):
        pdf = out_dir / f"p{n:02d}.pdf"
        export_sheet_to_pdf(args.xlsx, sheet, str(pdf))
        doc = fitz.open(pdf)
        names = []
        for k, page in enumerate(doc, start=1):
            png = out_dir / f"p{n:02d}_{k}.png"
            page.get_pixmap(dpi=args.dpi).save(png)
            names.append(str(png))
        doc.close()
        print(f"[{n:02d}] {sheet}（{len(names)}ページ）")
        for name in names:
            print(f"     {name}")


if __name__ == "__main__":
    main()
