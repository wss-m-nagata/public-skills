# Revision History
# <YYYY/MM/DD>: <会社の略称><氏名>: 新規作成。整形のフック（prettier.py、black.py）の共通部分。
"""整形のフックの共通部分。

フックは、AIがファイルを編集したあとに実行され、標準入力から、編集の内容（JSON）を受け取る。
どのファイルの拡張子で、どのフックを起動するかは、`.claude/settings.json` の `if` に書く。

- 直せない指摘や、構文エラーが残ったときは、標準エラー出力に書き、終了コード2で終わる（AIに伝わる）。
- ツールが入っていないときは、警告だけを出して、終了コード0で終わる（作業を止めない）。
- 環境変数 HOOK_DRY_RUN=1 のときは、実行するコマンドを表示するだけで、ファイルを変更しない。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# リポジトリのルート（このファイルは .claude/hooks/formatter/ にある）
REPO = Path(__file__).resolve().parents[3]
# アプリのルート。リポジトリの直下にアプリがあるときは、"."。サブディレクトリにあるときは、そのディレクトリ名
APP = (REPO / "{{APP_DIR}}").resolve()
NUXT = APP / "nuxt"

# 整形・検査の対象にしないディレクトリ（依存パッケージ、生成物）
_EXCLUDED_DIRS = {"node_modules", ".nuxt", ".output", "dist", "cdk.out", ".venv", "__pycache__"}
_TIMEOUT_SECONDS = 60


def setup_output() -> None:
    """Windowsでも、日本語のメッセージが文字化けしないように、出力の文字コードをUTF-8にする。"""
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")


def read_target_path() -> Path | None:
    """フックの入力（JSON）から、編集されたファイルを取り出す。整形の対象でなければ、None を返す。

    対象は、アプリのルート配下にある、実在するファイルで、除外するディレクトリの外にあるものである。
    """
    # 標準入力は、文字コードを明示して読む（Windowsの既定の文字コードでは、日本語を含むJSONが壊れるため）
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        return None

    path = Path(file_path).resolve()
    if not path.is_file() or (APP != path and APP not in path.parents):
        return None
    if _EXCLUDED_DIRS & set(path.relative_to(REPO).parts):
        return None
    return path


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    """コマンドを実行し、終了コードと、出力（標準出力と標準エラー）を返す。ドライランでは、表示だけを行う。"""
    if os.environ.get("HOOK_DRY_RUN") == "1":
        print(f"[dry-run] ({cwd.relative_to(REPO) if cwd != REPO else '.'}) {' '.join(command)}")
        return 0, ""
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=_TIMEOUT_SECONDS,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def fail(message: str) -> None:
    """AIに伝えるメッセージを、標準エラー出力に書き、終了コード2で終わる。"""
    print(message, file=sys.stderr)
    sys.exit(2)


def warn_and_exit(message: str) -> None:
    """作業を止めない警告を書き、終了コード0で終わる。"""
    print(f"[formatter] {message}", file=sys.stderr)
    sys.exit(0)
