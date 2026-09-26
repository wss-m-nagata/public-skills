"""処理フロー図（.drawio）を組み立てるためのライブラリ。

改版履歴
2026/09/02: 1ページ内の段分けと戻り線の扱いを見直した。
  - 段を分ける見出し `Page.section()` を追加した。枠（group）で段を分けると、
    範囲を示す囲み（aws_frame / tables / scope_out）と区別がつかなくなるため。
  - `Page.back()` の使いどころを「戻る値がその先の流れを決めるときだけ」に改めた。
    自明な戻り線を省き、残した線を強調として機能させるためである。
2026/09/03: 凡例の画面の見本から「別チームが作成する場合は注記する」を外した。
  処理フロー図は誰が作るかを割り当てる図ではなく、役割分担は対象外であるため
  （ユーザー判断）。あわせて、描き手への指示を凡例に置かない方針とした。
  処理の「何をするかを1〜2行で書く」は、読み手が中身を思い描く助けになるので残す。
2026/09/03: 書き出し前の照合と書き出し後の記録を入れた（`Diagram.save()`）。
  人が drawio で直した図に生成スクリプトを流すと手直しが消えるため、既定で止める。
  判定はハッシュ（台帳 `.drawio-baseline/`）で行う。mxfile の host 属性は
  Web版 drawio で保存されると生成スクリプトと同じ値になり、判定に使えないためである。
2026/09/03: 自己ループを `Page.self_loop()` として独立させた。
  従来は `flow()` の始点と終点に同じ図形を渡す書き方を案内していたが、
  接続位置（exitX / entryX）の指定だけでは drawio の直交ルータが経路を決めきれず、
  ループが潰れて線に見えないか、戻り脚が図形を突き抜けるかのどちらかになっていた。
  中継点（waypoint）で経路を固定する形へ改め、既定の置き場所を画面の右上とした。
  - 図形の座標を `Page.geoms` に控えるようにした。自己ループの中継点を
    呼ぶ側に計算させないためである。
  - `flow()` に始点と終点が同じ場合のガードを入れた。黙って壊れた線を出すより、
    `self_loop()` へ誘導するほうがよい。
2026/09/04: WBS を前提にした言い回しを一般化した（`scope_out()` の説明、凡例の（他機能で作る））。
  作業計画の呼び方や有無はプロジェクトごとに違い、WBS が無い現場では成り立たないため。
  あわせて、範囲外の枠を使ってよい場面を3つに限る旨を `scope_out()` の説明に書いた。
2026/09/08: 凡例の語彙から「（他機能で作る）」を外した（`legend_page()`）。
  「別の機能の作成対象」は誰が作るかの割り当てに読めるためである（ユーザー判断）。
  あわせて「どの機能・どのチームが作るのかは書かない」旨を凡例に明記した。
2026/09/04: 凡例の「この図の範囲」の高さを本文から決めるようにした（`legend_page()`）。
  620x145 の固定だったため、範囲の説明が長い図では文字が枠から出ていた。
  凡例ページは文字あふれの検査（検査6）の対象外なので、検査でも気づけなかった。
  - T.B.D の見本の置き場所も、範囲の欄の下端に合わせて下げるようにした。
2026/09/09: 凡例の「画面の段階」で、見出しと本文が重なっていたのを直した（`legend_page()`）。
  本文の y が見出しより 5px 上（395）に置かれていたため、1行目が見出しに重なっていた。
  隣の「この図の範囲」と同じ 425 にそろえた。凡例ページの図形はテキスト扱いのため、
  重なり検査では気づけなかった。
2026/09/04: 圧縮形式の .drawio を検出する `assert_expanded_drawio()` を足した。
  圧縮形式では mxGraphModel が現れず、セルが0件になるため、検査は「問題なし」、
  差分は「変更なし」と誤って通っていた。黙って通すより止めるほうがよい。
2026/09/04: `edge()` に中継点 `points` を足した。経路の固定は `self_loop()` だけが
  持っており、語彙で表せない線を引くには呼ぶ側で mxCell を組み立てるしかなかったため。
2026/09/04: 注記・T.B.D などの高さを本文から見積もるようにした（`estimate_height()`）。
  高さを渡さなければ自動で決まる。文字がはみ出すたびに数値を当て直す手間が
  作図の時間の大半を占めていたためで、見積もりは余る側へ寄せてある。
  文字が切れるより余白が多いほうが害が小さいという判断による。


drawio の XML を手で書くと、座標のずれ・ID の重複・エスケープ漏れで簡単に壊れる。
このライブラリは「画面」「処理」「テーブル」といった図の語彙で書けるようにして、
座標計算と ID 採番を引き受ける。使う側は要素を置いて線をつなぐことだけに集中できる。

使い方の最小例:

    from drawio_builder import Diagram

    d = Diagram()
    p = d.page("①新規作成・編集")
    p.title("① アンケート作成　新規作成の流れ（左から右へ読む）")
    p.aws_frame("AWS（本システム）", 40, 70, 2800, 900)

    actor = p.actor("システム管理者", 70, 148)
    scr = p.screen("アンケート一覧画面", 150, 140)
    lmb = p.lambda_box("下書きを1件作る", 370, 146)
    out = p.tables(["アンケート配信設定"], 430, 420, "書き込み先", kind="out")

    p.flow(actor, scr, "起動")
    p.flow(scr, lmb, "① 新規作成を押す")
    p.write(lmb, out, "② 追加")
    d.save("処理フロー_xxx.drawio")

座標の考え方は references/default_rules.md の「3段構成」に従う。
Y_SCREEN / Y_LAMBDA / Y_TABLE / Y_NOTE を目安に置けば、段がそろう。
"""

import hashlib
import io
import re
import unicodedata
import json
import os
import xml.etree.ElementTree as ET

# ---- 既定の段（3段構成）--------------------------------------------------
# 上段=画面、中段=処理、下段=テーブル、その下に補足。
# 図ごとに上書きしてよいが、そろえておくと複数ページを並べたときに読みやすい。
Y_SCREEN = 140
Y_LAMBDA = 330
Y_TABLE = 420
Y_NOTE = 760

# ---- 既定の寸法 ----------------------------------------------------------
TBL_W, TBL_H = 220, 38  # テーブル（円柱）
SCREEN_W, SCREEN_H = 170, 64  # 画面
LAMBDA_W, LAMBDA_H = 220, 52  # 処理ボックス（アイコンは別に36px）
ICON = 36

# ---- 線の色（意味を色で区別する。凡例ページと対応させること）----------------
C_FLOW = "#546E7A"  # 画面と処理のつながり
C_READ = "#1976D2"  # テーブルの読み取り
C_WRITE = "#2E7D32"  # テーブルへの書き込み
C_DEL = "#C62828"  # テーブルからの削除
C_BACK = "#8D6E63"  # 処理から画面への戻り
C_GEN = "#5E35B1"  # 世代・派生などの補助的な関係

# ---- スタイル定義 --------------------------------------------------------
S_TITLE = "text;html=1;align=left;verticalAlign=middle;fontSize=18;fontStyle=1;fontColor=#263238;"
# 本文が1行に収まる幅の目安。drawio の既定フォントで、全角は文字寸法どおり、
# 半角はおよそ 0.55 倍の幅になる。厳密な字送りは持っていないのでこの近似で足りる。
_WIDE = "WFA"


def estimate_height(html, width, font=11, pad=20):
    """本文と箱の幅から、文字が収まるのに必要な高さを見積もる。

    引数:
        html  : 箱に入れる本文。`<br>` などのタグを含んでよい。
        width : 箱の幅（px）。
        font  : 文字の大きさ（px）。スタイルの fontSize に合わせる。
        pad   : 上下の余白（px）。
    戻り値:
        必要な高さ（px）。

    drawio の折り返しを Python 側で真似ているだけなので、実際の描画とは数 px ずれる。
    文字が切れるより余白が余るほうが害が小さいため、余る側へ寄せてある。
    """
    text = re.sub(r"<br\s*/?>", "\n", html or "")
    text = re.sub(r"</(div|p|li|tr)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")

    avail = max(40, width - 24)          # 左右の余白（spacingLeft ＋ 枠線）
    lines = 0
    for para in text.split("\n"):
        run = 0.0
        for ch in para:
            run += font if unicodedata.east_asian_width(ch) in _WIDE else font * 0.55
        lines += max(1, int(run // avail) + (1 if run % avail else 0))
    return int(lines * font * 1.45 + pad)


def _auto_h(h, html, width, font=11, floor=40):
    """高さが渡されていなければ見積もる。渡されていればその値を尊重する。"""
    if h is not None:
        return h
    return max(floor, estimate_height(html, width, font))


S_HEAD = "text;html=1;align=left;verticalAlign=top;fontSize=12;fontStyle=1;fontColor=#37474F;"
S_SMALL = "text;html=1;align=left;verticalAlign=top;fontSize=10;fontColor=#78909C;"
S_TEXT = "text;html=1;align=left;verticalAlign=top;fontSize=11;fontColor=#37474F;"
S_NOTE = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFDE7;strokeColor=#FBC02D;fontColor=#5D4037;"
    "fontSize=11;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;"
)
S_CALLOUT = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF3E0;strokeColor=#FB8C00;fontColor=#5D4037;"
    "fontSize=11;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;"
)
S_TBD = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFEBEE;strokeColor=#C62828;strokeWidth=2;dashed=1;"
    "fontColor=#B71C1C;fontSize=11;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;"
)
S_SCOPE_OUT = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#9E9E9E;dashed=1;"
    "fontColor=#616161;fontSize=11;align=left;verticalAlign=middle;spacingLeft=12;"
)
S_AWS = (
    "sketch=0;outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=0;"
    "container=0;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;"
    "grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;verticalAlign=top;"
    "align=left;spacingLeft=30;fontColor=#232F3E;dashed=0;"
)
S_GROUP = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#64B5F6;dashed=1;verticalAlign=top;"
    "align=left;spacingLeft=10;spacingTop=4;fontSize=11;fontColor=#1565C0;"
)
S_SCREEN = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#1976D2;strokeWidth=2;"
    "fontColor=#0D47A1;fontSize=12;"
)
S_STEP = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#1976D2;fontColor=#0D47A1;"
    "fontSize=11;verticalAlign=middle;"
)
S_LAMBDA_ICON = (
    "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#ED7100;"
    "strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;"
    "html=1;fontSize=10;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;"
    "resIcon=mxgraph.aws4.lambda_function;"
)
S_LAMBDA_BOX = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#ED7100;fontColor=#333333;"
    "fontSize=11;align=left;spacingLeft=10;verticalAlign=middle;"
)
S_TABLE = (
    "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=7;"
    "fillColor=#FFFFFF;strokeColor=#3949AB;fontColor=#1A237E;fontSize=10;"
)
S_TABLE_OFF = (
    "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=7;"
    "fillColor=#F5F5F5;strokeColor=#BDBDBD;fontColor=#9E9E9E;fontSize=10;dashed=1;"
)
# 認証基盤・キュー・オブジェクトストレージ・外部システムなど、
# テーブルでもファイルでもない保存先。円柱と区別がつくよう角丸の箱にする。
S_STORE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#00838F;"
    "fontColor=#006064;fontSize=10;arcSize=20;"
)
S_FILE = (
    "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;size=14;"
    "fillColor=#FFFFFF;strokeColor=#00838F;fontColor=#006064;fontSize=10;"
)
S_ACTOR = (
    "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#232F3E;strokeColor=none;"
    "dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;"
    "fontStyle=0;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.user;"
)
S_BOX = (
    "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#5E35B1;fontColor=#311B92;"
    "fontSize=11;align=left;spacingLeft=10;"
)

# テーブル群を囲む枠。読み取り元＝青、書き込み先＝緑、対象外＝灰で、役割を色でも示す。
_FRAME = {
    "in": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#F3F7FB;strokeColor=#90CAF9;dashed=0;"
        "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontSize=11;fontColor=#1565C0;"
    ),
    "out": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#F1F8F2;strokeColor=#A5D6A7;dashed=0;"
        "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontSize=11;fontColor=#2E7D32;"
    ),
    "off": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#FAFAFA;strokeColor=#CFD8DC;dashed=1;"
        "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontSize=11;fontColor=#90A4AE;"
    ),
}

_EDGE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=%s;endFill=1;strokeColor=%s;"
    "fontSize=10;fontColor=%s;labelBackgroundColor=#FFFFFF;jettySize=auto;orthogonalLoop=1;"
)

# AIが書いた T.B.D に必ず添える一文。読み手が鵜呑みにしないための断り書き。
AI_NOTE = (
    '<br><br><span style="font-size:10px;">'
    "※ この T.B.D はAIの自動生成です。内容は必ずしも正しいとは限りません。"
    "重要な情報は確認するようにしてください。</span>"
)



# ---- 手直しの検知 --------------------------------------------------------
# 図は人とAIが交互に直す。生成スクリプトは図を丸ごと作り直すため、
# 人の手直しが入ったファイルへ書き出すと、それが消える。
#
# 判定はハッシュで行う。書き出した時点の内容を台帳に控えておき、次に書く前に
# 突き合わせる。mxfile の host 属性でも「どのアプリが書いたか」は分かるが、
# Web版 drawio で保存されると生成スクリプトと同じ "app.diagrams.net" になるため、
# 判定の根拠にはできない（参考情報として報告するだけにする）。
class DrawioFormatError(RuntimeError):
    """.drawio が、この道具が扱える形式ではないことを示す。"""


def assert_expanded_drawio(path, root=None):
    """.drawio が展開形式であることを確かめる。そうでなければ例外で止める。

    引数:
        path : 対象のファイルパス。メッセージに出す。
        root : すでに読み込んである場合は mxfile の要素。省略すると読み込む。
    戻り値:
        mxfile の要素。
    例外:
        DrawioFormatError: 圧縮形式、または diagram / mxGraphModel が見当たらないとき。

    drawio は既定で、`<diagram>` の中身を deflate + base64 で圧縮して保存できる。
    その形式では `<mxGraphModel>` が現れないため、セルを数える処理がすべて0件になる。
    検査は「問題は見つかりませんでした」、差分は「差分はありません」と**誤って通る**。
    黙って通すほうが害が大きいので、ここで止める。
    """
    if root is None:
        root = ET.parse(path).getroot()

    HINT = (
        "圧縮形式の .drawio は未対応のため、展開形式へ変換してから実行してください。\n"
        "変換のしかた: drawio で開き、[ファイル] > [プロパティ] の「圧縮」を外して保存し直す。\n"
        "対象: %s" % path
    )

    if root.tag != "mxfile":
        raise DrawioFormatError(
            "最上位の要素が mxfile ではない（%s）。\n%s" % (root.tag, HINT)
        )

    diagrams = root.findall("diagram")
    if not diagrams:
        raise DrawioFormatError("diagram 要素が1つも無い。\n%s" % HINT)

    for index, diagram in enumerate(diagrams, 1):
        if diagram.find("mxGraphModel") is not None:
            continue
        name = diagram.get("name") or "(名前なし)"
        packed = (diagram.text or "").strip()
        reason = (
            "中身が圧縮された1つの文字列になっている（%d文字）" % len(packed)
            if packed
            else "中身が空である"
        )
        raise DrawioFormatError(
            "%d枚目「%s」に mxGraphModel が無い。%s。\n%s" % (index, name, reason, HINT)
        )
    return root


BASELINE_DIR = ".drawio-baseline"


def _baseline_path(path):
    """台帳の置き場所。図と同じ場所の隠しディレクトリに置き、図と一緒に移動できるようにする。"""
    return os.path.join(
        os.path.dirname(os.path.abspath(path)),
        BASELINE_DIR,
        os.path.basename(path) + ".json",
    )


def _digest(path):
    """ファイルの中身のハッシュ。手直しの有無はこれで判定する。"""
    with io.open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _host_of(path):
    """mxfile の host。誰が最後に保存したかの参考にする（判定には使わない）。"""
    import re

    head = io.open(path, encoding="utf-8", errors="replace").read(300)
    m = re.search(r'<mxfile[^>]*host="([^"]*)"', head)
    return m.group(1) if m else "(不明)"


def check_untouched(path):
    """人が触っていないかを確かめ、(状態, 説明) を返す。

    状態は "clean"（前回書き出したまま）、"touched"（変わっている）、
    "unknown"（台帳が無く判定できない）のいずれか。\n"""
    if not os.path.exists(path):
        return "clean", "まだファイルが無い"
    ledger = _baseline_path(path)
    if not os.path.exists(ledger):
        return "unknown", "台帳が無い（host=%s）" % _host_of(path)
    with io.open(ledger, encoding="utf-8") as handle:
        rec = json.load(handle)
    if rec.get("sha256") == _digest(path):
        return "clean", "%s の書き出しのまま" % rec.get("recorded_at", "?")
    return "touched", "%s の書き出し以降に変わっている（host=%s）" % (
        rec.get("recorded_at", "?"),
        _host_of(path),
    )


def record_baseline(path, by=None):
    """いまの内容を基準として台帳に控える。書き出した直後に呼ぶ。"""
    import datetime
    import sys as _sys

    ledger = _baseline_path(path)
    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    rec = {
        "sha256": _digest(path),
        "recorded_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "recorded_by": by or os.path.basename(_sys.argv[0] or "?"),
            "host": _host_of(path),
    }
    with io.open(ledger, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(rec, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return ledger


class Page:
    """1ページ分の図。図形を置き、線でつなぐ。"""

    def __init__(self, name):
        self.name = name
        self.cells = []
        self.seq = 0
        self.kinds = {}  # 図形IDごとの種別。線の引き方を種別で変えるために持つ
        self.geoms = {}  # 図形IDごとの (x, y, w, h)。自己ループの中継点の計算に使う

    # ---- 基本 ------------------------------------------------------------
    def _new_id(self):
        self.seq += 1
        return "n%d" % self.seq

    def node(self, value, style, x, y, w, h, kind="box", ident=None):
        """任意の図形を1つ置き、そのIDを返す。"""
        ident = ident or self._new_id()
        cell = ET.Element(
            "mxCell",
            {"id": ident, "value": value, "style": style, "vertex": "1", "parent": "1"},
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": str(int(x)),
                "y": str(int(y)),
                "width": str(int(w)),
                "height": str(int(h)),
                "as": "geometry",
            },
        )
        self.cells.append(cell)
        self.kinds[ident] = kind
        self.geoms[ident] = (int(x), int(y), int(w), int(h))
        return ident

    def edge(
        self,
        source,
        target,
        label="",
        color=C_FLOW,
        dashed=False,
        arrow="block",
        exit_xy=None,
        entry_xy=None,
        label_pos=None,
        points=None,
    ):
        """図形どうしを線でつなぐ。

        exit_xy / entry_xy は接続位置を (x, y) の割合で指定する。("1", "0.5") なら右辺の中央。
        線が他の図形を突き抜けるときは、ここを指定して経路を誘導する。
        label_pos は線上のラベル位置（-1=始点, 0=中点, 1=終点）。長い線で中点だと
        遠くの図形へラベルが重なるため、終点寄り（0.8前後）に寄せると読みやすい。
        points は経路の中継点を [(x, y), ...] で渡す。接続位置の指定だけでは
        drawio の直交ルータが経路を決めきれないときに、通る場所を固定する。
        """
        style = _EDGE % (arrow, color, color)
        if dashed:
            style += "dashed=1;"
        if exit_xy:
            style += "exitX=%s;exitY=%s;exitDx=0;exitDy=0;" % exit_xy
        if entry_xy:
            style += "entryX=%s;entryY=%s;entryDx=0;entryDy=0;" % entry_xy
        cell = ET.Element(
            "mxCell",
            {
                "id": self._new_id(),
                "value": label,
                "style": style,
                "edge": "1",
                "parent": "1",
                "source": source,
                    "target": target,
            },
        )
        attrs = {"relative": "1", "as": "geometry"}
        if label_pos is not None:
            attrs["x"] = str(label_pos)
        geo = ET.SubElement(cell, "mxGeometry", attrs)
        # 中継点。渡されたときだけ経路を固定する
        if points:
            arr = ET.SubElement(geo, "Array", {"as": "points"})
            for px, py in points:
                ET.SubElement(arr, "mxPoint", {"x": str(px), "y": str(py)})
        self.cells.append(cell)

    # ---- 図の部品 --------------------------------------------------------
    def title(self, text, x=40, y=24, w=1200, h=30):
        """図のタイトル。ページの左上に置く。"""
        return self.node(text, S_TITLE, x, y, w, h, kind="text")

    def aws_frame(self, label, x, y, w, h):
        """システム全体を囲む枠（AWSロゴ付き）。"""
        return self.node(label, S_AWS, x, y, w, h, kind="frame")

    def group(self, label, x, y, w, h):
        """ウィザードのステップ群など、いくつかの図形をまとめる枠。"""
        return self.node(label, S_GROUP, x, y, w, h, kind="frame")

    def actor(self, label, x, y):
        """利用者。図のいちばん左に置く。"""
        return self.node(label, S_ACTOR, x, y, 48, 48, kind="icon")

    def screen(self, label, x, y, w=SCREEN_W, h=SCREEN_H):
        """画面。上段に横並びで置く。"""
        return self.node(label, S_SCREEN, x, y, w, h, kind="screen")

    def step(self, no, label, x, y, w=165, h=64):
        """ウィザードの1ステップ。画面を分割して並べるときに使う。"""
        return self.node(
            "<b>%s</b><br>%s" % (no, label), S_STEP, x, y, w, h, kind="screen"
        )

    def lambda_box(self, label, x, y, w=LAMBDA_W, h=LAMBDA_H):
        """処理（Lambda）。アイコンと概要ボックスの組で置き、ボックス側のIDを返す。

        呼び出し元の画面の真下に置くと、どの画面から呼ばれた処理かが位置で分かる。
        複数の画面から呼ばれる処理は、それらの中間に置く。
        """
        self.node("", S_LAMBDA_ICON, x, y + (h - ICON) // 2, ICON, ICON, kind="icon")
        return self.node(label, S_LAMBDA_BOX, x + ICON + 6, y, w, h, kind="lambda")

    def tables(self, names, x, y, title, kind="out", cols=1):
        """テーブル群を枠付きで置き、(枠のID, 幅, 高さ) を返す。

        kind は out=書き込み先 / in=読み取り元 / off=この処理では扱わないもの。
        線は枠に対してつなぐ。個々のテーブルへ引くと本数が増えて読めなくなる。
        """
        style = _FRAME[kind]
        tbl_style = S_TABLE_OFF if kind == "off" else S_TABLE
        rows = (len(names) + cols - 1) // cols
        w = 20 + cols * (TBL_W + 16)
        h = 30 + rows * (TBL_H + 8)
        frame = self.node(title, style, x, y, w, h, kind="frame")
        for i, name in enumerate(names):
            cx = x + 12 + (i % cols) * (TBL_W + 16)
            cy = y + 26 + (i // cols) * (TBL_H + 8)
            self.node(name, tbl_style, cx, cy, TBL_W, TBL_H, kind="table")
        return frame, w, h

    def files(self, names, x, y, title, kind="out", cols=1):
        """ファイル（CSV等）を枠付きで置く。テーブルと同じ扱いで、形だけ変える。"""
        style = _FRAME[kind]
        rows = (len(names) + cols - 1) // cols
        w = 20 + cols * (TBL_W + 16)
        h = 30 + rows * (TBL_H + 8)
        frame = self.node(title, style, x, y, w, h, kind="frame")
        for i, name in enumerate(names):
            cx = x + 12 + (i % cols) * (TBL_W + 16)
            cy = y + 26 + (i // cols) * (TBL_H + 8)
            self.node(name, S_FILE, cx, cy, TBL_W, TBL_H, kind="table")
        return frame, w, h

    def stores(self, names, x, y, title, kind="out", cols=1):
        """テーブルでもファイルでもない保存先を置く。

        認証基盤（Cognito）、キュー（SQS）、オブジェクトストレージ（S3）、外部システムなど。
        DB と同じ扱いで読み書きの線を引けるが、形を変えて「DBではない」ことを示す。
        図に出すときは、凡例にも同じ形の説明があるので読み手が迷わない。
        """
        style = _FRAME[kind]
        rows = (len(names) + cols - 1) // cols
        w = 20 + cols * (TBL_W + 16)
        h = 30 + rows * (TBL_H + 8)
        frame = self.node(title, style, x, y, w, h, kind="frame")
        for i, name in enumerate(names):
            cx = x + 12 + (i % cols) * (TBL_W + 16)
            cy = y + 26 + (i // cols) * (TBL_H + 8)
            self.node(name, S_STORE, cx, cy, TBL_W, TBL_H, kind="table")
        return frame, w, h

    def note(self, title, body, x, y, w=620, h=None):
        """補足（黄色の枠）。図では表せない前提や背景を書く。

        高さ h は省略できる。省略すると本文と幅から見積もる。
        """
        self.node(title, S_HEAD, x, y, 320, 20, kind="text")
        return self.node(body, S_NOTE, x, y + 25, w, _auto_h(h, body, w), kind="note")

    def callout(self, title, body, x, y, w=620, h=None):
        """吹き出し（橙の枠）。読み手が誤解しやすい点を先回りして説明する。

        高さ h は省略できる。省略すると本文と幅から見積もる。
        """
        self.node(title, S_HEAD, x, y, 320, 20, kind="text")
        return self.node(body, S_CALLOUT, x, y + 25, w, _auto_h(h, body, w), kind="note")

    def section(self, text, x, y, w=700):
        """1ページの中を段に分ける見出し。

        枠（group）で囲んで分けるのではなく、この見出しで分ける。
        この図では囲みが「システムの範囲」「読み取り元・書き込み先」「扱わない範囲」を
        示す記号として既に使われており、段の区切りにも使うと読み手が判断できなくなる。
        見出しは `1.` `2.` の連番にする（既定ルール §2 を参照）。
        """
        return self.node(text, S_HEAD, x, y, w, 20, kind="text")

    def small(self, text, x, y, w=340, h=None):
        """図形のそばに置く小さな注釈。

        高さ h は省略できる。省略すると本文と幅から見積もる。
        """
        return self.node(text, S_SMALL, x, y, w, _auto_h(h, text, w, font=10, floor=20), kind="text")

    def text(self, text, x, y, w=420, h=None):
        """本文サイズのテキスト。凡例などに使う。

        高さ h は省略できる。省略すると本文と幅から見積もる。
        """
        return self.node(text, S_TEXT, x, y, w, _auto_h(h, text, w, floor=20), kind="text")

    def tbd(self, body, x, y, w=820, h=None, by_ai=True):
        """T.B.D（実装者に確認したい未確定事項）。

        仕様が未確定な箇所や、実装が要件を満たしていない箇所を赤い破線の枠で示す。
        by_ai=True のときは、AIの自動生成である旨の断り書きを末尾に自動で付ける。
        読み手が内容を鵜呑みにしないために必要な情報なので、既定で付く。
        
        高さ h は省略できる。省略すると本文と幅から見積もる。
        """
        value = "<b>T.B.D　実装者に確認</b><br>" + body + (AI_NOTE if by_ai else "")
        return self.node(value, S_TBD, x, y, w, _auto_h(h, value, w), kind="note")

    def scope_out(self, body, x, y, w=360, h=None):
        """この図では扱わない範囲であることを示す枠。

        流れを途中で切るときは、黙って切らずに「どこで整理するのか」を書く。
        読み手が続きを探せるようにするためで、行き先の呼び方はプロジェクトに合わせる
        （別の図の名前・工程の名前・作業計画の項目名など）。

        使ってよいのは、システムの外・前後の工程・別の図の3つへ流れが出ていくときだけ。
        実装があるものを「この機能の作成対象ではない」という理由で省いてはいけない
        （既定ルール §4）。誰が作るかは名前の後ろの（既存）（他機能で作る）で示す。
        
        高さ h は省略できる。省略すると本文と幅から見積もる。
        """
        return self.node(body, S_SCOPE_OUT, x, y, w, _auto_h(h, body, w, floor=60), kind="note")

    def gen_box(self, body, x, y, w=300, h=None):
        """世代・状態などを説明する補助ボックス。

        高さ h は省略できる。省略すると本文と幅から見積もる。
        """
        return self.node(body, S_BOX, x, y, w, _auto_h(h, body, w), kind="note")

    # ---- 線の種類（意味ごとに色と向きを固定する）----------------------------
    def flow(self, src, dst, label="", **kw):
        """画面と処理のつながり。左から右、上から下へ流す。

        始点と終点が同じ場合は `self_loop()` を使う。ここでは受け付けない。
        接続位置の指定だけでは自己ループの経路が定まらず、黙って壊れた線が出るためである。
        """
        if src == dst:
            raise ValueError(
                "自己ループは flow() ではなく self_loop() を使う。"
                "接続位置の指定だけでは経路が定まらず、ループが潰れるか図形を突き抜ける（対象: %s）"
                % src
            )
        self.edge(src, dst, label, C_FLOW, **kw)

    def self_loop(self, shape, label="", side="top", gap=44, span=(0.65, 0.9)):
        """画面の中だけで完結する操作を、その画面への自己ループで描く。

処理を呼ばずに画面の中で終わる操作（保持している一覧の絞り込みなど）に使う。
処理の箱が無いこと自体が「Backend を作らなくてよい」という情報になるため、
線を省いて文章だけで補うより、ループとして見せたほうが伝わる。

**既定は画面の右上（side="top"）である。** 3段構成では画面の下を処理へ降りる線が
必ず通り、左右は前後の画面への遷移線でふさがっているため、構造的に空いているのは
上だけである。下に置くと、その画面が呼ぶ処理への線とラベルが必ず競合する。

**中継点で経路を固定している。** 接続位置（exitX / entryX）の指定だけでは
drawio の直交ルータが経路を決めきれず、2点を近づけるとループが潰れて線に見えず、
離すと戻り脚が図形を突き抜ける。中継点を置いて初めて形が決まる。

見出し（section）とぶつからないよう、段の見出しと画面の間は 60px 以上あける。

Args:
    shape (str): 対象の画面のID。
    label (str): 線のラベル。「条件を変える → 画面内で絞る」のように
        操作と、その結果どうなるかを書く。
    side (str): "top"（既定。画面の上）または "bottom"（画面の下）。
    gap (int): 画面の辺からループまでの距離（px）。
    span (tuple): ループの出口・入口の位置。画面の幅に対する割合で、
        既定は右寄りの (0.65, 0.9)。

Returns:
    None: 線を1本足すだけで、参照するIDは無い。
"""
        # 中継点を計算するため、対象の座標を控えから引く
        if shape not in self.geoms:
            raise KeyError("この図に無い図形が指定された（対象: %s）" % shape)
        if side not in ("top", "bottom"):
            raise ValueError('side は "top" か "bottom"（指定: %r）' % side)

        x, y, w, h = self.geoms[shape]
        px1 = int(x + w * span[0])
        px2 = int(x + w * span[1])
        # 上なら辺の gap px 上、下なら gap px 下に、ループの折り返しを置く
        if side == "top":
            py = y - gap
            edge_y = "0"
        else:
            py = y + h + gap
            edge_y = "1"

        style = _EDGE % ("block", C_FLOW, C_FLOW)
        style += "exitX=%s;exitY=%s;exitDx=0;exitDy=0;" % (span[0], edge_y)
        style += "entryX=%s;entryY=%s;entryDx=0;entryDy=0;" % (span[1], edge_y)
        cell = ET.Element(
            "mxCell",
            {
                "id": self._new_id(),
                "value": label,
                "style": style,
                "edge": "1",
                "parent": "1",
                "source": shape,
                    "target": shape,
            },
        )
        geo = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        points = ET.SubElement(geo, "Array", {"as": "points"})
        for px in (px1, px2):
            ET.SubElement(points, "mxPoint", {"x": str(px), "y": str(py)})
        self.cells.append(cell)

    def back(self, src, dst, label="", **kw):
        """処理から呼び出し元の画面へ戻る線。点線にして、流れの本線と区別する。

        **戻る値がその先の流れを決めるときだけ呼ぶ。**
        処理を呼べば何かが返るのは当たり前で、「表示色を取る → 表示色を返す」のように
        処理名から戻り値が読み取れるものに線を引いても情報は増えず、本数だけが増える。
        引くのは、採番されたIDを次の処理が使う場合、値を画面遷移で次の画面へ渡す場合
        （ラベルに渡すキーを書く）、戻り先が呼び出し元とは別の画面の場合である。
        参照だけの機能では1本も残らないことがあり、それが正しい（既定ルール §3 を参照）。

        省く目的は、戻り線を情報ではなく**強調**として使うことである。
        値が次へ渡る箇所には実装の依存関係があり、作る順序・担当の分担・
        インターフェースの決めごとが発生する。図の読み手はそこを見つけたい。
        自明な戻り線まで引くと、その1本が同じ見た目の線に埋もれて見つけられなくなる。

        なお、処理の結果で画面が変わる場合も、処理から次の画面へ直接はつながない。
        遷移は画面どうしでつなぐ。直接つなぐと「処理が画面遷移している」ように読めてしまう。
        """
        kw.setdefault("dashed", True)
        self.edge(src, dst, label, C_BACK, **kw)

    def read(self, frame, lmb, label="読み取り", **kw):
        """テーブルから処理への読み取り。下から上へ、青。"""
        kw.setdefault("exit_xy", ("0.5", "0"))
        kw.setdefault("entry_xy", ("0.5", "1"))
        self.edge(frame, lmb, label, C_READ, **kw)

    def write(self, lmb, frame, label="書き込み", **kw):
        """処理からテーブルへの書き込み。上から下へ、緑。"""
        kw.setdefault("exit_xy", ("0.5", "1"))
        kw.setdefault("entry_xy", ("0.5", "0"))
        self.edge(lmb, frame, label, C_WRITE, **kw)

    def delete(self, lmb, frame, label="削除", **kw):
        """テーブルからの削除。赤。"""
        kw.setdefault("exit_xy", ("0.5", "1"))
        kw.setdefault("entry_xy", ("0.5", "0"))
        self.edge(lmb, frame, label, C_DEL, **kw)

    def cascade(self, src, dst, label="連鎖して削除される", **kw):
        """外部キーによる連鎖削除。赤の点線。"""
        kw.setdefault("dashed", True)
        self.edge(src, dst, label, C_DEL, **kw)

    def relate(self, src, dst, label="", **kw):
        """世代関係など、処理の流れではない補助的な関係。"""
        self.edge(src, dst, label, C_GEN, **kw)

    def lead(self, src, dst, **kw):
        """T.B.D などの注記が、どの図形に対するものかを示す引き出し線。

        矢印を付けないのは、処理の流れと混同させないため。
        """
        kw.setdefault("dashed", True)
        kw.setdefault("arrow", "none")
        self.edge(src, dst, "", C_DEL, **kw)


class Diagram:
    """複数ページからなる .drawio ファイル。"""

    def __init__(self, page_w=2900, page_h=1100):
        self.pages = []
        self.page_w = page_w
        self.page_h = page_h

    def page(self, name):
        p = Page(name)
        self.pages.append(p)
        return p

    def to_xml(self):
        mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "type": "device"})
        for index, page in enumerate(self.pages, 1):
            diagram = ET.SubElement(
                mxfile, "diagram", {"id": "page%d" % index, "name": page.name}
            )
            model = ET.SubElement(
                diagram,
                "mxGraphModel",
                {
                    "dx": "1400",
                    "dy": "800",
                    "grid": "0",
                    "gridSize": "10",
                    "guides": "1",
                    "tooltips": "1",
                    "connect": "1",
                    "arrows": "1",
                    "fold": "1",
                    "page": "1",
                    "pageScale": "1",
                    "pageWidth": str(self.page_w),
                    "pageHeight": str(self.page_h),
                    "math": "0",
                    "shadow": "0",
                    "background": "#FFFFFF",
                },
            )
            root = ET.SubElement(model, "root")
            ET.SubElement(root, "mxCell", {"id": "0"})
            ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
            for c in page.cells:
                root.append(c)
        ET.indent(mxfile, space="    ")
        return ET.tostring(mxfile, encoding="unicode")

    def save(self, path, force=False):
        """書き出す。人の手直しが入っていれば、上書きせずに止める。

        生成スクリプトは図を丸ごと作り直すため、drawio 側で直した内容は消える。
        貼り付けた画像のように復元できないものもあるので、既定で止める。
        意図して作り直すときだけ force=True を渡す。
        """
        state, detail = check_untouched(path)
        if state == "touched" and not force:
            raise RuntimeError(
                "%s には、前回の書き出しの後で手が入っている（%s）。\n"
                "このまま書き出すと、その手直しは消える。\n"
                "修正は .drawio を直接編集すること"
                "（SKILL.md 手順7、assets/edit_existing.py）。\n"
                "作り直すと決めた場合だけ save(path, force=True) とする。" % (path, detail)
                )
        if state == "unknown" and not force:
            raise RuntimeError(
                "%s の台帳が無く、手直しの有無を判定できない（%s）。\n"
                "生成スクリプトが書いたままだと分かっているなら、次で基準を作ってから実行する。\n"
                "    from drawio_builder import record_baseline; record_baseline(%r)\n"
                "作り直してよいなら save(path, force=True)。" % (path, detail, path)
                )
        io.open(path, "w", encoding="utf-8", newline="\n").write(self.to_xml())
        record_baseline(path)
        return path


def legend_page(diagram, schemas, tables, steps=None, scope=None, no=None):
    """凡例ページを作る。

    記号・線の色・読みかたは図をまたいで共通なので、ここで一度だけ説明する。
    和名と物理名の対応表も置いて、図の和名から実物をたどれるようにする。

    Args:
        diagram: Diagram インスタンス。
        schemas: [(和名, 物理名)] のリスト。スキーマの対応。
        tables: [(和名, 物理名)] のリスト。テーブルの対応。
        steps: [(番号, 名前)] のリスト。ウィザード等の段階があれば渡す。
        scope: この図の範囲を説明する文字列（HTML可）。
    """
    # 凡例は最後のページなので、それまでに作ったページ数から番号を決める。
    # 操作が3つなら④になる。番号を固定すると、操作の数を図の都合ではなく
    # 関数の都合で決めることになってしまう。
    if no is None:
        index = len(diagram.pages)
        no = "①②③④⑤⑥⑦⑧⑨⑩"[index] if index < 10 else "(%d)" % (index + 1)
    p = diagram.page("%s凡例・和名対応" % no)
    p.title("%s 凡例と和名の対応" % no)

    p.node("記号の意味", S_HEAD, 40, 80, 300, 20, kind="text")
    p.node("画面", S_SCREEN, 40, 110, 240, 44, kind="screen")
    p.node("", S_LAMBDA_ICON, 40, 170, ICON, ICON, kind="icon")
    p.node(
        "処理（何をするかを1〜2行で書く）",
        S_LAMBDA_BOX,
        82,
        170,
        198,
        ICON,
        kind="lambda",
    )
    p.node("テーブル", S_TABLE, 40, 222, 240, 40, kind="table")
    p.node(
        "DB以外の保存先（認証基盤・キュー・外部システム等）",
        S_STORE,
        40,
        278,
        240,
        40,
        kind="table",
    )
    p.node("この処理では扱わないテーブル", S_TABLE_OFF, 40, 334, 240, 40, kind="table")

    p.node("読みかた", S_HEAD, 340, 80, 300, 20, kind="text")
    p.text(
        "・上段が画面、中段がその画面から呼ばれる処理、下段がテーブル。<br>"
        "・左から右へ、操作の順に読む。<br>"
        "・テーブルへの<b>書き込みは下向きの緑</b>の矢印。<br>"
        "・テーブルからの<b>読み取りは上向きの青</b>の矢印。<br>"
        "・丸数字は、その操作の中での処理の順序を示す。<br>"
        "・同じテーブルが複数の処理に出てくることがある。<br>"
        "　処理ごとに流れを追えるようにするため、あえて重複して描いている。",
        340,
        110,
        520,
        150,
    )

    # 名前の後ろの（　）は、見積もりで数える対象を見分けるための印である。
    # 意味を書いておかないと「（新規）と（未実装）は何が違うのか」が読み手に伝わらない。
    p.node("名前の後ろの（　）", S_HEAD, 340, 275, 300, 20, kind="text")
    p.text(
        "<b>この機能で作るかどうか</b>を示す。見積もりで数える対象を見分けるための印である。<br>"
        "<b>（新規）</b>　この機能で新しく作る。<b>作業量に数える</b><br>"
        "<b>（既存）</b>　他の機能で作成済み。そのまま使う。数えない<br>"
        "無印　　　　すでに在るものを、そのまま使う<br>"
        "<b>どの機能・どのチームが作るのかは書かない。</b>この図は役割分担を割り当てる図ではない。",
        340,
        300,
        520,
        88,
    )

    p.node("線の色", S_HEAD, 900, 80, 300, 20, kind="text")
    p.text(
        "灰色　　　：画面と処理のつながり<br>"
        "青　　　　：テーブルの読み取り<br>"
        "緑　　　　：テーブルへの書き込み（追加・更新）<br>"
        "赤　　　　：テーブルからの削除<br>"
        "茶（点線）：処理から画面への戻り<br>"
        "赤（点線）：外部キーによる連鎖削除",
        900,
        110,
        420,
        130,
    )

    y = 400
    p.node("スキーマの和名", S_HEAD, 40, y, 300, 20, kind="text")
    p.text(
        "<br>".join("%s　＝　%s" % (ja, en) for ja, en in schemas), 40, y + 25, 420, 50
        )

    y += 90
    p.node("テーブルの和名と物理名", S_HEAD, 40, y, 300, 20, kind="text")
    cell = (
        "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#B0BEC5;fontSize=11;"
        "align=left;spacingLeft=8;fontColor=#37474F;"
    )
    head = cell.replace("#FFFFFF", "#ECEFF1") + "fontStyle=1;"
    p.node("和名（図で使う名前）", head, 40, y + 25, 250, 30, kind="box")
    p.node("物理名（DB上の名前）", head, 290, y + 25, 330, 30, kind="box")
    for i, (ja, en) in enumerate(tables):
        ty = y + 55 + i * 30
        p.node(ja, cell, 40, ty, 250, 30, kind="box")
        p.node(en, cell, 290, ty, 330, 30, kind="box")

    if steps:
        # 本文は見出しの下端（420）より下から始める。「この図の範囲」の欄と同じ 425 にそろえる
        p.node("画面の段階", S_HEAD, 700, 400, 300, 20, kind="text")
        p.text(
            "<br>".join("%s：%s" % (no, name) for no, name in steps), 700, 425, 300, 170
            )

    scope_bottom = 570
    if scope:
        p.node("この図の範囲", S_HEAD, 1060, 400, 300, 20, kind="text")
        # 高さは本文から決める。固定にすると、範囲の説明が長い図で文字が枠から出る。
        # 凡例ページは文字あふれの検査（検査6）の対象外なので、検査でも気づけない
        scope_h = max(145, estimate_height(scope, 620))
        p.node(scope, S_NOTE, 1060, 425, 620, scope_h, kind="note")
        scope_bottom = 425 + scope_h

    # T.B.D の見本は、範囲の欄の下端とぶつからない位置へ置く
    tbd_y = max(600, scope_bottom + 30)
    p.node("確認が必要な事項の書きかた", S_HEAD, 700, tbd_y, 300, 20, kind="text")
    p.node(
        "<b>T.B.D　実装者に確認</b><br>"
        "仕様が未確定な箇所、実装が要件を満たしていない箇所は、この赤い破線の枠で示す。"
        "冒頭に「T.B.D　実装者に確認」と書き、続けて<b>何を確認したいのか</b>を箇条書きにする。<br>"
        "AIが書いたものは、<b>末尾に自動生成である旨を必ず添える</b>（下記の定型文）。<br>"
        "他の処理フロー図でも同じ書式を使う。" + AI_NOTE,
        S_TBD,
        700,
        tbd_y + 25,
        620,
        168,
        kind="note",
    )
    return p
