# -*- coding: utf-8 -*-
"""機能別ER図の配色・書式の定数。

生成スクリプトと検査スクリプトの両方がこの定数を使う。
見た目を変えるときは、ここと references/rules.md を同じ変更で直すこと。
"""

import html
import re


# テーブルの変更区分ごとの配色と見出しの接頭辞。
#   fill        : 箱の塗り
#   stroke      : 箱の枠線と、箱の中の区切り線
#   font        : 文字色
#   header_bg   : 見出し（論理名・物理名）の背景
#   prefix      : 見出しの論理名の前に付ける接頭辞
#   legend      : 凡例の見本に書く文言
#   dashed      : 枠線を点線にするかどうか
STATUS = {
    # 変更なし（現行DDLのまま使う）
    "unchanged": dict(fill="#FFFFFF", stroke="#8C8C8C", font="#333333", header_bg="#EFEFEF",
                      prefix="", legend="変更なし", dashed=False),
    # 列や制約を直す
    "changed": dict(fill="#FFF7E6", stroke="#E08A1E", font="#333333", header_bg="#EFEFEF",
                    prefix="［変更］", legend="［変更］列や制約を直す", dashed=False),
    # テーブルを新しく作る
    "new": dict(fill="#E8F5E9", stroke="#2E7D32", font="#333333", header_bg="#EFEFEF",
                prefix="［新規］", legend="［新規］テーブルを新しく作る", dashed=False),
    # テーブルごと削除する
    "abolished": dict(fill="#F5F5F5", stroke="#BDBDBD", font="#9E9E9E", header_bg="#EAEAEA",
                      prefix="［廃止］", legend="［廃止］テーブルごと削除する", dashed=True),
}

# 凡例に並べる順番
STATUS_ORDER = ("unchanged", "changed", "new", "abolished")

# 注記の種類ごとの書式。
#   point    : 設計の要点・変更点・処理フロー図との差異（訂正）・DB制約で表せない決まりごと（橙の囲み）
#   readonly : 値を読むだけでFKの無い関係の一覧（青の囲み）
#   scope    : この図に載せていないもの（青の囲み）
#   key      : 図全体の読み方の前提（区分の持ち方など、最初に読んでほしいこと）
#   tbd      : 決まっていないこと（赤い破線の枠。処理フロー図の T.B.D と同じ書式）。決まったら枠ごと消す
# 青の囲みは2種類ある。文字の色で見分ける。
#   scope    : 青い文字（「この図に載せていないもの」）
#   readonly : 濃い灰の文字（「値を読むだけでFKの無い関係」）
_BLUE_NOTE = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#F3F7FB;strokeColor=#90CAF9;dashed=0;"
              "verticalAlign=top;align=left;spacingLeft=10;spacingTop=6;fontSize=11;fontColor={font};")
NOTE_STYLE = {
    "point": ("rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF3E0;strokeColor=#FB8C00;"
              "fontColor=#5D4037;fontSize=11;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;"),
    "readonly": _BLUE_NOTE.format(font="#37474F"),
    "scope": _BLUE_NOTE.format(font="#1565C0"),
    "key": ("rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFDE7;strokeColor=#FBC02D;fontColor=#5D4037;"
            "fontSize=12;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;"),
    "tbd": ("rounded=0;whiteSpace=wrap;html=1;fillColor=#FFEBEE;strokeColor=#C62828;strokeWidth=2;dashed=1;"
            "fontColor=#B71C1C;fontSize=11;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;"),
}

# 注記の種類ごとの文字の大きさ（高さの見積もりに使う）
NOTE_FONT_SIZE = {"point": 11, "readonly": 11, "scope": 11, "key": 12, "tbd": 11}

# AIが書いた T.B.D の末尾に付ける定型文（process-flow-diagram の決まりと同じ文面）
TBD_AI_FOOTER = "※ この T.B.D はAIの自動生成です。内容は必ずしも正しいとは限りません。重要な情報は確認するようにしてください。"

# テーブルの箱。
# overflow=fill は、付けないと箱が中身より広いときに見出しの帯と区切り線が
# 右端まで届かない（drawio は中身の幅で帯を描くため）。
ENTITY_STYLE = ("rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=0;strokeWidth=2;"
                "overflow=fill;fontSize=11;fillColor={fill};strokeColor={stroke};fontColor={font};")

# ページの見出し・説明・区分見出し・凡例
TITLE_STYLE = "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=22;fontColor=#263238;fontStyle=1;"
DESC_STYLE = "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=13;fontColor=#37474F;"
# 区分見出しは線より手前に描き、白い背景で線が文字に重ならないようにする
SECTION_STYLE = ("text;html=1;align=left;verticalAlign=top;fontSize=14;fontColor=#546E7A;fontStyle=1;"
                 "labelBackgroundColor=#FFFFFF;")
LEGEND_HEAD_STYLE = "text;html=1;align=left;verticalAlign=top;fontSize=14;fontColor=#37474F;fontStyle=1;"
LEGEND_CHIP_STYLE = ("rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor={font};"
                     "fontSize=12;align=center;verticalAlign=top;spacingLeft=10;spacingTop=6;")
LEGEND_TEXT_STYLE = "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=12;fontColor=#37474F;"

# 削除予定のテーブルをまとめる帯
BAND_STYLE = ("rounded=0;whiteSpace=wrap;html=1;fillColor=#FAFAFA;strokeColor=#BDBDBD;fontColor=#757575;"
              "fontSize=15;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;")
BAND_TEXT = "<b>削除予定のテーブル</b>　この処理では使わない。どこから参照されるかを示す必要が無いため、関連線は引かない。"

# 変更点の表（凡例・変更点ページ）
TABLE_HEAD_STYLE = ("rounded=0;whiteSpace=wrap;html=1;fillColor=#ECEFF1;strokeColor=#B0BEC5;fontColor=#37474F;"
                    "fontSize=12;align=center;verticalAlign=top;spacingLeft=10;spacingTop=6;")
TABLE_CELL_STYLE = ("rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor=#B0BEC5;fontColor=#37474F;"
                    "fontSize=12;align={align};verticalAlign=top;spacingLeft=10;spacingTop=6;")
# 変更点の表の「区分」ごとの行の塗り
CHANGE_KIND_FILL = {"変更": "#FFF7E6", "新規": "#E8F5E9", "廃止": "#F5F5F5", "変更なし": "#FFFFFF", "対象外": "#FFFFFF"}

# 関連線。親（参照される側）を source、子（FKを持つ側）を target にする。
EDGE_BASE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;fontSize=11;endArrow={end};endFill=0;"
             "startArrow=ERone;startFill=0;strokeColor=#5A6470;")
EDGE_LABEL_EXTRA = "fontSize=10;fontColor=#5A6470;"
# 線の種類。
#   fk         : 外部キー（実線、1対多）
#   zero_to_one: 外部キー＋一意制約で、子の行が無いこともある関係（実線、1対0..1）。DDLの外部キー＋一意制約はこれ
#   one_to_one : 子の行が必ず1件ある関係（実線、1対1）。業務上必ず作る場合だけ使う
#   value      : 値だけを持ち、FKを張らない関係（点線）
#   simplified : 実際は別のテーブル経由の複合FKなどを、簡略化して直接つないだ線（点線、注記必須）
EDGE_KIND = {
    "fk": dict(end="ERzeroToMany", dashed=False, default_label=""),
    "zero_to_one": dict(end="ERzeroToOne", dashed=False, default_label="1:0..1（UNIQUE）"),
    "one_to_one": dict(end="ERone", dashed=False, default_label="1:1（UNIQUE）"),
    "value": dict(end="ERzeroToMany", dashed=True, default_label="値のみ保持"),
    "simplified": dict(end="ERzeroToMany", dashed=True, default_label=None),
}

# 用紙の余白（px）。全図形の右端・下端から、この2倍以上の余白を取って用紙の大きさを決める。図全体を囲む枠は置かない。
PAGE_MARGIN = 40

# 決めた日・確認した日（例：「（YYYY-MM-DD 決定）」「（YYYY/MM/DD）」「M月D日に合意」）は、ER図に書かない（rules.md の 7）。
# 年月日のそろった日付は、語に関係なくすべて拾う。
# 例外は、すぐ後ろに「時点」が続く基準日（例：変更点の表の「（YYYY-MM-DD 時点）」）だけである。
# 年の無い「M月D日」は、毎年の決まりや期限にも使うため、決めたことを表す語が続くときだけ拾う。
_DIGIT = "[0-9０-９]"
_DATE_FULL = re.compile(
    rf"{_DIGIT}{{4}}\s*[-/.／．年]\s*{_DIGIT}{{1,2}}\s*[-/.／．月]\s*{_DIGIT}{{1,2}}日?(?![0-9０-９日])(?!\s*時点)")
_DATE_MD_DECIDED = re.compile(rf"{_DIGIT}{{1,2}}月{_DIGIT}{{1,2}}日[^。\n]{{0,8}}?(?:決定|決め|決ま|合意|了承|承認)")
# 図形の値（HTML）を行に分ける区切り
_LINE_BREAK = re.compile(r"</div>|</p>|</li>|<br\s*/?>", re.I)


def plain_lines(value):
    """図形の値（HTML）を、タグを除いた文字の行に分ける。

    value: 図形の value 属性（HTML）、または JSON に書いた文字列。
    戻り値: 空でない行の並び。
    """
    parts = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in _LINE_BREAK.split(value or "")]
    return [p for p in parts if p]


def find_dated_decision(text):
    """決めた日・確認した日として拾う日付を探す。

    text: 1行分の文字。
    戻り値: 見つけた部分の文字。無ければ None。
    """
    for pattern in (_DATE_FULL, _DATE_MD_DECIDED):
        m = pattern.search(text)
        if m:
            return m.group(0)
    return None

# 箱の中の文字の見積もり（fontSize=11）。drawio の描画幅をもとにした概算値。
ENTITY_FONT_PX = 11
LINE_HEIGHT = 14
