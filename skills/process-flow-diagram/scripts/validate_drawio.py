"""生成した .drawio を機械的に検査する。

図の崩れは、drawio で開いて初めて気づくことが多い。開かずに分かる不具合
（図形の重なり、線のつなぎ先が消えている、ページからのはみ出し、文字が箱に入りきらない）
はここで潰しておく。
残るのは「線の経路が読みにくい」といった目で見ないと分からないものだけになるので、
preview_drawio.py での目視確認が短く済む。

使い方:
    python validate_drawio.py 処理フロー_xxx.drawio

終了コードは、問題があれば 1、なければ 0。

改版履歴
2026/09/04: 圧縮形式の .drawio を検出して止めるようにした。
  その形式では mxGraphModel が現れず、図形0件・線0件のまま全検査を通過して
  「問題は見つかりませんでした」と誤って報告していた。終了コードは 2 とする
  （問題ありの 1 と区別するため）。
2026/09/04: 文字が箱に入りきっているかの検査を足した（検査6）。
  注記や T.B.D の本文が枠からあふれる崩れは目視でしか気づけず、直すたびに
  高さの数値を当て直していたため。判定は drawio_builder.estimate_height を使う。
  - 凡例のページと、枠線も塗りも無いテキストは対象外にした。
    見本の図形は寸法をそろえて並べており、少しのあふれを崩れとは呼べないため。
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio_builder import (  # noqa: E402
    DrawioFormatError,
    assert_expanded_drawio,
    estimate_height,
)


def _font_size(style):
    """スタイル文字列から文字の大きさを取り出す。指定が無ければ drawio の既定値。"""
    m = re.search(r"fontSize=(\d+)", style or "")
    return int(m.group(1)) if m else 12


def classify(style):
    """スタイル文字列から図形の役割を推定する。

    drawio の XML には役割の情報が残らないため、スタイルから逆算する。
    枠（frame）は中に図形を置くのが正しい使い方なので、重なり検査から外す必要がある。
    """
    if "shape=mxgraph.aws4.group" in style:
        return "frame"
    if "shape=cylinder3" in style or "shape=note" in style:
        return "table"
    if "resIcon=" in style or "aws4.user" in style:
        return "icon"
    if style.startswith("text;"):
        return "text"
    # テーブル群やステップ群を囲む枠。ラベルを左上に置く指定を目印にする
    if "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4" in style:
        return "frame"
    if "fillColor=none" in style:
        return "frame"
    return "solid"


def validate(path):
    problems = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return ["XML として壊れている: %s" % e]

    # 圧縮形式は mxGraphModel が現れず、以降の検査がすべて0件になって「問題なし」と
    # 誤って通る。黙って通すより止める（例外は呼び出し側が受けて終了コード2で終わる）
    assert_expanded_drawio(path, tree.getroot())

    for diagram in tree.getroot().findall("diagram"):
        name = diagram.get("name")
        cells = diagram.findall(".//mxCell")
        ids = {c.get("id") for c in cells}

        shapes, edges = [], []
        for c in cells:
            g = c.find("mxGeometry")
            if c.get("vertex") == "1" and g is not None:
                shapes.append(
                    (
                        c.get("id"),
                        c.get("value") or "",
                        classify(c.get("style") or ""),
                        float(g.get("x", 0)),
                        float(g.get("y", 0)),
                        float(g.get("width", 0)),
                        float(g.get("height", 0)),
                        c.get("style") or "",
                    )
                )
            if c.get("edge") == "1":
                edges.append(c)

        # 1) 線のつなぎ先が実在するか。図形を消したときに線だけ残ると drawio 上で浮く
        for e in edges:
            for key in ("source", "target"):
                ref = e.get(key)
                if ref and ref not in ids:
                    problems.append(
                        "%s: 線 %s の %s=%s が存在しない"
                        % (name, e.get("id"), key, ref)
                    )

        # 2) 実体の図形どうしが重なっていないか。枠と中身の入れ子は正しい配置なので除く
        solids = [
            s for s in shapes if s[2] in ("solid", "table", "icon", "screen", "lambda")
        ]
        for i in range(len(solids)):
            for j in range(i + 1, len(solids)):
                a, b = solids[i], solids[j]
                ox = min(a[3] + a[5], b[3] + b[5]) - max(a[3], b[3])
                oy = min(a[4] + a[6], b[4] + b[6]) - max(a[4], b[4])
                if ox > 2 and oy > 2:
                    problems.append(
                        "%s: 図形が重なる 「%s」×「%s」" % (name, _label(a), _label(b))
                    )

        # 3) 注記・吹き出しが他の図形へかぶっていないか。文字が読めなくなる
        notes = [s for s in shapes if s[2] == "solid"]
        others = [
            s for s in shapes if s[2] in ("table", "screen", "lambda", "icon", "text")
        ]
        for a in notes:
            for b in others:
                if a[0] == b[0]:
                    continue
                ox = min(a[3] + a[5], b[3] + b[5]) - max(a[3], b[3])
                oy = min(a[4] + a[6], b[4] + b[6]) - max(a[4], b[4])
                if ox > 2 and oy > 2:
                    problems.append(
                        "%s: 注記が図形へかぶる 「%s」×「%s」"
                        % (name, _label(a), _label(b))
                    )

        # 4) ページからはみ出していないか。印刷・画像化で切れる
        model = diagram.find("mxGraphModel")
        pw = float(model.get("pageWidth", 0))
        ph = float(model.get("pageHeight", 0))
        for s in shapes:
            if pw and s[3] + s[5] > pw:
                problems.append(
                    "%s: 「%s」がページ幅を超える（右端 %.0f > %.0f）"
                    % (name, _label(s), s[3] + s[5], pw)
                )
            if ph and s[4] + s[6] > ph:
                problems.append(
                    "%s: 「%s」がページ高さを超える（下端 %.0f > %.0f）"
                    % (name, _label(s), s[4] + s[6], ph)
                )

        # 5) 枠が中身を収めきれているか。枠からテーブルがはみ出ると意味が読めない
        frames = [s for s in shapes if s[2] == "frame" and s[5] < 1500]
        inner = [s for s in shapes if s[2] in ("table", "screen", "lambda")]
        for f in frames:
            # 枠の x 範囲に収まり、かつ y が枠の上下に収まっているものだけを中身とみなす。
            # 下端を見ないと、真下の段に置いた別の図形まで「この枠の中身」と誤判定する。
            contained = [
                s
                for s in inner
                if s[3] >= f[3] - 2
                and s[3] + s[5] <= f[3] + f[5] + 2
                and s[4] >= f[4] - 2
                and s[4] < f[4] + f[6]
            ]
            for s in contained:
                if s[4] + s[6] > f[4] + f[6] + 2:
                    problems.append(
                        "%s: 「%s」が枠「%s」の下へはみ出す"
                        % (name, _label(s), _label(f))
                    )

        # 6) 文字が箱に入りきっているか。あふれると枠の外へ文字だけが流れ出る。
        #    枠線も塗りも無いテキストは、はみ出しても見た目が崩れないので対象外。
        #    凡例のページも対象外。見本の図形は寸法をそろえて並べており、
        #    ラベルが少しあふれても崩れとは言えないため。
        if "凡例" not in (name or ""):
            for s in shapes:
                if s[2] != "solid":
                    continue
                style = s[7]
                font = _font_size(style)
                # 上寄せの箱は spacingTop の分だけ余白が要る。中央寄せは上下に分かれる
                pad = 20 if "verticalAlign=top" in style else 10
                need = estimate_height(s[1], s[5], font, pad)
                if need > s[6] + 8:
                    problems.append(
                        "%s: 文字が箱に入りきらない 「%s」（高さ %.0f → %d 必要）"
                        % (name, _label(s), s[6], need)
                    )

        print("%s: 図形 %d / 線 %d" % (name, len(shapes), len(edges)))

    # 重複した指摘は1回にまとめる
    seen, unique = set(), []
    for p in problems:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _label(shape):
    text = re.sub(r"<[^>]+>", " ", shape[1] or "").strip()
    return text[:28] or shape[0]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python validate_drawio.py <path.drawio>")
        sys.exit(2)
    try:
        issues = validate(sys.argv[1])
    except DrawioFormatError as e:
        print(e)
        sys.exit(2)
    if issues:
        print()
        for i in issues:
            print("[要修正] " + i)
        print("\n%d 件の問題があります。" % len(issues))
        sys.exit(1)
    print("\n問題は見つかりませんでした。")
    sys.exit(0)
