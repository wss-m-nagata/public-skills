#!/usr/bin/env python3
"""おすすめの設定を、対象プロジェクトの `.claude/settings.json` などに反映する。

項目（--items で、カンマ区切りで指定する）:
  permissions      承認なしで許可、確認、禁止する操作を、`.claude/settings.json` の `permissions` に統合する。
  formatter-hooks  保存時の整形のフック（Prettier、Black）を、`.claude/hooks/formatter/` に写し、
                   `.claude/settings.json` の `hooks` に統合する。Prettierの設定と除外も、アプリのルートに写す。

- 既定は確認だけ（dry-run）。反映するのは --apply を付けたときだけ。
- 既存の `settings.json` は、上書きしない。足りない規則とフックだけを足す（既存の内容は、変更も削除もしない）。
- 同名のファイルが既にあるときは、上書きせず、スキップして表示する。
- 修正履歴の担当者は、--author で人が指定した値だけを入れる。指定がなければ置き換えない。
- パッケージの導入（pnpm add、uv add）と、既存コードの一括整形は、行わない。終了後に、人が行う手順を表示する。

使い方（対象プロジェクトのルートで実行する）:
  python <スキル>/scripts/recommended-settings/apply_recommended_settings.py --items permissions,formatter-hooks
  python <スキル>/scripts/recommended-settings/apply_recommended_settings.py --items formatter-hooks --app-dir <ディレクトリ名> --apply
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# ひな形の置き場所（スキル直下の assets/optional/recommended-settings）
_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "optional" / "recommended-settings"

_ITEMS = ("permissions", "formatter-hooks")

# 整形のフックのスクリプト（ひな形 → 対象プロジェクトでの置き先）
_HOOK_SCRIPTS = {
    "formatter/_common.py": ".claude/hooks/formatter/_common.py",
    "formatter/prettier.py": ".claude/hooks/formatter/prettier.py",
    "formatter/black.py": ".claude/hooks/formatter/black.py",
}
# 整形の設定（ひな形 → アプリのルートでの置き先）
_APP_FILES = {
    "formatter/prettierrc.json": ".prettierrc",
    "formatter/prettierignore.txt": ".prettierignore",
}
# フックを起動する拡張子（スクリプト → 拡張子）。ツール（Edit、Write）ごとに、別のフックとして設定に書く
_HOOK_EXTENSIONS = {
    "black.py": ["py"],
    "prettier.py": ["ts", "vue", "mjs", "js", "json"],
}
_HOOK_TOOLS = ["Edit", "Write"]

_DATE_PLACEHOLDER = "<YYYY/MM/DD>"
_AUTHOR_PLACEHOLDER = "<会社の略称><氏名>"


def _render(text: str, app_dir: str, author: str | None, today: str) -> str:
    """ひな形の記入用の表記（アプリのルート、日付、担当者）を置き換える。担当者は、指定があるときだけ置き換える。"""
    text = text.replace("\r\n", "\n").replace("{{APP_DIR}}", app_dir).replace(_DATE_PLACEHOLDER, today)
    if author:
        text = text.replace(_AUTHOR_PLACEHOLDER, author)
    return text


def _merge_permissions(settings: dict, changes: list[str]) -> None:
    """`permissions` に、足りない規則だけを足す。既存の規則は、変更しない。"""
    recommended = json.loads((_ASSETS / "permissions.json").read_text(encoding="utf-8"))["permissions"]
    permissions = settings.setdefault("permissions", {})
    for kind in ("allow", "ask", "deny"):
        current = permissions.setdefault(kind, [])
        for rule in recommended.get(kind, []):
            if rule not in current:
                current.append(rule)
                changes.append(f"permissions.{kind} に追加: {rule}")
    # 空の配列は、書かない
    for kind in [k for k, v in permissions.items() if v == []]:
        del permissions[kind]


def _merge_hooks(settings: dict, changes: list[str]) -> None:
    """`hooks.PostToolUse` に、拡張子ごとの整形のフックを足す。同じ `if` と `command` のフックは、足さない。"""
    groups = settings.setdefault("hooks", {}).setdefault("PostToolUse", [])
    group = next((g for g in groups if g.get("matcher") == "Edit|Write"), None)
    if group is None:
        group = {"matcher": "Edit|Write", "hooks": []}
        groups.append(group)
    existing = {(h.get("if"), h.get("command")) for h in group["hooks"]}
    for script, extensions in _HOOK_EXTENSIONS.items():
        command = f'python -X utf8 "$CLAUDE_PROJECT_DIR/.claude/hooks/formatter/{script}"'
        for extension in extensions:
            for tool in _HOOK_TOOLS:
                condition = f"{tool}(*.{extension})"
                if (condition, command) not in existing:
                    group["hooks"].append({"type": "command", "if": condition, "command": command, "timeout": 60})
                    changes.append(f"hooks に追加: {condition} → {script}")


def main() -> None:
    """選んだ項目を、確認、または、対象プロジェクトに反映する。"""
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--items", required=True, help="反映する項目（カンマ区切り）: " + ", ".join(_ITEMS))
    parser.add_argument("--target", default=".", help="対象プロジェクトのルート（既定: カレントディレクトリ）")
    parser.add_argument("--app-dir", default=".", help="アプリのルート（既定: . = リポジトリの直下。サブディレクトリなら、そのディレクトリ名）")
    parser.add_argument("--author", help="修正履歴に入れる、会社の略称と氏名（人が指定する。省略時は置き換えない）")
    parser.add_argument("--date", default=date.today().strftime("%Y/%m/%d"), help="修正履歴に入れる日付（既定: 今日）")
    parser.add_argument("--apply", action="store_true", help="実際に反映する（省略時は確認だけ）")
    args = parser.parse_args()

    # 引数の検査
    items = [i.strip() for i in args.items.split(",") if i.strip()]
    unknown = [i for i in items if i not in _ITEMS]
    if unknown:
        sys.exit(f"Error: 不明な項目です: {', '.join(unknown)}（使える項目: {', '.join(_ITEMS)}）")
    target = Path(args.target).resolve()
    if not (target / ".git").exists():
        sys.exit(f"Error: Gitリポジトリのルートではありません: {target}")
    app_dir = args.app_dir.replace("\\", "/").strip("/") or "."
    app_path = (target / app_dir).resolve()
    if "formatter-hooks" in items and not app_path.is_dir():
        sys.exit(f"Error: アプリのルートが見つかりません: {app_path}")

    # ファイルを写す計画を立てる
    writes: list[tuple[Path, str]] = []
    if "formatter-hooks" in items:
        sources = [(src, target / dest) for src, dest in _HOOK_SCRIPTS.items()]
        sources += [(src, app_path / dest) for src, dest in _APP_FILES.items()]
        for src, dest in sources:
            text = _render((_ASSETS / src).read_text(encoding="utf-8"), app_dir, args.author, args.date)
            if dest.exists():
                same = dest.read_text(encoding="utf-8").replace("\r\n", "\n") == text
                print(f"  [スキップ・{'同一' if same else '内容が異なる'}] {dest.relative_to(target).as_posix()}")
            else:
                print(f"  [{'写した' if args.apply else '写す予定'}] {dest.relative_to(target).as_posix()}")
                writes.append((dest, text))

    # settings.json に統合する
    settings_path = target / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    changes: list[str] = []
    if "permissions" in items:
        _merge_permissions(settings, changes)
    if "formatter-hooks" in items:
        _merge_hooks(settings, changes)
    for change in changes:
        print(f"  [{'追加した' if args.apply else '追加予定'}] .claude/settings.json: {change}")
    if not changes:
        print("  [変更なし] .claude/settings.json")

    if not args.apply:
        print("確認だけです。反映するときは --apply を付けて、もう一度実行してください。")
        return

    # 反映する
    for dest, text in writes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")
    if changes:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(writes)} 件のファイルを写し、settings.json に {len(changes)} 件を反映しました。")

    # 人が行うことを表示する
    if any(_AUTHOR_PLACEHOLDER in text for _, text in writes):
        print("修正履歴に、記入用の表記が残っています。人が、会社の略称と氏名を書いてください。")
    if "formatter-hooks" in items:
        print("次は、人が行ってください:")
        print(f"  1. Prettierの導入: cd {app_dir}/nuxt; pnpm add -D -E prettier eslint-config-prettier")
        print("     ESLintの設定（eslint.config.mjs）の最後に、eslint-config-prettier を追加する")
        print(f"  2. Blackの導入（Pythonのサービスごと）: cd {app_dir}/backend/<サービス>; uv add --dev black")
        print("  3. 既存コードの一括整形を、別のコミットで行う（フックを有効にする前に）")
        print("  4. Claude Codeを再起動する（設定の変更は、再起動後に有効になる）")


if __name__ == "__main__":
    main()
