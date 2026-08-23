# -*- coding: utf-8 -*-
"""
指定したシートをPDFとして書き出し、実際の見栄え(レイアウト崩れ・図形の重なり・
長文セルの折り返し等)を目視確認できるようにするスクリプト。

verify_layout.py・extract_structure.pyは結合セル・入力規則等の「構造」は検証できるが、
実際にExcelで開いたときの見た目（Mermaidフロー図が既存の図形と重なっていないか、
長文が列幅内でどう折り返されるか等）までは分からない。このスクリプトはExcelを実際に
起動して(COM経由)PDF化することで、この「見た目」を確認する手段を提供する。

【前提・制約】
- Windows環境に**Microsoft Excelがインストール済み**であることが必須(`pywin32`経由でExcelを
  COM操作する)。Excelが無い環境（Mac/Linuxのローカル実行、Excel未インストールのWindows）では
  使用できない。使えるかどうかは`python -c "import win32com.client; win32com.client.Dispatch('Excel.Application')"`
  がエラーにならないかで確認できる。
- 元ファイルは**読み取り専用で開き、保存せずに閉じる**ため、一切変更しない。
- 出力したPDFは、Claude Codeの`Read`ツールで直接読んで視覚的に確認できる
  (画像と同様にレンダリングされる)ほか、ユーザーがPDFビューアで開いて確認することもできる。

使い方:
    python export_sheet_preview.py <元xlsxパス> <シート名> <出力PDFパス> [印刷範囲(例: A1:AH60)]

印刷範囲を省略した場合は、そのシートの既定の印刷範囲（無ければシート全体）で出力する。
既定の印刷範囲が無い巨大なシートでは、意図せず数十ページに渡るPDFになることがあるため、
`get_bordered_bbox`等で確認した罫線範囲を印刷範囲として明示的に指定することを推奨する。

例(Mermaidフロー図を挿入した後、既存の凡例と重なっていないか確認する場合):
    python export_sheet_preview.py システム機能設計書.xlsx "1.3. バッチ処理フロー" preview.pdf A1:BA70
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio

try:
    import win32com.client as win32
except ImportError:
    win32 = None

# 0 = Excel定数のxlTypePDF
XL_TYPE_PDF = 0
# 2 = xlLandscape(横向き)。フロー図・幅広の表は横向きの方が1ページに収まりやすい。
XL_LANDSCAPE = 2


def export_sheet_to_pdf(xlsx_path, sheet_name, pdf_path, cell_range=None, fit_wide=True):
    if win32 is None:
        raise RuntimeError(
            "pywin32(win32com)がインストールされていません。"
            "`pip install pywin32`でインストールしてください。"
            "またこのスクリプトはWindows+Excelインストール済み環境でのみ動作します。"
        )

    xlsx_path = os.path.abspath(xlsx_path)
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {xlsx_path}")

    try:
        excel = win32.DispatchEx("Excel.Application")
    except Exception as e:
        raise RuntimeError(
            f"Excelを起動できませんでした(この環境にExcelがインストールされていない可能性があります): {e}"
        )

    excel.Visible = False
    excel.DisplayAlerts = False
    wb = excel.Workbooks.Open(xlsx_path, ReadOnly=True, UpdateLinks=0)
    try:
        if sheet_name not in [s.Name for s in wb.Worksheets]:
            raise ValueError(f"シートが存在しません: {sheet_name}")
        ws = wb.Worksheets(sheet_name)
        if cell_range:
            ws.PageSetup.PrintArea = cell_range
        if fit_wide:
            ws.PageSetup.Zoom = False
            ws.PageSetup.FitToPagesWide = 1
            ws.PageSetup.FitToPagesTall = False
        ws.PageSetup.Orientation = XL_LANDSCAPE
        ws.ExportAsFixedFormat(XL_TYPE_PDF, pdf_path)
    finally:
        wb.Close(SaveChanges=False)
        excel.Quit()

    return pdf_path


def main():
    ensure_utf8_stdio()
    if len(sys.argv) not in (4, 5):
        print(__doc__)
        sys.exit(2)

    xlsx_path, sheet_name, pdf_path = sys.argv[1:4]
    cell_range = sys.argv[4] if len(sys.argv) == 5 else None

    result = export_sheet_to_pdf(xlsx_path, sheet_name, pdf_path, cell_range)
    print(f"=== PDF出力結果: {result} ===")
    print("このPDFをReadツールで開くか、ユーザーに開いてもらって、見栄え(重なり・折り返し・")
    print("はみ出し等)を確認すること。構造上の差分はverify_layout.pyでは検出できないため、")
    print("Mermaidフロー図の挿入後や、長文セルを多数記入した後は、このスクリプトでの")
    print("目視確認を必ず行うこと。")


if __name__ == "__main__":
    main()
