# -*- coding: utf-8 -*-
"""design-doc-revision の共通部品（設定の読み込み・ハッシュ・パスの対応）。"""

import hashlib
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]

# 設定ファイル（プロジェクトルート直下からの相対パス）。スキル自身のディレクトリには置かない
SETTINGS_RELATIVE = Path(".agents") / "config" / "design-doc-revision" / "settings.md"
# 設定ファイルの場所を、直接指定するときの環境変数
SETTINGS_ENV = "DESIGN_DOC_REVISION_SETTINGS"

# 設定の「| 項目 | 値 |」の表で、スクリプトが読む項目
KEY_ROOT = "設計書のルート"
KEY_SOURCE = "正本の場所"
KEY_REVIEW = "レビュー用の置き場の場所"
KEY_LOCAL = "手元の作業フォルダ"
KEY_RECORD = "取得の記録ファイル名"
KEY_KEEP = "構造を保つフォルダ"
KEY_RECIPIENT = "レビュー担当者の呼び名"
REQUIRED_KEYS = (KEY_ROOT, KEY_SOURCE, KEY_REVIEW, KEY_RECORD, KEY_RECIPIENT)


def ensure_utf8():
    """日本語の出力が文字化けしないようにする。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def find_settings(start=None):
    """設定ファイル（.agents/config/design-doc-revision/settings.md）を探す。

    環境変数 DESIGN_DOC_REVISION_SETTINGS があれば、それを使う。
    無ければ、start（省略時は、現在のフォルダ）から親へたどって探す。

    Args:
        start (str | Path | None): 探し始めるフォルダ。

    Returns:
        Path: 設定ファイルのパス。

    Raises:
        FileNotFoundError: 見つからないとき。
    """
    # 環境変数での指定
    env = os.environ.get(SETTINGS_ENV)
    if env:
        path = Path(env)
        if not path.is_file():
            raise FileNotFoundError(
                f"{SETTINGS_ENV} が指す設定ファイルがありません: {path}"
            )
        return path
    # 親へたどって探す（start、現在のフォルダの順）
    bases = ([Path(start).resolve()] if start else []) + [Path.cwd().resolve()]
    for base in bases:
        for folder in [base, *base.parents]:
            candidate = folder / SETTINGS_RELATIVE
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        f"設定ファイルが見つかりません: {SETTINGS_RELATIVE}（references/interview.md に従って作成する）"
    )


def read_settings(start=None):
    """設定ファイルの「| 項目 | 値 |」の表を読み、項目名から値への辞書を返す。

    値の前後の空白と、バッククォートは取り除く。
    見出しの行（項目 | 値）と、区切りの行は読み飛ばす。
    必須の項目が無い、または、記入されていない（< で始まる）ときは、止める。

    Args:
        start (str | Path | None): 設定ファイルを探し始めるフォルダ（作業フォルダなど）。

    Returns:
        dict[str, str]: 項目名 → 値。
    """
    path = find_settings(start)
    settings = {}
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in text.strip("|").split("|")]
        # 表の見出し（項目 | 値）で、読み取りの対象の表かを決める
        if len(cells) >= 2 and cells[0] == "項目" and cells[1] == "値":
            in_table = True
            continue
        if not in_table or set(text) <= set("|-: "):
            continue
        if len(cells) >= 2:
            settings[cells[0]] = cells[1].strip("`").strip()
    # 必須の項目の確認
    bad = [
        k for k in REQUIRED_KEYS if not settings.get(k) or settings[k].startswith("<")
    ]
    if bad:
        raise ValueError(f"設定が未記入です（{path}）: " + "、".join(bad))
    settings["_path"] = str(path)
    return settings


def load_config(start=None):
    """設定から、スクリプトが使う形（場所・名前）の辞書を作る。

    Returns:
        dict: design_root（設計書のルート）、source_dir（正本。ルートからの相対）、
              review_dir（レビュー用の置き場。ルートからの相対）、record_file（取得の記録）、
              recipient（レビュー担当者の呼び名）、keep（構造を保つフォルダの一覧。空なら、すべて保つ）。
    """
    s = read_settings(start)
    keep_text = s.get(KEY_KEEP, "")
    keep = (
        []
        if keep_text in ("", "なし")
        else [k.strip() for k in keep_text.replace("、", ",").split(",") if k.strip()]
    )
    return {
        "design_root": s[KEY_ROOT],
        "source_dir": s[KEY_SOURCE],
        "review_dir": s[KEY_REVIEW],
        "record_file": s[KEY_RECORD],
        "recipient": s[KEY_RECIPIENT],
        "keep": keep,
    }


def sha256(path):
    """ファイルの SHA-256（大文字16進）を返す。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def local_relative(source_path, config=None):
    """正本の中の相対パスを、作業フォルダ（手元・レビュー用の置き場）の中の相対パスに直す。

    設定の「構造を保つフォルダ」の下は、同じ構成で置く（空のときは、すべて同じ構成で置く）。
    それ以外は、作業フォルダの直下にファイル名だけで置く。
    戻り値は、「/」区切り。
    """
    config = config or load_config()
    parts = str(source_path).replace(chr(92), "/").strip("/").split("/")
    if not config["keep"] or parts[0] in config["keep"]:
        return "/".join(parts)
    return parts[-1]


def top_folder(source_path):
    """正本の中の、先頭のフォルダ名（旧版を移す old の親を説明するときに使う）。"""
    return str(source_path).replace(chr(92), "/").strip("/").split("/")[0]
