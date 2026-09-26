# -*- coding: utf-8 -*-
"""作成例（example_process_flow.drawio）を生成するスクリプト。

架空の「お知らせ管理」を題材に、このスキルで使う描き方を一通り並べたもの。
実際の作図では、このスクリプトを雛形にして要素を差し替えていくと早い。

このファイル自体が「生成スクリプトの書き方の例」も兼ねている。
図を直すときは .drawio を手で触らず、このようなスクリプトを直して作り直す。
座標を1箇所変えるだけで全体がそろうため、描き直しが何度も発生する作業に向く。

実行:
    python assets/build_example.py

改版履歴
2026/09/04: 範囲外の枠と凡例から、WBS を前提にした言い回しを外した。
  作業計画の呼び方や有無はプロジェクトごとに違い、作例を写した図に WBS が前提として
  持ち込まれるため。行き先は「別の図の名前」で示す形にした。
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
)

from drawio_builder import (  # noqa: E402
    Diagram,
    legend_page,
    Y_SCREEN,
    Y_LAMBDA,
    Y_TABLE,
    Y_NOTE,
)

# 題材の登場人物。実際の作図では naming.md の対応表から持ってくる
T_NOTICE = "お知らせ"
T_ATTACH = "お知らせ添付ファイル"
T_PUBLISH = "公開履歴"
T_USER = "利用者マスタ"


def page_create(d):
    """① 新規作成・公開。画面遷移と処理・テーブルの関係を1枚で示す基本形。"""
    p = d.page("①新規作成・公開")
    p.title("① お知らせ管理　新規作成から公開まで（左から右へ読む）")
    p.aws_frame("AWS（本システム）", 40, 70, 2600, 900)

    # ---- 上段：画面。利用者から始めて遷移の順に横へ並べる ----
    actor = p.actor("担当者", 70, Y_SCREEN + 8)
    scr_list = p.screen("お知らせ一覧画面", 150, Y_SCREEN)
    l_new = p.lambda_box("下書きを1件作る", 463, Y_LAMBDA)
    scr_edit = p.screen("お知らせ編集画面", 892, Y_SCREEN, w=190)
    l_publish = p.lambda_box("お知らせを公開する", 1560, Y_LAMBDA)
    scr_detail = p.screen("お知らせ詳細画面", 1800, Y_SCREEN, w=190)

    p.flow(actor, scr_list, "起動")
    p.flow(
        scr_list,
        l_new,
        "① 新規作成を押す",
        exit_xy=("0.75", "1"),
        entry_xy=("0.25", "0"),
    )
    # ここは戻り線を引く。返ったIDを③の画面遷移で使うため、値の受け渡しを見せる必要がある。
    # あわせて、処理から次の画面へ直接つながないことも示している
    # （直接つなぐと「処理が画面遷移している」ように読めてしまう）
    p.back(
        l_new,
        scr_list,
        "② 採番されたIDを返す",
        exit_xy=("0.5", "0"),
        entry_xy=("1", "0.75"),
    )
    p.flow(
        scr_list,
        scr_edit,
        "③ 採番されたIDの編集画面へ移る",
        exit_xy=("1", "0.25"),
        entry_xy=("0", "0.25"),
    )
    # ここは戻り線を引かない。「お知らせを公開する」なら結果が返るのは処理名から自明で、
    # 返った値をこの先で使うわけでもない。自明な線を省くことで、上の②の1本が
    # 「値を受け渡している箇所」として目に留まるようになる
    p.flow(scr_edit, l_publish, "公開する")
    p.flow(
        scr_edit,
        scr_detail,
        "公開後の内容を見る",
        exit_xy=("1", "0.15"),
        entry_xy=("0", "0.15"),
    )

    # ---- 中段：処理。呼び出し元の画面の真下に置く ----
    l_list = p.lambda_box("お知らせの一覧を返す", 110, Y_LAMBDA, w=230)
    l_get = p.lambda_box("お知らせを1件返す", 790, Y_LAMBDA, w=230)
    l_save = p.lambda_box("お知らせを保存する", 1180, Y_LAMBDA, w=230)

    p.flow(
        scr_list, l_list, "一覧を表示する", exit_xy=("0.3", "1"), entry_xy=("0.5", "0")
    )
    p.flow(
        scr_edit,
        l_get,
        "開いたとき読み込む",
        exit_xy=("0.3", "1"),
        entry_xy=("0.5", "0"),
    )
    p.flow(
        scr_edit,
        l_save,
        "一時保存する",
        exit_xy=("0.7", "1"),
        entry_xy=("0.5", "0"),
        label_pos=0.8,
    )

    # ---- 下段：テーブル。読み取りは青の上向き、書き込みは緑の下向き ----
    f_list, _, _ = p.tables([T_NOTICE], 152, Y_TABLE, "読み取り元", kind="in")
    p.read(f_list, l_list)
    p.small(
        "一覧が使うのは題名・状態・公開日だけだが、<br>明細も同時に読んでいる。",
        110,
        Y_TABLE + 84,
        320,
    )

    f_new, _, _ = p.tables([T_NOTICE], 492, Y_TABLE, "書き込み先", kind="out")
    p.write(l_new, f_new, "追加", label_pos=-0.8)

    f_get, _, _ = p.tables([T_NOTICE, T_ATTACH], 819, Y_TABLE, "読み取り元", kind="in")
    p.read(f_get, l_get)

    f_save, _, _ = p.tables(
        [T_NOTICE, T_ATTACH], 1222, Y_TABLE, "書き込み先", kind="out"
    )
    p.write(l_save, f_save, "更新／入れ直し")

    f_pub, _, _ = p.tables(
        [T_NOTICE, T_PUBLISH], 1965, Y_TABLE, "書き込み先", kind="out"
    )
    p.write(
        l_publish,
        f_pub,
        "状態を更新／公開履歴を追記",
        exit_xy=("1", "0.75"),
        entry_xy=("0.5", "0"),
    )

    # ---- DB以外の保存先。テーブルと同じ扱いで線を引き、形だけ変える ----
    f_queue, _, _ = p.stores(["通知キュー"], 2305, Y_TABLE, "書き込み先", kind="out")
    p.write(
        l_publish,
        f_queue,
        "通知の依頼を積む",
        exit_xy=("1", "0.25"),
        entry_xy=("0.5", "0"),
    )

    # ---- 範囲外。黙って切らず、どこで整理するのかを書く ----
    p.scope_out(
        "<b>この先はこの図では扱わない</b><br>"
        "キューから先の通知メール送信は<br>「通知機能」の図で整理する。",
        2047,
        Y_SCREEN,
        340,
        84,
    )

    # ---- 未確定事項。対象の処理へ引き出し線を引く ----
    tbd = p.tbd(
        "要件「公開したお知らせの変更履歴を確認できること」に対し、現状は次の点が不足している。<br>"
        "<br>"
        "・<b>変更内容が残らない</b>。公開履歴には公開日時しか記録されず、"
        "どこを直したのかは分からない。差分を残すか。<br>"
        "・<b>下書きの変更は履歴に残らない</b>。公開したときだけ1件記録される。"
        "このタイミングでよいか。",
        790,
        Y_TABLE + 200,
        740,
        170,
    )
    p.lead(tbd, l_save, exit_xy=("1", "0"), entry_xy=("1", "0.5"))

    # ---- 吹き出し。読み手が誤解しやすい点を先回りして説明する ----
    p.callout(
        "新規作成のしくみ",
        "「新規作成」を押した時点で、DBに下書きが1件できる。<br>"
        "空の編集画面を先に開いて後から保存するのではなく、"
        "<b>先に器を作ってから編集画面へ移る</b>作りである。<br>"
        "編集画面のURLには、このとき採番されたIDを使う。",
        150,
        Y_NOTE,
        500,
        110,
    )

    p.node(
        "この図の見かた",
        "text;html=1;align=left;verticalAlign=top;fontSize=12;fontStyle=1;"
        "fontColor=#37474F;",
        1620,
        Y_NOTE,
        300,
        20,
        kind="text",
    )
    p.node(
        "・上段が画面、中段がその画面から呼ばれる処理、下段がテーブル。左から右へ読む。<br>"
        "・テーブルへの<b>書き込みは下向きの緑</b>、テーブルからの<b>読み取りは上向きの青</b>。<br>"
        "・丸数字は「新規作成を押してから編集画面が開くまで」の順序を示す。<br>"
        "・同じテーブルが複数の処理に出てくる。処理ごとに流れを追えるよう重複して描いた。",
        "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFDE7;strokeColor=#FBC02D;"
        "fontColor=#5D4037;fontSize=11;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;",
        1620,
        Y_NOTE + 25,
        700,
        110,
        kind="note",
    )
    return p


def page_delete(d):
    """② 削除。連鎖削除の示し方と、権限の扱いを含む例。"""
    p = d.page("②削除")
    p.title("② 削除（物理削除）")
    p.aws_frame("AWS（本システム）", 40, 70, 1900, 700)

    actor = p.actor("担当者", 70, Y_SCREEN + 8)
    scr_list = p.screen("お知らせ一覧画面", 150, Y_SCREEN)
    scr_detail = p.screen("お知らせ詳細画面", 390, Y_SCREEN)
    l_del = p.lambda_box("お知らせを物理削除する", 640, Y_SCREEN, w=240)

    p.flow(actor, scr_list, "起動")
    p.flow(scr_list, scr_detail, "開く")
    p.flow(scr_detail, l_del, "① 削除")
    p.flow(
        scr_list,
        l_del,
        "① 削除",
        exit_xy=("0.5", "1"),
        entry_xy=("0.2", "0"),
        label_pos=-0.6,
    )

    f_del, w_del, _ = p.tables([T_NOTICE], 700, Y_TABLE, "② 削除する", kind="out")
    p.delete(l_del, f_del, "行を削除する")

    f_cas, _, _ = p.tables(
        [T_ATTACH, T_PUBLISH],
        700 + w_del + 60,
        Y_TABLE,
        "③ 外部キーのCASCADEで一緒に消える",
        kind="out",
    )
    p.cascade(f_del, f_cas, exit_xy=("1", "0.5"), entry_xy=("0", "0.5"))

    f_user, _, _ = p.tables([T_USER], 1450, Y_TABLE, "権限判定", kind="in")
    p.read(
        f_user, l_del, "ロールを判定する", exit_xy=("0.5", "0"), entry_xy=("1", "0.5")
    )

    p.note(
        "削除の性質",
        "・論理削除ではなく物理削除。行そのものが消えるため元に戻せない。<br>"
        "・添付ファイルと公開履歴は外部キーのCASCADEで自動的に消えるため、"
        "処理は本体の1行だけを削除する。<br>"
        "・削除できるのは管理者のみ。すべての処理の入口でロールを判定する。",
        150,
        Y_NOTE - 80,
        1000,
        80,
    )
    return p


def main():
    d = Diagram(page_w=2700, page_h=1100)
    page_create(d)
    page_delete(d)
    legend_page(
        d,
        schemas=[("お知らせスキーマ", "notice"), ("共通データ基盤スキーマ", "common")],
        tables=[
            (T_NOTICE, "notice.notice"),
            (T_ATTACH, "notice.notice_attachment"),
            (T_PUBLISH, "notice.publish_history"),
            (T_USER, "common.user_master"),
        ],
        scope="・「お知らせ管理」を対象とする。<br>"
        "・公開後の通知メール送信は、この操作より後の工程のため含めない（「通知機能」の図）。<br>"
        "・現行の実装（As-Is）をそのまま図にしている。",
    )

    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "example_process_flow.drawio"
    )
    d.save(out)
    print("生成しました:", out)


if __name__ == "__main__":
    main()
