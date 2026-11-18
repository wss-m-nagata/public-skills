# -*- coding: utf-8 -*-
"""正本から、直す設計書の写しを、手元の作業フォルダへ取得する（正本は読み取りだけ）。

使い方:
    python fetch_from_source.py --folder <手元の作業フォルダ> <正本の中の相対パス>...

例:
    python fetch_from_source.py --folder <手元の作業フォルダ> \
        "<フォルダA>/<元の設計書>.xlsx" "<フォルダB>/<元の図>.drawio"

やること:
  - 正本の場所は、設定ファイル（.agents/config/design-doc-revision/settings.md）の
    「設計書のルート」と「正本の場所」から決める。
  - 配置は、設定の「構造を保つフォルダ」の下は同じ構成、それ以外は、作業フォルダの直下（空のときは、すべて同じ構成）。
  - 取得した時点の、最終更新日時と SHA-256 を、作業フォルダの記録ファイル（既定：取得の記録.json）に残す。
    SHA-256 は、あとで、正本が修正の元にした版のままかを確かめる（check_server_unchanged.py・反映スクリプト）のに使う。
  - 手元にすでに同じ名前のファイルがあれば、止める（直した内容を消さないため。--force で上書き）。
  - 最後に、READMEの配置表に貼れる行を表示する。
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import ensure_utf8, load_config, local_relative, sha256  # noqa: E402


def main():
    """引数を読み、正本から手元へ取得して、取得の記録を残す。"""
    ensure_utf8()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--folder", required=True, help="手元の作業フォルダ")
    ap.add_argument(
        "--force", action="store_true", help="手元に同じ名前があっても上書きする"
    )
    ap.add_argument("paths", nargs="+", help="正本の中の相対パス")
    args = ap.parse_args()

    # 設定の読み込み（作業フォルダから親へたどって、設定ファイルを探す）
    folder = Path(args.folder)
    cfg = load_config(folder)
    source = Path(cfg["design_root"]) / cfg["source_dir"]
    folder.mkdir(parents=True, exist_ok=True)
    record_path = folder / cfg["record_file"]
    record = (
        json.loads(record_path.read_text(encoding="utf-8"))
        if record_path.exists()
        else {}
    )

    # 先に全件を確かめる（1件でも問題があれば、何も取得しない）
    plan, problems = [], []
    for p in args.paths:
        src = source.joinpath(*p.replace(chr(92), "/").split("/"))
        rel = local_relative(p, cfg)
        dst = folder / rel
        if not src.is_file():
            problems.append(f"正本に無い（または、つながらない）: {p}")
        elif dst.exists() and not args.force:
            problems.append(
                f"手元にすでにある（直した内容を消さないため止めた。--force で上書き）: {rel}"
            )
        else:
            plan.append((p, src, rel, dst))
    if problems:
        print("問題があるため、何も取得していません。")
        for x in problems:
            print("  [NG]", x)
        sys.exit(1)

    # 取得（読み取りだけ。更新日時を保つ）
    lines = []
    for p, src, rel, dst in plan:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        mtime = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        digest = sha256(src)
        record[p.replace(chr(92), "/")] = {
            "local": rel,
            "modified": mtime,
            "sha256": digest,
        }
        print(f"取得: {p}\n   -> {rel}  （最終更新 {mtime}）")
        lines.append(f"| `{p}` | `{rel}` | {mtime} |")
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n記録: {record_path}")
    print("\nREADME の配置表に貼れる行（取得元 | 手元での配置 | 最終更新日時）:")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
