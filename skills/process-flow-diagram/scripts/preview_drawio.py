"""生成した .drawio をブラウザで描画して目視確認するためのプレビューを作る。

drawio がインストールされていない環境でも、diagrams.net の閲覧用スクリプトを読み込めば
同じ見た目で描画できる。線の経路やラベルの重なりは検査スクリプトでは拾いきれないため、
出す前に一度は目で見ておく。

使い方:
    # HTML を作るだけ（生成先を表示する）
    python preview_drawio.py 処理フロー_xxx.drawio

    # 作ったうえでローカルサーバを起動する（Ctrl+C で終了）
    python preview_drawio.py 処理フロー_xxx.drawio --serve

    # 特定のページだけを見る
    python preview_drawio.py 処理フロー_xxx.drawio --page ①新規作成・編集

ネットワークが使えない環境では描画できない（閲覧用スクリプトを取得するため）。
その場合は drawio デスクトップで開いて確認する。
"""

import argparse
import html
import io
import json
import os
import tempfile
import xml.etree.ElementTree as ET

VIEWER = "https://viewer.diagrams.net/js/viewer-static.min.js"

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>%(title)s</title>
<style>
  body { margin: 0; padding: 12px; background: #fff; font-family: sans-serif; }
  h2 { font-size: 13px; color: #607d8b; margin: 16px 0 6px; }
</style>
</head>
<body>
%(body)s
<script src="%(viewer)s"></script>
</body>
</html>
"""


def build(path, page=None):
    """各ページを1つずつ描画する HTML を組み立てて、その中身を返す。"""
    tree = ET.parse(path)
    blocks = []
    for diagram in tree.getroot().findall("diagram"):
        name = diagram.get("name")
        if page and name != page:
            continue
        single = ET.Element("mxfile", {"host": "app.diagrams.net"})
        single.append(diagram)
        config = json.dumps(
            {
                "highlight": "#0000ff",
                "nav": False,
                "toolbar": "",
                "resize": True,
                "xml": ET.tostring(single, encoding="unicode"),
            },
            ensure_ascii=False,
        )
        blocks.append(
            '<h2>%s</h2>\n<div class="mxgraph" data-mxgraph="%s"></div>'
            % (html.escape(name), html.escape(config, quote=True))
        )
    if not blocks:
        raise SystemExit("該当するページがありません: %s" % page)
    return TEMPLATE % {
        "title": os.path.basename(path),
        "body": "\n".join(blocks),
        "viewer": VIEWER,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drawio")
    ap.add_argument("--page", help="このページだけを描画する")
    ap.add_argument("--out", help="HTML の出力先（既定は一時ディレクトリ）")
    ap.add_argument("--serve", action="store_true", help="ローカルサーバを起動する")
    ap.add_argument("--port", type=int, default=8931)
    args = ap.parse_args()

    content = build(args.drawio, args.page)
    out = args.out or os.path.join(tempfile.gettempdir(), "drawio_preview.html")
    io.open(out, "w", encoding="utf-8", newline="\n").write(content)
    print("HTML を作成しました: %s" % out)

    if args.serve:
        import functools
        import http.server
        import socketserver

        directory = os.path.dirname(os.path.abspath(out))
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=directory
        )
        with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
            print("http://127.0.0.1:%d/%s" % (args.port, os.path.basename(out)))
            print("Ctrl+C で終了します。")
            httpd.serve_forever()


if __name__ == "__main__":
    main()
