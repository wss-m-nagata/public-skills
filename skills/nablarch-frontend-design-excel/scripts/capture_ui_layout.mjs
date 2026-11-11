// 修正履歴
// 2026/11/11: 画面画像と要素の相対座標を同じ表示状態から取得する。
import { writeFile } from 'node:fs/promises'
import { basename, dirname, resolve } from 'node:path'

/** 表示を安定させ、PlaywrightのページからExcel注釈用の画像と定義を作る。 */
export async function captureUiLayout(page, { root, elements, frameCell, imagePath, definitionPath }) {
  if (!/^C[1-9]\d*$/.test(frameCell) || !elements.length) throw new Error('枠セルと要素を指定してください。')
  const ids = new Set(elements.map(element => element.id))
  if (ids.size !== elements.length || elements.some(element => !/^E-\d+$/.test(element.id))) throw new Error('要素IDは重複しないE-番号で指定してください。')
  const image = resolve(imagePath)
  const definition = resolve(definitionPath)
  if (dirname(image) !== dirname(definition)) throw new Error('画像と定義JSONは同じディレクトリに置いてください。')
  const style = await page.addStyleTag({ content: '*, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }' })
  try {
    await page.evaluate(() => new Promise(resolveFrame => requestAnimationFrame(() => requestAnimationFrame(resolveFrame))))
    const target = page.locator(root)
    if (await target.count() !== 1 || !(await target.isVisible())) throw new Error('撮影対象は表示中の要素を一つ指定してください。')
    await target.scrollIntoViewIfNeeded()
    const measure = async () => target.evaluate((container, specs) => {
      const rect = container.getBoundingClientRect()
      const list = specs.map(({ id, selector }) => {
        const matches = container.querySelectorAll(selector)
        if (matches.length !== 1) throw new Error(`${id}: 要素を一つ指定してください。`)
        const item = matches[0].getBoundingClientRect()
        if (item.width <= 0 || item.height <= 0 || item.left < rect.left || item.top < rect.top || item.right > rect.right || item.bottom > rect.bottom) throw new Error(`${id}: 撮影範囲内の表示要素を指定してください。`)
        return { id, x: (item.left - rect.left) / rect.width, y: (item.top - rect.top) / rect.height, width: item.width / rect.width, height: item.height / rect.height }
      })
      return { rect: [rect.x, rect.y, rect.width, rect.height], elements: list }
    }, elements)
    const before = await measure()
    const pixels = await target.screenshot({ animations: 'disabled', scale: 'css' })
    const after = await measure()
    const numbers = state => [...state.rect, ...state.elements.flatMap(item => [item.x, item.y, item.width, item.height])]
    if (numbers(before).some((value, index) => Math.abs(value - numbers(after)[index]) > 0.001)) throw new Error('撮影前後で画面が動きました。表示が安定してから再実行してください。')
    await writeFile(image, pixels, { flag: 'wx' })
    await writeFile(definition, JSON.stringify({ layouts: [{ frame_cell: frameCell, image: basename(image), elements: before.elements }] }, null, 2) + '\n', { flag: 'wx' })
  }
  finally {
    await style.evaluate(node => node.remove())
  }
}
