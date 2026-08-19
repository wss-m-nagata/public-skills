#!/usr/bin/env python3
"""
点数計算スクリプト。
各評価項目について、confirmed かつ result=true となった到達条件のうち、
最も高い score_threshold を評価点とする。25点条件も満たさない場合は0点。
配下の到達条件が全て not_applicable の評価項目のみ、採点対象外として扱う。
点数の判定自体はAIに任せず、保存された確認結果をもとに機械的に決定する。

Revision History
# 2026/08/19: 新規作成。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common


def calculate_scores(save=True):
    """
    各評価項目のスコアを算出する。

    引数:
        save: True の場合、算出したスコアを state ファイルの items[].score へ
            反映して保存する。

    戻り値:
        dict: {"items": [{"criteria_id":.., "name":.., "score": int|None, "applicable": bool}, ...]}
            applicable が False の項目は、配下の到達条件が全て not_applicable の
            採点対象外の項目。score が None なのは applicable が False の場合のみで、
            それ以外は必ず 0/25/50/75/100 のいずれかになる。
    """
    data, _source = _common.load_state()
    results = []

    for item in data.get("items", []):
        checks = item.get("checks", [])
        statuses = {c.get("status") for c in checks}

        if statuses and statuses == {"not_applicable"}:
            item["score"] = None
            results.append(
                {
                    "criteria_id": item["criteria_id"],
                    "name": item["name"],
                    "score": None,
                    "applicable": False,
                }
            )
            continue

        achieved = [
            c["score_threshold"]
            for c in checks
            if c.get("status") == "confirmed" and c.get("result") is True
        ]
        score = max(achieved) if achieved else 0
        item["score"] = score
        results.append(
            {
                "criteria_id": item["criteria_id"],
                "name": item["name"],
                "score": score,
                "applicable": True,
            }
        )

    if save:
        _common.save_state(data)

    return {"items": results}


def main():
    result = calculate_scores()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
