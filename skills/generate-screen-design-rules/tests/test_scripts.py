# 修正履歴
# 2026/10/28: テンプレート処理と色見本の動作確認を追加。

"""スキルの生成補助スクリプトを一時ディレクトリで検証する。"""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'
LEDGER = 'デザインシステム管理台帳.md'
HEADER = '# 台帳\n\n| 規約 | 状態 | 確認 | 出典 | 参照 |\n|---|---|---|---|---|\n'


class ScreenScriptTest(unittest.TestCase):
    """生成先と管理台帳を壊さないことを確認する。"""

    def setUp(self):
        """テスト用の出力先を作る。"""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / LEDGER).write_text(HEADER, encoding='utf-8')

    def _run(self, script, *arguments):
        """同じPythonで対象スクリプトを実行する。"""
        return subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPTS / script), *map(str, arguments)], capture_output=True, text=True, encoding='utf-8')

    def test_extract_and_repeat(self):
        """管理情報を移し、本文と確定済みの別項目を保持する。"""
        ledger = self.root / LEDGER
        ledger.write_text(HEADER + '| other.md / 確定 | 確定 | 手動変更 | DADS | URL |\n', encoding='utf-8')
        source = self.root / 'layout.md'
        source.write_text('# 画面\n\n## 1. 余白\n\n<!-- template-only:start -->\n- **状態:** 暫定\n- **出典:** DADS\n<!-- template-only:end -->\n\n### 規約\n\n8pxを使う。\n', encoding='utf-8')
        self.assertEqual(self._run('extract_template_metadata.py', self.root).returncode, 0)
        self.assertNotIn('template-only', source.read_text(encoding='utf-8'))
        self.assertIn('8pxを使う。', source.read_text(encoding='utf-8'))
        result = ledger.read_text(encoding='utf-8')
        self.assertIn('other.md / 確定 | 確定 | 手動変更', result)
        self.assertIn('layout.md / 1. 余白 | 暫定', result)
        self.assertEqual(self._run('extract_template_metadata.py', self.root).returncode, 0)
        self.assertEqual(result, ledger.read_text(encoding='utf-8'))

    def test_conflict_and_bad_marker_do_not_write(self):
        """同一対象や不完全なマーカーを検出した場合は書き換えない。"""
        ledger = self.root / LEDGER
        ledger.write_text(HEADER + '| layout.md / 1. 余白 | 確定 | 手動変更 | DADS | URL |\n', encoding='utf-8')
        source = self.root / 'layout.md'
        content = '## 1. 余白\n<!-- template-only:start -->\n- **状態:** 暫定\n<!-- template-only:end -->\n'
        source.write_text(content, encoding='utf-8')
        before = ledger.read_text(encoding='utf-8')
        self.assertNotEqual(self._run('extract_template_metadata.py', self.root).returncode, 0)
        self.assertEqual(before, ledger.read_text(encoding='utf-8'))
        self.assertEqual(content, source.read_text(encoding='utf-8'))
        source.write_text(content.replace('<!-- template-only:end -->\n', ''), encoding='utf-8')
        self.assertNotEqual(self._run('extract_template_metadata.py', self.root).returncode, 0)
        self.assertEqual(before, ledger.read_text(encoding='utf-8'))

    def test_swatch_and_check(self):
        """色見本の生成と色値の不一致を検証する。"""
        swatch = self.root / 'color.svg'
        self.assertEqual(self._run('swatch.py', swatch, '#ffffff').returncode, 0)
        self.assertNotEqual(self._run('swatch.py', swatch, '#000000').returncode, 0)
        source = self.root / 'colors.md'
        source.write_text('| 色 | ![白](./color.svg) | `#ffffff` |\n', encoding='utf-8')
        self.assertEqual(self._run('check_output.py', self.root).returncode, 0)
        source.write_text('| 色 | ![黒](./color.svg) | `#000000` |\n', encoding='utf-8')
        self.assertNotEqual(self._run('check_output.py', self.root).returncode, 0)
        self.assertNotEqual(self._run('swatch.py', self.root / 'transparent.svg', '#000000', '--opacity', '0.5').returncode, 0)

    def test_rejects_values_and_explanation_inside_marker(self):
        """規約の値や説明が誤って囲まれている場合、何も削除しない。"""
        ledger = self.root / LEDGER
        source = self.root / 'foundations.md'
        for specification in ('- **値:** `Noto Sans JP`', '文字の読みやすさを確保します。', '| 項目 | 値 |'):
            content = '## 1. 文字\n<!-- template-only:start -->\n- **状態:** 暫定\n' + specification + '\n<!-- template-only:end -->\n'
            source.write_text(content, encoding='utf-8')
            before = ledger.read_text(encoding='utf-8')
            self.assertNotEqual(self._run('extract_template_metadata.py', self.root).returncode, 0)
            self.assertEqual(content, source.read_text(encoding='utf-8'))
            self.assertEqual(before, ledger.read_text(encoding='utf-8'))

    def test_ledger_heading_with_slashes(self):
        """見出しに区切り文字が含まれる場合も台帳との対応を確認する。"""
        (self.root / 'layout.md').write_text('## 1. Dialog / Modal\n', encoding='utf-8')
        (self.root / LEDGER).write_text(HEADER + '| layout.md / 1. Dialog / Modal | 確定 |  |  |  |\n', encoding='utf-8')
        self.assertEqual(self._run('check_output.py', self.root).returncode, 0)
        (self.root / 'layout.md').write_text('## 1. 別の見出し\n', encoding='utf-8')
        self.assertNotEqual(self._run('check_output.py', self.root).returncode, 0)

    def test_external_issue_ledger_is_not_reported_empty(self):
        """外部管理の台帳は空の確認事項として扱わない。"""
        ledger = self.root / LEDGER
        ledger.write_text('# 台帳\n\n| 規約 | 出典 | 参照 |\n|---|---|---|\n', encoding='utf-8')
        result = self._run('list_pending.py', ledger)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('確認待ちの項目はありません', result.stdout)
        ledger.write_text(HEADER + '| layout.md / 余白 | 暫定 | 内容 | DADS | URL |\n', encoding='utf-8')
        result = self._run('list_pending.py', ledger)
        self.assertEqual(result.returncode, 0)
        self.assertIn('暫定', result.stdout)

    def test_directory_link_and_composite_swatch(self):
        """ディレクトリを認識し、複合色は人による確認として知らせる。"""
        (self.root / 'icons').mkdir()
        (self.root / 'sample.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
        (self.root / 'colors.md').write_text('[アイコン](./icons/)\n| ![見本](./sample.svg) | #000000 と #ffffff |\n', encoding='utf-8')
        result = self._run('check_output.py', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('手動確認', result.stderr)

    def test_full_template_preserves_values_and_explanations(self):
        """全テンプレートの抽出後も、値・規約・説明が残る。"""
        template = SCRIPTS.parent / 'assets' / 'screen-design-rules-template'
        output = self.root / 'output'
        shutil.copytree(template, output)
        extraction = self._run('extract_template_metadata.py', output)
        self.assertEqual(extraction.returncode, 0, extraction.stderr)
        foundations = (output / 'foundations.md').read_text(encoding='utf-8')
        layout = (output / 'layout.md').read_text(encoding='utf-8')
        components = (output / 'components.md').read_text(encoding='utf-8')
        self.assertIn('- **基本書体:** Noto Sans JP。', foundations)
        self.assertIn('- **等幅書体:** Noto Sans Mono。', foundations)
        self.assertIn('想定する画面の幅は、横に長い画面', foundations)
        self.assertIn('横に長い画面（表、ツリーなど）が多い場合', layout)
        self.assertIn('| `[例: Tree]` | `[理由]` | `[Radix / TanStack / 独自等]` |', components)
        self.assertIn('出典: DADS', (output / LEDGER).read_text(encoding='utf-8'))
        check = self._run('check_output.py', output)
        self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == '__main__':
    unittest.main()
