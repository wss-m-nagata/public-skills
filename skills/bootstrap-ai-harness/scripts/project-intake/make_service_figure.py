#!/usr/bin/env python3
"""入力シートのアプリ構成シートに貼る、構成のイメージ図（PNG）を描く。

画面（フロントエンド）は1つ、バックエンドは業務の塊（サービス）ごとに分ける構成と、業務の塊の分け方の目安を描く。
例は、架空のアプリ「備品管理システム」にする。

- 高解像度（2倍）で描き、Excelでは半分の大きさで表示する。
- 日本語のフォントが要る。既定は Windows のメイリオ。ほかの環境では --font、--font-bold で指定する。
- Pillow が要る。
- 図を変えたら、build_intake.py を実行して、Excelを作り直す。

使い方（スキルのディレクトリで実行する）:
  python scripts/project-intake/make_service_figure.py
  python scripts/project-intake/make_service_figure.py --font <通常のフォント> --font-bold <太字のフォント>
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 出力先（スキル直下の assets/project-intake）
_OUT = Path(__file__).resolve().parents[2] / "assets" / "project-intake" / "service_figure.png"
# 高解像度で描く倍率と、図の大きさ（表示の大きさ）
_S = 2
_W, _H = 1240, 490
# 文字と線の色
_TEXT = "#1a1a1a"
_LINE = "#404040"


class _Canvas:
    """図を描く。座標は表示の大きさで指定し、描くときに倍率を掛ける。"""

    def __init__(self, font_regular: str, font_bold: str):
        """白い画像と、使うフォントを用意する。"""
        self.img = Image.new("RGB", (_W * _S, _H * _S), "white")
        self.d = ImageDraw.Draw(self.img)
        self.font_regular = font_regular
        self.font_bold = font_bold

    def font(self, size: int, bold: bool = False):
        """指定の大きさのフォントを返す。"""
        return ImageFont.truetype(self.font_bold if bold else self.font_regular, size * _S)

    def text(self, x: int, y: int, text: str, size: int, bold: bool = False, fill: str = _TEXT) -> None:
        """文字を書く。"""
        self.d.text((x * _S, y * _S), text, font=self.font(size, bold), fill=fill)

    def box(self, x1, y1, x2, y2, fill, outline, lines, dash=False) -> None:
        """角丸の箱（dash のときは点線の枠）を描き、中に複数行の文字を中央ぞろえで書く。lines は (文字, 大きさ, 太字か)。"""
        if dash:
            # 点線の枠（業務の塊をまとめる範囲）
            step = 12
            for x in range(x1, x2, step * 2):
                for y in (y1, y2):
                    self.d.line([(x * _S, y * _S), (min(x + step, x2) * _S, y * _S)], fill=outline, width=2 * _S)
            for y in range(y1, y2, step * 2):
                for x in (x1, x2):
                    self.d.line([(x * _S, y * _S), (x * _S, min(y + step, y2) * _S)], fill=outline, width=2 * _S)
        else:
            self.d.rounded_rectangle([x1 * _S, y1 * _S, x2 * _S, y2 * _S], radius=10 * _S,
                                     fill=fill, outline=outline, width=2 * _S)
        if not lines:
            return
        # 文字の高さの合計から、縦の中央に置く位置を決める
        fonts = [self.font(size, bold) for _, size, bold in lines]
        heights = [f.getbbox(t)[3] + 6 * _S for (t, _, _), f in zip(lines, fonts)]
        y = (y1 + y2) * _S / 2 - sum(heights) / 2
        for (t, _, _), f, h in zip(lines, fonts, heights):
            w = self.d.textlength(t, font=f)
            self.d.text(((x1 + x2) * _S / 2 - w / 2, y), t, font=f, fill=_TEXT)
            y += h

    def arrow(self, x, y1, y2, label=None) -> None:
        """下向きの矢印を描く。"""
        self.d.line([(x * _S, y1 * _S), (x * _S, (y2 - 8) * _S)], fill=_LINE, width=2 * _S)
        self.d.polygon([((x - 7) * _S, (y2 - 10) * _S), ((x + 7) * _S, (y2 - 10) * _S), (x * _S, y2 * _S)], fill=_LINE)
        if label:
            self.text(x + 8, (y1 + y2) // 2 - 10, label, 12, fill=_LINE)


def draw(out: Path, font_regular: str, font_bold: str) -> None:
    """構成のイメージ図を描いて保存する。"""
    c = _Canvas(font_regular, font_bold)

    # 左：構成（利用者 → 画面 → 業務の塊ごとのサービス → データ）
    c.text(20, 8, "このアプリの構成（例：架空の「備品管理システム」）", 16, bold=True)
    c.box(330, 44, 550, 84, "#f2f2f2", "#808080", [("利用者（ブラウザー）", 13, False)])
    c.arrow(440, 84, 112)
    c.box(40, 112, 840, 182, "#dbe7ff", "#3460fb", [
        ("画面（フロントエンド）　…　アプリ全体で 1 つ", 15, True),
        ("メニュー：備品　／　貸出　／　発注", 13, False),
    ])
    c.box(28, 200, 852, 452, None, "#c55a11", None, dash=True)
    c.text(40, 458, "↑ 点線の中が、バックエンド　…　業務の塊（サービス）ごとに分けて作る", 13, bold=True, fill="#c55a11")
    services = [
        ("サービス：備品", "備品台帳の", "登録・参照", "備品、備品の分類"),
        ("サービス：貸出", "備品の", "貸出と返却の記録", "貸出、返却"),
        ("サービス：発注", "備品の発注と", "取引先の管理", "発注、取引先"),
    ]
    for i, (name, line1, line2, tables) in enumerate(services):
        x1 = 48 + i * 268
        x2 = x1 + 248
        cx = (x1 + x2) // 2
        c.arrow(cx, 182, 252, "API を呼ぶ" if i == 0 else None)
        c.box(x1, 252, x2, 344, "#fbe5d6", "#c55a11", [(name, 14, True), (line1, 12, False), (line2, 12, False)])
        c.arrow(cx, 344, 372)
        c.box(x1 + 14, 372, x2 - 14, 436, "#f2f2f2", "#808080", [("データ（テーブル）", 12, True), (tables, 12, False)])

    # 右：業務の塊の分け方の目安
    c.box(872, 44, 1224, 452, "#fffbe6", "#bf9000", None)
    c.text(888, 56, "業務の塊の分け方の目安", 15, bold=True)
    tips = [
        ("● 同じデータ（テーブル）を扱う業務は、", False),
        ("　 同じ塊にする。", False),
        ("● データを管理する部署が違う業務は、", False),
        ("　 別の塊にする。", False),
        ("● 一緒に変わることが多い業務は、", False),
        ("　 同じ塊にする。", False),
        ("● メニューの第1階層が、ひとつの目安に", False),
        ("　 なる。", False),
        ("", False),
        ("迷うとき・指定がないときは、", True),
        ("サービスを 1 つにして始める。", True),
        ("後から分けることもできる。", True),
    ]
    for i, (t, bold) in enumerate(tips):
        c.text(888, 96 + i * 28, t, 13, bold=bold)

    out.parent.mkdir(parents=True, exist_ok=True)
    c.img.save(out)


def main() -> None:
    """引数を読み、図を描く。"""
    parser = argparse.ArgumentParser(description="入力シートのアプリ構成シートに貼る、構成のイメージ図を描く。")
    parser.add_argument("--out", type=Path, default=_OUT, help="出力先（既定：assets/project-intake/service_figure.png）")
    parser.add_argument("--font", default=r"C:\Windows\Fonts\meiryo.ttc", help="通常の文字のフォントファイル")
    parser.add_argument("--font-bold", default=r"C:\Windows\Fonts\meiryob.ttc", help="太字のフォントファイル")
    args = parser.parse_args()
    draw(args.out, args.font, args.font_bold)
    print(f"作成: {args.out}")


if __name__ == "__main__":
    main()
