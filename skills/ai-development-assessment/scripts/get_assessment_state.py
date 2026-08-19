#!/usr/bin/env python3
"""
評価状態取得スクリプト。
state ファイル(.agents/state/ai-development-assessment/check-results.json)が
存在すればそれを、存在しなければテンプレート(assets/check-results.json)を
そのまま返す。取得しただけでは state ファイルを新規作成しない。

Revision History
# 2026/08/19: 新規作成。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common


def get_assessment_state():
    """
    現在の評価状態を取得する。

    引数:
        なし

    戻り値:
        dict: {"source": "state"|"template", "data": {...}}
            source が "state" なら保存済みの確認結果、
            "template" なら未着手でテンプレートをそのまま返している。
    """
    data, source = _common.load_state()
    return {"source": source, "data": data}


def main():
    parser = argparse.ArgumentParser(
        description="評価状態(check-results.json)を取得する。"
    )
    parser.parse_args()
    result = get_assessment_state()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
