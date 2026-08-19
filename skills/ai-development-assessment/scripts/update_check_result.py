#!/usr/bin/env python3
"""
確認結果更新スクリプト。
AIは check-results.json (state) を直接編集せず、必ずこのスクリプト経由で
1件ずつ確認結果を更新する。state ファイルが未作成の場合は、テンプレートを
読み込んだ上で初回保存する。

Revision History
# 2026/08/19: 新規作成。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common

VALID_STATUSES = ["unconfirmed", "confirmed", "needs_recheck", "not_applicable"]


def update_check_result(
    check_id,
    status,
    result=None,
    evidence=None,
    notes=None,
    confirmed_by=None,
    confirmed_at=None,
    project_name=None,
    repository=None,
    evaluated_at=None,
):
    """
    1件の確認結果を更新し、state ファイルへ保存する。

    引数:
        check_id: 更新対象の check_id (例: "SPEC-01-50")
        status: unconfirmed / confirmed / needs_recheck / not_applicable のいずれか
        result: 到達条件を満たしたか(True/False)。省略時は既存値を維持する。
        evidence: 証跡文字列のリスト。省略時は既存値を維持する。
        notes: 評価根拠・所見等の自由記述。省略時は既存値を維持する。
        confirmed_by: 確認者。省略時は "Claude Code"。
        confirmed_at: 確認日時(ISO8601)。省略時は現在時刻を採番する。
        project_name: プロジェクト名。指定時のみ project.name を更新する。
        repository: リポジトリ名。指定時のみ project.repository を更新する。
        evaluated_at: 評価日。指定時のみ project.evaluated_at を更新する。

    戻り値:
        dict: 更新後の check オブジェクト
    """
    data, source = _common.load_state()

    _item, check = _common.find_check(data, check_id)
    if check is None:
        raise ValueError(
            f"check_id '{check_id}' が criteria.json / check-results.json に存在しません。"
        )

    check["status"] = status
    if result is not None:
        check["result"] = result
    if evidence is not None:
        check["evidence"] = evidence
    if notes is not None:
        check["notes"] = notes
    check["confirmed_by"] = confirmed_by or "Claude Code"
    check["confirmed_at"] = confirmed_at or datetime.now().astimezone().isoformat()

    if project_name is not None:
        data["project"]["name"] = project_name
    if repository is not None:
        data["project"]["repository"] = repository
    if evaluated_at is not None:
        data["project"]["evaluated_at"] = evaluated_at

    _common.save_state(data)

    if source == "template":
        print(
            f"state ファイルを新規作成しました: {_common.STATE_PATH}",
            file=sys.stderr,
        )

    return check


def _parse_bool(value):
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise argparse.ArgumentTypeError("--result は true か false を指定してください。")


def main():
    parser = argparse.ArgumentParser(
        description="確認結果(check-results.json)を1件更新する。"
    )
    parser.add_argument("--check-id", required=True)
    parser.add_argument("--status", required=True, choices=VALID_STATUSES)
    parser.add_argument("--result", type=_parse_bool, default=None)
    parser.add_argument(
        "--evidence", action="append", default=None, help="証跡を1件指定。複数指定可。"
    )
    parser.add_argument("--notes", default=None)
    parser.add_argument("--confirmed-by", default=None)
    parser.add_argument("--confirmed-at", default=None)
    parser.add_argument("--project-name", default=None)
    parser.add_argument("--repository", default=None)
    parser.add_argument("--evaluated-at", default=None)
    args = parser.parse_args()

    try:
        check = update_check_result(
            check_id=args.check_id,
            status=args.status,
            result=args.result,
            evidence=args.evidence,
            notes=args.notes,
            confirmed_by=args.confirmed_by,
            confirmed_at=args.confirmed_at,
            project_name=args.project_name,
            repository=args.repository,
            evaluated_at=args.evaluated_at,
        )
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(check, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
