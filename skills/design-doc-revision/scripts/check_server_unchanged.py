# -*- coding: utf-8 -*-
"""作業フォルダに取得したファイルが、正本の今のファイルと同じ版かを確かめる（正本は読み取りだけ）。

fetch_from_source.py が取得の記録ファイル（既定：取得の記録.json）に残した SHA-256 と、正本の今のファイルの SHA-256 を比べる。
不一致なら、取得してから、誰かが正本のファイルを直している。
その版を元にして直した内容を上げると、相手の直した内容が消えるため、止まって確かめる。

使い方:
    python check_server_unchanged.py <作業フォルダ>

出力：取得したファイルごとに、「一致」「不一致（サーバーが変わっている）」「サーバーに無い」。
終了コード：すべて一致なら 0。不一致・サーバーに無い・記録が無いものがあれば 1。

使うとき：
  - 報告する前（SKILL.md の「見た目と整合を確かめる」）。
  - レビュー用の置き場へ上げるスクリプト・正本へ反映するスクリプトを作る前（make_scripts.py の前）。
  （反映スクリプトも、実行のときに、同じ突き合わせを行う）
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ensure_utf8, load_config, sha256  # noqa: E402


def check(folder):
    """取得の記録と、正本の今のファイルを比べる。

    Args:
        folder (Path): 作業フォルダ。

    Returns:
        list[tuple[str, str]]: （正本の中の相対パス, 結果）。結果は「一致」「不一致」「サーバーに無い」。
    """
    cfg = load_config(folder)
    record_path = folder / cfg["record_file"]
    if not record_path.is_file():
        raise FileNotFoundError(f"取得の記録がありません: {record_path}")
    record = json.loads(record_path.read_text(encoding="utf-8"))

    source = Path(cfg["design_root"]) / cfg["source_dir"]
    results = []
    for rel, item in record.items():
        src = source.joinpath(*rel.split("/"))
        if not src.is_file():
            results.append((rel, "サーバーに無い"))
        elif sha256(src).upper() == item["sha256"].upper():
            results.append((rel, "一致"))
        else:
            results.append((rel, "不一致"))
    return results


def main():
    ensure_utf8()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("folder", help="作業フォルダ")
    args = parser.parse_args()

    try:
        results = check(Path(args.folder))
    except FileNotFoundError as error:
        print(f"NG: {error}")
        sys.exit(1)

    bad = [r for r in results if r[1] != "一致"]
    for rel, status in results:
        mark = "OK" if status == "一致" else "NG"
        note = (
            "（取得してから、正本のファイルが変わっている）"
            if status == "不一致"
            else ""
        )
        print(f"{mark} {status}{note}: {rel}")
    if bad:
        print(
            "\nNG: 取得した版から、正本が変わっています。変更の内容を確かめ、取り込み直すかを、ユーザーと決めてください。"
        )
        sys.exit(1)
    print(f"\nOK: {len(results)} ファイルとも、取得した版のままです。")


if __name__ == "__main__":
    main()
