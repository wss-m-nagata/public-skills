#!/usr/bin/env python3
"""GitHub Actionsのひな形を、対象プロジェクトの正しい場所へ写す。

- 既定は確認だけ（dry-run）。写す先と、スキップするものを表示して終わる。
- 実際に写すのは --apply を付けたときだけ。
- 同名のファイルが既にあるときは、上書きせず、スキップして表示する。
- 修正履歴の担当者は、--author で人が指定した値だけを入れる。指定がなければ置き換えない。
- Gitのステージは、行わない。写した .sh は、実行権限を付けて git add --chmod=+x する必要がある。

使い方（対象プロジェクトのルートで実行する）:
  python <スキル>/scripts/github-actions/install_github_actions.py --features review,labeling
  python <スキル>/scripts/github-actions/install_github_actions.py --features review,labeling --author "<会社の略称><氏名>" --apply
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# ひな形の置き場所（スキル直下の assets/optional/github-actions）
_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "optional" / "github-actions"

# 機能ごとの、ひな形（_ASSETS からの相対パス）と、対象プロジェクトでの置き先
_FEATURES = {
    # PRのAIレビュー
    "review": {
        "workflows/claude-code-review.yml": ".github/workflows/claude-code-review.yml",
        "claude/code-review-focus.md": ".github/claude/code-review-focus.md",
    },
    # Issueの自動ラベル付け
    "labeling": {
        "workflows/issue-triage.yml": ".github/workflows/issue-triage.yml",
        "commands/label-issue.md": ".claude/commands/label-issue.md",
        "scripts/gh.sh": "scripts/gh.sh",
        "scripts/edit-issue-labels.sh": "scripts/edit-issue-labels.sh",
        "scripts/stage-executable-scripts.sh": "scripts/stage-executable-scripts.sh",
        "labels.json": ".github/labels.json",
    },
}

# 修正履歴の記入用の表記
_DATE_PLACEHOLDER = "<YYYY/MM/DD>"
_AUTHOR_PLACEHOLDER = "<会社の略称><氏名>"
_PLACEHOLDER_PATTERN = re.compile(re.escape(_DATE_PLACEHOLDER) + "|" + re.escape(_AUTHOR_PLACEHOLDER))


def _render(source: Path, author: str | None, today: str) -> str:
    """ひな形を読み、日付と（指定があれば）担当者を置き換えた本文を返す。"""
    text = source.read_text(encoding="utf-8").replace("\r\n", "\n")
    text = text.replace(_DATE_PLACEHOLDER, today)
    if author:
        text = text.replace(_AUTHOR_PLACEHOLDER, author)
    return text


def main() -> None:
    """選んだ機能のひな形を、確認、または対象プロジェクトへ写す。"""
    # Windowsでも、日本語のメッセージが文字化けしないようにする
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--features", required=True, help="写す機能（カンマ区切り）: " + ", ".join(_FEATURES))
    parser.add_argument("--target", default=".", help="対象プロジェクトのルート（既定: カレントディレクトリ）")
    parser.add_argument("--author", help="修正履歴に入れる、会社の略称と氏名（人が指定する。省略時は置き換えない）")
    parser.add_argument("--date", default=date.today().strftime("%Y/%m/%d"), help="修正履歴に入れる日付（既定: 今日）")
    parser.add_argument("--apply", action="store_true", help="実際に写す（省略時は確認だけ）")
    args = parser.parse_args()

    # 引数の検査
    names = [n.strip() for n in args.features.split(",") if n.strip()]
    unknown = [n for n in names if n not in _FEATURES]
    if unknown:
        sys.exit(f"Error: 不明な機能です: {', '.join(unknown)}（使える機能: {', '.join(_FEATURES)}）")
    target = Path(args.target).resolve()
    if not (target / ".git").exists():
        sys.exit(f"Error: Gitリポジトリのルートではありません: {target}")

    # ファイルごとに、写す・スキップを判定する
    written = []
    skipped = 0
    for name in names:
        for src_rel, dest_rel in _FEATURES[name].items():
            source = _ASSETS / src_rel
            dest = target / dest_rel
            if not source.is_file():
                sys.exit(f"Error: ひな形が見つかりません: {source}")
            text = _render(source, args.author, args.date)
            if dest.exists():
                same = dest.read_text(encoding="utf-8").replace("\r\n", "\n") == text
                print(f"  [スキップ・{'同一' if same else '内容が異なる'}] {dest_rel}")
                skipped += 1
                continue
            print(f"  [{'写した' if args.apply else '写す予定'}] {dest_rel}")
            if args.apply:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8", newline="\n")
                if dest.suffix == ".sh":
                    dest.chmod(0o755)
                written.append(dest_rel)

    if not args.apply:
        print("確認だけです。写すときは --apply を付けて、もう一度実行してください。")
        return

    print(f"{len(written)} 件を写し、{skipped} 件をスキップしました。")

    # 人が対応するものを表示する
    remaining = [p for p in written if _PLACEHOLDER_PATTERN.search((target / p).read_text(encoding="utf-8"))]
    if remaining:
        print("次のファイルの修正履歴に、記入用の表記が残っています。人が、会社の略称と氏名を書いてください:")
        for p in remaining:
            print(f"  {p}")
    if any(p.endswith(".sh") for p in written):
        print("写した .sh は、コミットの前に、実行権限を付けてステージしてください:")
        print("  bash scripts/stage-executable-scripts.sh")
    if "labeling" in names:
        print("Issueの自動ラベル付けを使うときは、.github/labels.json を、プロジェクトのラベルに書き換えてから、ラベルを作ってください:")
        print("  python <スキル>/scripts/github-actions/create_missing_labels.py")


if __name__ == "__main__":
    main()
