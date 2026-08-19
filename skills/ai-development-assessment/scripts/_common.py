#!/usr/bin/env python3
"""
ai-development-assessment Skill の各スクリプトが共有するパス解決・JSON入出力のヘルパー。
Skill内部専用のため、他のSkillやスクリプトから直接importしない。

Revision History
# 2026/08/19: 新規作成。
"""

import json
import sys
from pathlib import Path

# Windowsではコンソールの既定エンコーディングがUTF-8でない場合があり、
# 標準出力へ日本語のJSONをそのまま書くと文字化けする。ここで一括して矯正する。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# このファイルの場所: <repo_root>/skills/ai-development-assessment/scripts/_common.py
SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parents[1]

CRITERIA_PATH = SKILL_DIR / "references" / "criteria.json"
TEMPLATE_STATE_PATH = SKILL_DIR / "assets" / "check-results.json"
STATE_PATH = (
    REPO_ROOT / ".agents" / "state" / "ai-development-assessment" / "check-results.json"
)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_state():
    """
    現在の評価状態を取得する。

    引数:
        なし

    戻り値:
        tuple[dict, str]: (評価状態のdict, "state"|"template")
            state ファイルが存在すればそれを、なければテンプレートをそのまま返す。
            呼び出しただけでは state ファイルを新規作成しない。
    """
    if STATE_PATH.exists():
        return _load_json(STATE_PATH), "state"
    return _load_json(TEMPLATE_STATE_PATH), "template"


def save_state(data):
    """評価状態を state ファイルへ保存する(初回は新規作成)。"""
    _save_json(STATE_PATH, data)


def load_criteria():
    """評価基準(criteria.json)を読み込む。"""
    return _load_json(CRITERIA_PATH)


def find_check(data, check_id):
    """
    check_id から、対応する item(criteria単位) と check(到達条件単位) を探す。

    引数:
        data: load_state() で得た評価状態のdict
        check_id: 例 "SPEC-01-50"

    戻り値:
        tuple[dict|None, dict|None]: (item, check)。見つからなければ (None, None)。
    """
    for item in data.get("items", []):
        for check in item.get("checks", []):
            if check.get("check_id") == check_id:
                return item, check
    return None, None
