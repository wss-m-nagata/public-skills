// 修正履歴
// 2026/11/11: 画像と座標の同時取得を検証する。
import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { captureUiLayout } from '../scripts/capture_ui_layout.mjs'

// 撮影前後の計測値を指定できるPlaywright互換のテスト用ページ。
function fakePage(moving = false) {
  let calls = 0
  const target = {
    count: async () => 1,
    isVisible: async () => true,
    scrollIntoViewIfNeeded: async () => {},
    evaluate: async () => ({ rect: [moving && calls++ ? 10 : 0, 0, 200, 100], elements: [{ id: 'E-01', x: 0.1, y: 0.2, width: 0.3, height: 0.4 }] }),
    screenshot: async () => Buffer.from('image'),
  }
  return { addStyleTag: async () => ({ evaluate: async () => {} }), evaluate: async () => {}, locator: () => target }
}

test('撮影画像と注釈用JSONを同じ位置から出力する', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'capture-ui-'))
  try {
    const options = { root: '#dialog', elements: [{ id: 'E-01', selector: 'h2' }], frameCell: 'C8', imagePath: join(dir, 'image.png'), definitionPath: join(dir, 'layout.json') }
    await captureUiLayout(fakePage(), options)
    const definition = JSON.parse(await readFile(options.definitionPath, 'utf8'))
    assert.equal(definition.layouts[0].image, 'image.png')
    assert.equal(definition.layouts[0].elements[0].x, 0.1)
    assert.equal((await readFile(options.imagePath)).toString(), 'image')
  } finally { await rm(dir, { recursive: true, force: true }) }
})

test('撮影の前後で位置が変わる場合は出力しない', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'capture-ui-'))
  try {
    const options = { root: '#dialog', elements: [{ id: 'E-01', selector: 'h2' }], frameCell: 'C8', imagePath: join(dir, 'image.png'), definitionPath: join(dir, 'layout.json') }
    await assert.rejects(captureUiLayout(fakePage(true), options), /画面が動きました/)
    await assert.rejects(readFile(options.imagePath), { code: 'ENOENT' })
  } finally { await rm(dir, { recursive: true, force: true }) }
})
