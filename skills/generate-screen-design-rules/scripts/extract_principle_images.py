"""画面設計原則のExcelから、指定した原則・比較例のOK/NG画像を取り出す。

使い方:
    python extract_principle_images.py <表示番号> [--example N] [--out 出力先] [--xlsx Excelのパス]

例:
    python extract_principle_images.py 2-8                 # 2-8 のすべての比較例の画像
    python extract_principle_images.py 1-3 --example 2     # 1-3 の比較例②だけ
    python extract_principle_images.py A-1 --out ./images

出力するファイル名: <表示番号>_ex<比較例の番号>_<ng|ok>_s<画面の順番>.png
  例: 1-3_ex1_ng_s2.png（1-3 の比較例①、NG例の2画面目）
画面の名前（「① 社員一覧」など）は、references/design-principles/principles.json の
ng_screens・ok_screens に、画面の順番どおりに入っている。

標準ライブラリだけで動く（ExcelはZIPなので、描画の位置情報から、画像と原則を対応づける）。
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
COL_NG, COL_OK = 4, 6  # E列、G列（0始まり）。NG例・OK例の画像の列
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
DEFAULT_XLSX = Path(__file__).resolve().parent.parent / "references" / "design-principles" / "業務Webアプリ_画面設計原則.xlsx"


def join(base, target):
    """OPCの相対パス（../drawings/x.xml など）を、ZIP内のパスにする。"""
    if target.startswith("/"):
        return target.lstrip("/")
    parts = base.split("/")[:-1]
    for p in target.split("/"):
        if p == "..":
            parts.pop()
        elif p != ".":
            parts.append(p)
    return "/".join(parts)


def rels(z, path):
    """path の .rels を読み、{Id: 解決後のパス} を返す。"""
    rel_path = path.rsplit("/", 1)[0] + "/_rels/" + path.rsplit("/", 1)[1] + ".rels"
    if rel_path not in z.namelist():
        return {}
    root = ET.fromstring(z.read(rel_path))
    return {r.get("Id"): join(path, r.get("Target")) for r in root.findall("rel:Relationship", NS)}


def shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]


def sheet_cells(z, sheet_path, sst):
    """B列・C列のセルの文字列を、{(行, 列の文字): 文字列} で返す。"""
    cells = {}
    root = ET.fromstring(z.read(sheet_path))
    for c in root.iter(f"{{{NS['m']}}}c"):
        ref = c.get("r")
        col = re.match(r"[A-Z]+", ref).group()
        if col not in ("B", "C"):
            continue
        row = int(ref[len(col):])
        if c.get("t") == "s":
            v = c.find("m:v", NS)
            text = sst[int(v.text)] if v is not None else ""
        elif c.get("t") == "inlineStr":
            text = "".join(t.text or "" for t in c.iter(f"{{{NS['m']}}}t"))
        else:
            continue
        cells[(row, col)] = text
    return cells


def drawing_images(z, sheet_path):
    """シートの描画から、[(行(1始まり), 列(0始まり), 画像のZIP内パス)] を返す。"""
    root = ET.fromstring(z.read(sheet_path))
    d = root.find("m:drawing", NS)
    if d is None:
        return []
    drawing_path = rels(z, sheet_path)[d.get(f"{{{NS['r']}}}id")]
    image_rels = rels(z, drawing_path)
    out = []
    for anchor in ET.fromstring(z.read(drawing_path)):
        frm = anchor.find("xdr:from", NS)
        blip = anchor.find(".//a:blip", NS)
        if frm is None or blip is None:
            continue
        row = int(frm.find("xdr:row", NS).text) + 1
        col = int(frm.find("xdr:col", NS).text)
        out.append((row, col, image_rels[blip.get(f"{{{NS['r']}}}embed")]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("label", help="原則の表示番号（例：2-8、A-1）")
    ap.add_argument("--example", type=int, help="比較例の番号（①なら1）。省略時はすべて")
    ap.add_argument("--out", default="principle-images", help="出力先のフォルダー（既定：./principle-images）")
    ap.add_argument("--xlsx", default=str(DEFAULT_XLSX), help="Excelのパス（既定：同梱のExcel）")
    args = ap.parse_args()

    xlsx = Path(args.xlsx)
    if not xlsx.exists():
        sys.exit(f"Excelが見つからない: {xlsx}")
    with zipfile.ZipFile(xlsx) as z:
        sst = shared_strings(z)
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        wb_rels = rels(z, "xl/workbook.xml")
        found = None
        for s in wb.find("m:sheets", NS):
            path = wb_rels[s.get(f"{{{NS['r']}}}id")]
            cells = sheet_cells(z, path, sst)
            heads = sorted(r for (r, c), v in cells.items() if c == "B" and r > 4 and re.match(r"^[0-9A]+-?\d*　", v))
            for i, r in enumerate(heads):
                if cells[(r, "B")].startswith(args.label + "　"):
                    found = (path, cells, r, heads[i + 1] if i + 1 < len(heads) else 10**9)
        if not found:
            sys.exit(f"原則が見つからない: {args.label}（表示番号は、2-8 や A-1 の形）")
        path, cells, start, end = found
        print(f"{cells[(start, 'B')]}")

        bands = sorted((r, CIRCLED.index(v[len("■ 比較例")]) + 1) for (r, c), v in cells.items()
                       if c == "C" and start < r < end and v.startswith("■ 比較例") and v[len("■ 比較例"):][:1] in CIRCLED)
        images = sorted((r, col, p) for r, col, p in drawing_images(z, path) if start < r < end and col in (COL_NG, COL_OK))
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        steps = {}  # (比較例, 側) -> 画面の順番
        count = 0
        for r, col, media in images:
            ex = max((n for br, n in bands if br <= r), default=None)
            if ex is None or (args.example and ex != args.example):
                continue
            side = "ng" if col == COL_NG else "ok"
            steps[(ex, side)] = steps.get((ex, side), 0) + 1
            name = f"{args.label}_ex{ex}_{side}_s{steps[(ex, side)]}{Path(media).suffix}"
            (out_dir / name).write_bytes(z.read(media))
            print("  " + name)
            count += 1
        print(f"{count}枚を {out_dir.resolve()} に書き出した")
        if count == 0:
            sys.exit("画像がない（比較例の番号を確認する）")


if __name__ == "__main__":
    main()
