# Revision History
# <YYYY/MM/DD>: <会社の略称><氏名>: 新規作成。Prettier（とESLintの自動修正）で整形する。
"""AIが編集した `.ts`・`.vue`・`.mjs`・`.js`・`.json` を、Prettierで整形する（PostToolUse フック）。

- `nuxt/` 配下のファイルは、先に、ESLintの自動修正を行う。
  ESLintの自動修正と、Prettierは、同じファイルを書き換えるため、順に実行する（別のフックにすると、並列に動くおそれがある）。
- 整形の除外は、アプリのルートの `.prettierignore` に従う。
- 起動する拡張子は、`.claude/settings.json` の `if` で決める。
"""

import shutil

import _common

# ツールの実行ファイル（Node.jsで直接動かす。pnpmを経由しないため、速く、Windowsでも動く）
_ESLINT = _common.NUXT / "node_modules" / "eslint" / "bin" / "eslint.js"
_PRETTIER = _common.NUXT / "node_modules" / "prettier" / "bin" / "prettier.cjs"


def main() -> None:
    """編集されたファイルを、ESLintの自動修正（nuxt 配下のみ）、続けて、Prettierで整形する。"""
    _common.setup_output()
    path = _common.read_target_path()
    if path is None:
        return

    node = shutil.which("node")
    if node is None or not _PRETTIER.is_file():
        _common.warn_and_exit("node または prettier が見つからないため、整形しませんでした（nuxt で pnpm install を実行してください）")

    # nuxt 配下は、ESLintの自動修正を行う。直せない指摘は、整形のあとで、AIに伝える
    eslint_output = None
    if _common.NUXT in path.parents and _ESLINT.is_file():
        code, output = _common.run([node, str(_ESLINT), "--fix", str(path)], _common.NUXT)
        if code != 0:
            eslint_output = output

    # 整形する。除外は .prettierignore に従う
    code, output = _common.run(
        [node, str(_PRETTIER), "--write", "--ignore-path", str(_common.APP / ".prettierignore"), str(path)],
        _common.APP,
    )
    if code != 0:
        _common.fail(f"Prettierで整形できませんでした（構文エラーの可能性があります）:\n{output}")

    # 整形のあとで、ESLintの直せない指摘を伝える
    if eslint_output is not None:
        _common.fail(f"ESLintの指摘が残っています（自動では直せません）:\n{eslint_output}")


if __name__ == "__main__":
    main()
