## コードの整形（Prettier）

- コードの整形には、Prettierを使う。設定は、アプリのルートの`.prettierrc`にある。
- 整形の対象は、`.ts`、`.vue`、`.mjs`、`.js`、`.json`とする。Markdownは、対象外とする。
- 設定は、次のとおりとする。

| 項目 | 値 | 意味 |
| --- | --- | --- |
| `semi` | `false` | 行末にセミコロンを付けない |
| `singleQuote` | `true` | 文字列は、単一引用符で囲む |
| `tabWidth` | `2` | インデントは、半角スペース2つ |
| `printWidth` | `100` | 1行は、100文字までとし、超えたら折り返す |

- 対象外のファイルは、アプリのルートの`.prettierignore`に書く（依存パッケージ、生成物、テストの証跡とレポート、ロックファイル、`docs`、Markdown）。
- コードの検査（ESLint）と整形（Prettier）は、役割を分ける。ESLintは検査だけを行い、整形と衝突する規則は、`eslint-config-prettier`で無効にする。
- AIが編集したファイルは、フック（`.claude/hooks/formatter/`）が、自動で整形する。拡張子ごとの設定は、`.claude/settings.json`の`if`に書く。
- 手で整形するときは、アプリのルートで、次のコマンドを実行する。

```powershell
node nuxt/node_modules/prettier/bin/prettier.cjs --write --ignore-path .prettierignore <ファイルまたはパターン>
```

**理由**: Prettierは、JavaScript、TypeScript、Vueの整形ツールとして、広く使われている標準的なツールである。  
整形をツールに任せると、書き方の違いによる差分が、レビューに混ざらない。  
Markdownを対象外にするのは、文書の規約（行末の半角スペース2つによる改行など）を、崩さないためである。  
`docs`を対象外にするのは、設計書の生成元のJSONなど、資料を、整形で書き換えないためである。  
ESLintと役割を分けるのは、2つのツールが、同じ箇所を、逆向きに直し合うことを避けるためである。

> [AI]
> - ファイルを編集すると、フックが、自動で整形する。フックから、直せない指摘が伝えられたら、コードを直す。
> - フックが動かない環境では、手で整形してから、完了を報告する。
