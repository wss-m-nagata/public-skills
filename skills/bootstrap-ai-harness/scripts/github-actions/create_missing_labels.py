#!/usr/bin/env python3
"""ラベル定義（labels.json）にあって、GitHubのリポジトリに無いラベルだけを作る。

- 既定は確認だけ（dry-run）。作るラベルの一覧を表示して終わる。
- 実際に作るのは --apply を付けたときだけ。GitHubへの変更になるため、実行は人が行う。
- 既存のラベルは、変更も削除もしない。色や説明が違うものは、差異を表示するだけ。
- 何回実行しても、結果は同じになる（足りないものだけを作るため）。

使い方（対象プロジェクトのルートで実行する）:
  python <スキル>/scripts/github-actions/create_missing_labels.py
  python <スキル>/scripts/github-actions/create_missing_labels.py --apply
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# GitHubのラベルの説明の上限（文字数）
_DESCRIPTION_MAX = 100
_COLOR_PATTERN = re.compile(r"^[0-9a-fA-F]{6}$")


def _load_definitions(path: Path) -> list[dict]:
    """ラベル定義のJSONを読み、形式を検査して返す。形式が誤っていれば、終了する。"""
    if not path.is_file():
        sys.exit(f"Error: ラベル定義が見つかりません: {path}")
    labels = json.loads(path.read_text(encoding="utf-8")).get("labels")
    if not isinstance(labels, list) or not labels:
        sys.exit("Error: labels に、1つ以上のラベルを書いてください")

    errors = []
    names = set()
    for item in labels:
        name = str(item.get("name", "")).strip()
        color = str(item.get("color", ""))
        description = str(item.get("description", ""))
        if not name:
            errors.append(f"name が空のラベルがあります: {item}")
        if name.lower() in names:
            errors.append(f"name が重複しています（大文字小文字は区別されません）: {name}")
        names.add(name.lower())
        if not _COLOR_PATTERN.match(color):
            errors.append(f"{name}: color は6桁の16進数にしてください（例: d73a4a）: {color}")
        if len(description) > _DESCRIPTION_MAX:
            errors.append(f"{name}: description は{_DESCRIPTION_MAX}文字以内にしてください")
    if errors:
        sys.exit("Error:\n  " + "\n  ".join(errors))
    return labels


def _list_existing_labels() -> dict[str, dict]:
    """リポジトリの既存ラベルを、小文字の名前をキーにして返す。ghが使えなければ終了する。"""
    result = subprocess.run(
        ["gh", "label", "list", "--limit", "500", "--json", "name,color,description"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        sys.exit(f"Error: gh label list に失敗しました（gh の認証と、リポジトリを確認してください）\n{result.stderr}")
    return {item["name"].lower(): item for item in json.loads(result.stdout)}


def main() -> None:
    """定義と既存ラベルを比べ、足りないラベルを表示し、--apply のときは作る。"""
    # Windowsでも、日本語のメッセージが文字化けしないようにする
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--definitions", default=".github/labels.json", help="ラベル定義のパス（既定: .github/labels.json）")
    parser.add_argument("--apply", action="store_true", help="足りないラベルを実際に作る（省略時は確認だけ）")
    args = parser.parse_args()

    definitions = _load_definitions(Path(args.definitions))
    existing = _list_existing_labels()

    # 足りないラベルと、既存だが内容が違うラベルに分ける
    missing = []
    differs = []
    for item in definitions:
        found = existing.get(item["name"].lower())
        if found is None:
            missing.append(item)
        elif found["color"].lower() != item["color"].lower() or (found["description"] or "") != item["description"]:
            differs.append((item, found))

    print(f"定義 {len(definitions)} 件 / 既存で一致 {len(definitions) - len(missing) - len(differs)} 件 / 不足 {len(missing)} 件 / 差異あり {len(differs)} 件")
    for item, found in differs:
        print(f"  [差異あり・変更しない] {item['name']}: 既存の説明「{found['description']}」/ 定義の説明「{item['description']}」")
    for item in missing:
        print(f"  [{'作成' if args.apply else '作成予定'}] {item['name']}: {item['description']}")

    if not missing:
        print("作成するラベルはありません。")
        return
    if not args.apply:
        print("確認だけです。作成するときは --apply を付けて、もう一度実行してください。")
        return

    # 足りないラベルを作る
    for item in missing:
        subprocess.run(
            ["gh", "label", "create", item["name"], "--color", item["color"], "--description", item["description"]],
            check=True,
            encoding="utf-8",
        )
    print(f"{len(missing)} 件のラベルを作成しました。")


if __name__ == "__main__":
    main()
