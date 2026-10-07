# -*- coding: utf-8 -*-
"""
作業用の出力先（プロジェクトルートの .agents/state/nablarch-basic-design-excel/）を整理する。

【背景】このスキルは、途中のファイルも含めて出力先に書き出すため、放っておくと数百〜千のファイルが溜まり、
どれが今の作業のものか分からなくなる。そこで、作業ごとに <YYYYMMDD>_<件名>/ のフォルダを作る決まりにし
（SKILL.md「ローカル実行の手順」）、このスクリプトで古いものを見つけて片付ける。

処理内容:
    - 出力先の直下にあるファイル（決まりに反して、作業フォルダの外に置かれたもの）を一覧にする。
    - 作業フォルダのうち、中のファイルの最終更新日が --days 日より前のものを一覧にする。
      件数・大きさ・最終更新日も表示する。
    - --keep で指定したフォルダは、古くても一覧に出さない（例：正本を作り直すための中間データ）。
    - 既定では一覧を表示するだけで、何も消さない。
      --delete を付けたときだけ、一覧に出たものを消す。

使い方:
    python cleanup_state.py <出力先ディレクトリ> [--days 14] [--keep <フォルダ名> ...] [--delete]

例:
    # 何が古いかを確かめる（消さない）
    python cleanup_state.py .agents/state/nablarch-basic-design-excel

    # 30日より前の作業フォルダと、直下のファイルを消す。step1_master は残す
    python cleanup_state.py .agents/state/nablarch-basic-design-excel --days 30 --keep step1_master --delete

安全のため、出力先のパスに「.agents」と「state」が含まれない場合は、何もせずに止まる。
消す前には、成果物がファイルサーバーなどに上がっていることを、ユーザーに確かめること。
"""

import argparse
import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio


def _summary(path):
    """ファイルまたはフォルダの、件数・大きさ（バイト）・最終更新日時を返す。

    Args:
        path (Path): 対象のパス。

    Returns:
        tuple[int, int, datetime.datetime]: ファイル数、大きさの合計、最終更新日時。
    """
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    if not files:
        mtime = path.stat().st_mtime
        return 0, 0, datetime.datetime.fromtimestamp(mtime)
    size = sum(p.stat().st_size for p in files)
    latest = max(p.stat().st_mtime for p in files)
    return len(files), size, datetime.datetime.fromtimestamp(latest)


def find_targets(state_dir, days, keep):
    """片付ける候補（直下のファイルと、古い作業フォルダ）を集める。

    Args:
        state_dir (Path): 出力先ディレクトリ。
        days (int): この日数より前に最終更新されたフォルダを古いとみなす。
        keep (list[str]): 一覧に出さないフォルダ名。

    Returns:
        list[tuple[Path, str, int, int, datetime.datetime]]: パス・理由・件数・大きさ・最終更新日時。
    """
    border = datetime.datetime.now() - datetime.timedelta(days=days)
    targets = []
    for path in sorted(state_dir.iterdir()):
        count, size, latest = _summary(path)
        if path.is_file():
            targets.append((path, "直下のファイル", count, size, latest))
        elif path.name not in keep and latest < border:
            targets.append((path, f"{days}日より前", count, size, latest))
    return targets


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="作業用の出力先を整理する")
    parser.add_argument("state_dir")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--keep", nargs="*", default=[])
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()

    state_dir = Path(args.state_dir).resolve()
    if ".agents" not in state_dir.parts or "state" not in state_dir.parts:
        print(f"NG: 出力先ではないパスのため止めました: {state_dir}")
        sys.exit(1)
    if not state_dir.is_dir():
        print(f"NG: フォルダがありません: {state_dir}")
        sys.exit(1)

    targets = find_targets(state_dir, args.days, args.keep)
    if not targets:
        print("片付けるものはありません。")
        return

    total = sum(t[3] for t in targets)
    print(
        f"{'消します' if args.delete else '片付ける候補'}: {len(targets)} 件（{total / 1024 / 1024:.1f}MB）"
    )
    for path, reason, count, size, latest in targets:
        print(
            f"  - {path.name}  {reason}  {count}ファイル  {size / 1024:.0f}KB  最終更新 {latest:%Y-%m-%d}"
        )

    if not args.delete:
        print(
            "（一覧を表示しただけです。消すときは --delete を付けて実行してください）"
        )
        return
    for path, *_ in targets:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    print("OK: 消しました。")


if __name__ == "__main__":
    main()
