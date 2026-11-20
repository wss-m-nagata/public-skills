#!/usr/bin/env bash
# Revision History
# <YYYY/MM/DD>: <会社の略称><氏名>: 新規作成。
#
# scripts/ 配下のシェルスクリプトに、実行権限を付けてステージする（コミットはしない）。
# Windowsでは、ファイルの実行権限がGitに記録されないため、GitHub Actionsで実行できなくなる。
# それを防ぐため、コミットの前に、このスクリプトを実行する。
# 使い方：./scripts/stage-executable-scripts.sh

set -euo pipefail

# リポジトリのルートへ移動する
cd "$(git rev-parse --show-toplevel)"

shopt -s nullglob
FILES=(scripts/*.sh)
if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "Error: scripts/ 配下に .sh がありません" >&2
  exit 1
fi

# 実行権限を付けてステージする
git add --chmod=+x -- "${FILES[@]}"

# 結果を表示する（先頭が 100755 なら、実行権限が付いている）
git ls-files -s -- "${FILES[@]}"
