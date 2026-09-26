# -*- coding: utf-8 -*-
"""既にある .drawio を安全に直すための雛形。

改版履歴
2026/09/04: 圧縮形式の .drawio を検出して、控えを取る前に止めるようにした。
  その形式では mxGraphModel が現れずセルが1つも取れないため、書き換えが空振りし、
  それでも「書き換えました」と表示していた。
2026/09/03: 新規作成。人とAIが交互に図を直す運用で、毎回同じ手順を組み立て直して
  いたため（控えを取る／前提を検査する／書き込み直前に競合を確かめる／差分で確認する）、
  抜けが出ていた。ここに固めて、呼ぶ側は「何を変えるか」だけ書けばよいようにした。

人が drawio で保存した図に対しては、生成スクリプトを再実行できない（手直しが消える）。
そのため XML を直接いじることになるが、直接いじる作業には決まった危険が4つある。

    0. 圧縮形式でセルが1つも取れず、何も変えていないのに成功したように見える
    1. 直す前の状態を残しておらず、間違えても戻せない
    2. 読み込んでから書き込むまでの間に人が保存し、その分を消してしまう
    3. 座標や ID を当てにして書き換え、人が図をいじったせいで狙いを外す
    4. 意図した以外のところまで変えたことに気づかない

このモジュールは 0・1・2・4 を引き受ける。3 は変更内容ごとに違うので、
呼ぶ側が `apply` の中で `assert` を書く。

使い方:

    import xml.etree.ElementTree as ET
    from edit_existing import edit_drawio, find_cell, label

    def apply(tree):
        page = tree.getroot().findall("diagram")[1]      # ②シグナル詳細
        cell = find_cell(page, "n20")

        # ---- 前提の検査。想定と違えば、何も変えずに止める ----
        assert label(cell) == "検知理由（保存先未定）", "中身が想定と違う: %r" % label(cell)

        # ---- 書き換え ----
        cell.set("value", "AI提案")
        return ["n20 の中身を 検知理由 → AI提案 に変えた"]      # 報告用の記録を返す

    edit_drawio("tmp/処理フロー/処理フロー_シグナル管理.drawio", apply)

`apply` が例外を投げれば、ファイルは1バイトも書き換わらない。
迷ったら、まず `assert` を厚く書いてから中身を書く。
"""

import hashlib
import io
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET

# 圧縮形式の判定は drawio_builder が持っている。スキル同梱の scripts/ から読み込む
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"),
)
from drawio_builder import DrawioFormatError, assert_expanded_drawio  # noqa: E402,F401


def label(cell):
    """図形の見出し。タグを落として返す。前提の検査で中身を確かめるのに使う。"""
    return re.sub(r"<[^>]+>", "", cell.get("value") or "").strip()


def find_cell(page, cell_id):
    """ページから id でセルを1つ取る。無ければ止める。

    座標で探すより id で探すほうが安全である。人が図形を動かしても id は変わらない。
    id は diff_drawio.py の出力や、図を読んだときの一覧から拾う。
    """
    for cell in page.findall(".//mxCell"):
        if cell.get("id") == cell_id:
            return cell
    raise AssertionError("セル %s が見つからない" % cell_id)


def edge_endpoints(page):
    """そのページで線がつながっている図形の id を全部集める。

    図形を消す前に「線がつながっていないか」を確かめるために使う。
    つながったまま消すと、drawio 上で線が宙に浮く。
    """
    endpoints = set()
    for cell in page.findall(".//mxCell"):
        if cell.get("edge") == "1":
            endpoints |= {cell.get("source"), cell.get("target")}
    return endpoints


def _digest(path):
    """ファイルの中身のハッシュ。読んだ時点と書く直前で見比べ、競合を検知する。"""
    with io.open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def edit_drawio(path, apply, backup_dir=None):
    """既にある .drawio を、控えを取り競合を確かめたうえで書き換える。

    @param path 対象の .drawio
    @param apply 書き換えを行う関数。ElementTree を受け取り、変更内容の記録（文字列のリスト）を返す
    @param backup_dir 控えの置き先。省略時は環境変数 CLAUDE_SCRATCHPAD、それも無ければ対象と同じ場所
    @return 控えのパス
    """
    # ---- 控えを取る。間違えたときに戻せるようにするため ----
    # ---- まず形式を確かめる。圧縮形式ならセルが1つも取れず、apply が空振りする ----
    # 控えを取る前に見る。読めない形式なら、何もせずに止めるのが安全である
    assert_expanded_drawio(path)

    if backup_dir is None:
        backup_dir = os.environ.get("CLAUDE_SCRATCHPAD") or os.path.dirname(
            os.path.abspath(path)
        )
    os.makedirs(backup_dir, exist_ok=True)
    backup = os.path.join(backup_dir, os.path.basename(path) + ".bak")
    shutil.copy2(path, backup)

    # ---- 読み込む。このときのハッシュを覚えておく ----
    before = _digest(path)
    tree = ET.parse(path)

    # ---- 呼び出し側の書き換え。ここで例外が出れば、ファイルは無傷のまま ----
    changes = apply(tree) or []

    # ---- 書き込む直前に、人が保存していないかを確かめる ----
    # 調べている間に drawio で保存されることがある。気づかず上書きすると、その分が消える。
    if _digest(path) != before:
        raise RuntimeError(
            "読み込んでから今までの間に %s が更新された。\n"
            "drawio 側で保存された可能性が高い。書き込みは中止した。\n"
            "図を読み直し、変更内容が今も成り立つかを確かめてからやり直すこと。" % path
        )

    # ---- 書き込む。インデントは drawio の保存形式（4スペース）に合わせる ----
    ET.indent(tree, space="    ")
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        ET.tostring(tree.getroot(), encoding="unicode")
    )

    for line in changes:
        print("  " + line)
    print("\n書き換えました: %s" % path)
    print("控え: %s" % backup)
    skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("\n次の2つを必ず実行すること:")
    print(
        '  python "%s" "%s"'
        % (os.path.join(skill, "scripts", "validate_drawio.py"), path)
    )
    print(
        '  python "%s" "%s" "%s"'
        % (os.path.join(skill, "scripts", "diff_drawio.py"), backup, path)
    )
    print("差分に、意図した以外の項目（特に線のつなぎ先・スタイル）が出たら、")
    print("人の編集と競合している。上書きを続けずに報告すること。")
    return backup


if __name__ == "__main__":
    print(__doc__)
