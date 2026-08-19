#!/usr/bin/env python3
"""
整合性チェックスクリプト。
check-results.json (state) を criteria.json と突き合わせ、以下を検証する。

  - criteria_id が criteria.json に存在すること
  - check_id が重複していないこと
  - score_threshold が 25/50/75/100 の想定値であり、各評価項目で4つ揃っていること
  - confirmed なのに result が未設定になっていないこと
  - criteria_version が criteria.json と一致していること
  - 必須項目(check単位・評価項目単位)が欠けていないこと

問題があれば、AIが判断しやすいよう code / message / criteria_id / check_id を
持つエラーのリストとして返す。

Revision History
# 2026/08/19: 新規作成。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common

REQUIRED_CHECK_KEYS = [
    "check_id",
    "score_threshold",
    "question",
    "status",
    "result",
    "evidence",
    "confirmed_at",
    "confirmed_by",
    "notes",
]
REQUIRED_ITEM_KEYS = ["criteria_id", "name", "score", "checks"]
VALID_STATUSES = {"unconfirmed", "confirmed", "needs_recheck", "not_applicable"}
VALID_THRESHOLDS = {25, 50, 75, 100}


def validate_assessment():
    """
    check-results.json (state) の整合性を検証する。

    引数:
        なし

    戻り値:
        dict: {"valid": bool, "errors": [{"code":.., "message":.., "criteria_id":.., "check_id":..}, ...]}
    """
    data, _source = _common.load_state()
    criteria = _common.load_criteria()
    criteria_ids = {c["id"] for c in criteria["criteria"]}

    errors = []
    seen_check_ids = set()
    seen_criteria_ids = set()

    state_version = data.get("criteria_version")
    criteria_version = criteria.get("criteria_version")
    if state_version != criteria_version:
        errors.append(
            {
                "code": "criteria_version_mismatch",
                "message": (
                    f"check-results.json の criteria_version '{state_version}' が "
                    f"criteria.json の '{criteria_version}' と一致しません。"
                ),
            }
        )

    for item in data.get("items", []):
        criteria_id = item.get("criteria_id")
        seen_criteria_ids.add(criteria_id)

        missing_item_keys = [k for k in REQUIRED_ITEM_KEYS if k not in item]
        if missing_item_keys:
            errors.append(
                {
                    "code": "missing_item_fields",
                    "message": f"criteria_id '{criteria_id}' に必須項目が不足しています: {missing_item_keys}",
                    "criteria_id": criteria_id,
                }
            )

        if criteria_id not in criteria_ids:
            errors.append(
                {
                    "code": "unknown_criteria_id",
                    "message": f"criteria_id '{criteria_id}' は criteria.json に存在しません。",
                    "criteria_id": criteria_id,
                }
            )

        thresholds = set()
        for check in item.get("checks", []):
            check_id = check.get("check_id")

            missing_keys = [k for k in REQUIRED_CHECK_KEYS if k not in check]
            if missing_keys:
                errors.append(
                    {
                        "code": "missing_check_fields",
                        "message": f"check_id '{check_id}' に必須項目が不足しています: {missing_keys}",
                        "criteria_id": criteria_id,
                        "check_id": check_id,
                    }
                )

            if check_id in seen_check_ids:
                errors.append(
                    {
                        "code": "duplicate_check_id",
                        "message": f"check_id '{check_id}' が重複しています。",
                        "criteria_id": criteria_id,
                        "check_id": check_id,
                    }
                )
            seen_check_ids.add(check_id)

            threshold = check.get("score_threshold")
            if threshold not in VALID_THRESHOLDS:
                errors.append(
                    {
                        "code": "invalid_score_threshold",
                        "message": f"check_id '{check_id}' の score_threshold '{threshold}' は 25/50/75/100 のいずれかである必要があります。",
                        "criteria_id": criteria_id,
                        "check_id": check_id,
                    }
                )
            else:
                thresholds.add(threshold)

            status = check.get("status")
            if status not in VALID_STATUSES:
                errors.append(
                    {
                        "code": "invalid_status",
                        "message": f"check_id '{check_id}' の status '{status}' が不正です。",
                        "criteria_id": criteria_id,
                        "check_id": check_id,
                    }
                )

            if status == "confirmed" and check.get("result") is None:
                errors.append(
                    {
                        "code": "confirmed_without_result",
                        "message": f"check_id '{check_id}' は confirmed ですが result が未設定です。",
                        "criteria_id": criteria_id,
                        "check_id": check_id,
                    }
                )

        if thresholds != VALID_THRESHOLDS:
            errors.append(
                {
                    "code": "incomplete_thresholds",
                    "message": (
                        f"criteria_id '{criteria_id}' の score_threshold が 25/50/75/100 "
                        f"全て揃っていません(現在: {sorted(thresholds)})。"
                    ),
                    "criteria_id": criteria_id,
                }
            )

    missing_criteria = criteria_ids - seen_criteria_ids
    for criteria_id in sorted(missing_criteria):
        errors.append(
            {
                "code": "missing_criteria",
                "message": f"criteria_id '{criteria_id}' が check-results.json に存在しません。",
                "criteria_id": criteria_id,
            }
        )

    return {"valid": len(errors) == 0, "errors": errors}


def main():
    result = validate_assessment()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
