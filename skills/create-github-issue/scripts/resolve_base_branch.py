#!/usr/bin/env python3
"""起点ブランチの判定スクリプト。

作業ブランチを切る起点を、リポジトリのブランチ状態と規則から「提案」する。
読み取り専用の git コマンドしか使わない。自動で確定はせず、確認の要否を JSON で返す。
確認を取るかどうかの判断と提示は、呼び出し元のエージェントが行う。

規則の決め方（上にあるほど優先）:
  1. 引数（--pattern・--default・--remote）
  2. 設定ファイル .agents/config/create-github-issue/settings.md の「項目 | 値」の表
  3. 組み込みの既定
       規則    : ^(main|master|develop|development)$
       既定の起点: 取り込み先の HEAD が指すブランチ。無ければ main・master・develop・development の順で探す
       リモート名: origin

使い方:
    python resolve_base_branch.py
    python resolve_base_branch.py --pattern "^release/.+$" --default main --remote origin
    python resolve_base_branch.py --settings path/to/settings.md

出力 JSON:
    current_branch           今のブランチ
    rule_pattern             使った規則（正規表現）
    rule_source              規則の出どころ（argument / settings / builtin）
    default_branch           既定の起点（無ければ null）
    default_source           既定の起点の出どころ（argument / settings / remote_head / builtin_search / none）
    candidate_branches       規則に合うブランチの一覧（ローカルとリモートの合算、重複なし）
    recommended_base_branch  提案する起点（決められないときは null）
    needs_user_confirmation  ユーザーに確認が要るか
    reason                   判定の理由
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Windows のコンソールは UTF-8 以外のことがあり、日本語の出力が化けるため、UTF-8 に切り替える。
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding is None or _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8")

# 設定ファイルの場所（プロジェクトルートからの相対パス）。
SETTINGS_RELATIVE_PATH = (
    Path(".agents") / "config" / "create-github-issue" / "settings.md"
)

# 設定の表の項目名。
KEY_PATTERN = "起点ブランチの規則（正規表現）"
KEY_DEFAULT = "既定の起点ブランチ"
KEY_REMOTE = "リモート名"

# 組み込みの既定。
BUILTIN_PATTERN = r"^(main|master|develop|development)$"
BUILTIN_REMOTE = "origin"
BUILTIN_SEARCH_ORDER = ["main", "master", "develop", "development"]


def _split_row(line):
    """表の1行を、エスケープされていない `|` で区切ってセルのリストにする。"""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = re.split(r"(?<!\\)\|", body)
    return [c.replace("\\|", "|").strip() for c in cells]


def _strip_code(value):
    """値の前後のバッククォートと空白を外す。"""
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value


def _find_settings(start):
    """今のディレクトリから親方向にたどり、設定ファイルを探す。無ければ None。"""
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        path = candidate / SETTINGS_RELATIVE_PATH
        if path.is_file():
            return path
    return None


def read_settings(path=None):
    """設定ファイルの「| 項目 | 値 |」の表を読み、{項目: 値} を返す。

    path が None のときは、今のディレクトリから親方向に設定ファイルを探す。
    ファイルが無いときは空の辞書を返す。
    値が `<` で始まる（記入前のひな形の値）ものは、未設定として読み飛ばす。
    """
    target = Path(path) if path else _find_settings(Path.cwd())
    if target is None or not target.is_file():
        return {}

    settings = {}
    in_table = False
    with target.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.lstrip().startswith("|"):
                in_table = False
                continue
            cells = _split_row(line)
            # 見出し行で、項目と値の表かどうかを判定する。
            if not in_table:
                in_table = len(cells) == 2 and cells[0] == "項目" and cells[1] == "値"
                continue
            # 区切り行（---）は読み飛ばす。
            if len(cells) == 2 and set(cells[0] + cells[1]) <= set("-: "):
                continue
            if len(cells) == 2:
                value = _strip_code(cells[1])
                if value and not value.startswith("<"):
                    settings[cells[0]] = value
    return settings


def _run_git(args):
    """git を実行し、標準出力を行のリストで返す。失敗したときは空のリストを返す。"""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _all_branches(remote):
    """ローカルとリモートのブランチ名を、重複なく集める（リモートは接頭辞を外す）。"""
    names = set(
        _run_git(["for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads"])
    )
    remote_ref = f"refs/remotes/{remote}"
    strip = remote_ref.count("/") + 1
    for name in _run_git(
        ["for-each-ref", f"--format=%(refname:lstrip={strip})", remote_ref]
    ):
        if name != "HEAD":
            names.add(name)
    return names


def _remote_head(remote):
    """取り込み先の HEAD が指すブランチ名を返す。分からなければ None。"""
    lines = _run_git(["symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"])
    if lines and lines[0].startswith(f"{remote}/"):
        return lines[0][len(remote) + 1 :]
    return None


def resolve(pattern_text, default_branch, remote):
    """ブランチ状態と規則から、起点の提案と確認の要否を決める。

    pattern_text   : 規則（正規表現の文字列）
    default_branch : 既定の起点。None なら、取り込み先の HEAD、組み込みの探索順の順に決める
    remote         : リモート名
    戻り値         : 出力用の辞書（default_source は呼び出し側で足す）
    """
    pattern = re.compile(pattern_text)

    # 今のブランチと、全ブランチを集める。
    lines = _run_git(["branch", "--show-current"])
    current = lines[0] if lines else ""
    branches = _all_branches(remote)
    candidates = sorted(b for b in branches if pattern.match(b))

    # 既定の起点を決める（引数・設定で指定が無いとき）。
    default_source = "argument_or_settings"
    if default_branch is None:
        head = _remote_head(remote)
        if head and head in branches:
            default_branch, default_source = head, "remote_head"
        else:
            found = [b for b in BUILTIN_SEARCH_ORDER if b in branches]
            if found:
                default_branch, default_source = found[0], "builtin_search"
            else:
                default_source = "none"

    result = {
        "current_branch": current,
        "default_branch": default_branch,
        "default_source": default_source,
        "candidate_branches": candidates,
    }

    # 今のブランチが規則に合うなら、確認なしでそれを起点にする。
    if pattern.match(current):
        result.update(
            recommended_base_branch=current,
            needs_user_confirmation=False,
            reason="今のブランチが規則に合うため、これを起点とする。",
        )
        return result

    # 規則に合うブランチが無いときは、既定の起点を候補にする。
    if not candidates:
        if default_branch and default_branch in branches:
            result.update(
                recommended_base_branch=default_branch,
                needs_user_confirmation=True,
                reason=f"規則に合うブランチが無い。既定の起点 {default_branch} を起点にしてよいか、ユーザーに確認すること。",
            )
        else:
            result.update(
                recommended_base_branch=None,
                needs_user_confirmation=True,
                reason="規則に合うブランチも、使える既定の起点も無い。起点をユーザーに聞くこと。",
            )
        return result

    # 1つだけ合うときは、それを候補にして確認する。
    if len(candidates) == 1:
        result.update(
            recommended_base_branch=candidates[0],
            needs_user_confirmation=True,
            reason="規則に合うブランチが1つ見つかった。これを起点にしてよいか、ユーザーに確認すること。",
        )
        return result

    # 複数あるとき：既定の起点が候補に入っていれば提案し、無ければ自動で選ばない。
    if default_branch in candidates:
        result.update(
            recommended_base_branch=default_branch,
            needs_user_confirmation=True,
            reason=f"規則に合うブランチが複数ある。既定の起点 {default_branch} を提案する。候補を見せて、どれを起点にするか、ユーザーに確認すること。",
        )
    else:
        result.update(
            recommended_base_branch=None,
            needs_user_confirmation=True,
            reason="規則に合うブランチが複数ある。候補を選択肢として見せ、どれを起点にするか、ユーザーに選んでもらうこと（自動で選ばない）。",
        )
    return result


def main():
    """引数と設定を読み、判定結果を JSON で出力する。"""
    parser = argparse.ArgumentParser(
        description="作業ブランチの起点ブランチを提案する。"
    )
    parser.add_argument("--pattern", help="起点にできるブランチ名の規則（正規表現）")
    parser.add_argument(
        "--default", help="規則に合うブランチが無いときの、既定の起点ブランチ"
    )
    parser.add_argument("--remote", help="リモート名")
    parser.add_argument(
        "--settings",
        help="設定ファイルのパス（省略時は、今のディレクトリから親方向に探す）",
    )
    args = parser.parse_args()

    settings = read_settings(args.settings)

    # 引数、設定、組み込みの既定の順に、規則を決める。
    if args.pattern:
        pattern_text, rule_source = args.pattern, "argument"
    elif KEY_PATTERN in settings:
        pattern_text, rule_source = settings[KEY_PATTERN], "settings"
    else:
        pattern_text, rule_source = BUILTIN_PATTERN, "builtin"
    default_branch = args.default or settings.get(KEY_DEFAULT)
    remote = args.remote or settings.get(KEY_REMOTE) or BUILTIN_REMOTE

    try:
        result = resolve(pattern_text, default_branch, remote)
    except re.error as exc:
        print(f"規則（正規表現）が正しくない: {pattern_text} ({exc})", file=sys.stderr)
        sys.exit(1)

    # 出どころを、出力に添える。
    if result["default_source"] == "argument_or_settings":
        result["default_source"] = "argument" if args.default else "settings"
    output = {
        "current_branch": result["current_branch"],
        "rule_pattern": pattern_text,
        "rule_source": rule_source,
        "default_branch": result["default_branch"],
        "default_source": result["default_source"],
        "candidate_branches": result["candidate_branches"],
        "recommended_base_branch": result["recommended_base_branch"],
        "needs_user_confirmation": result["needs_user_confirmation"],
        "reason": result["reason"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
