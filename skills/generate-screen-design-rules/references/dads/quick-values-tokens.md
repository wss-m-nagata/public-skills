# DADS Design Token 早見表（生成物）

`scripts/gen_quick_values.py` が `design-tokens/tokens.json` から生成した。**手で書き換えない。**
tokens.json を更新したら、スクリプトをもう一度実行して作り直す。
値の出典は、DADS の Design Token（https://github.com/digital-go-jp/design-tokens）。
別名（例: Semantic が Primitive を指す）は、実際の値まで解決してある。

## 色

### キー（既定の色相）

| 段階 | 値 |
| --- | --- |
| 50 | `#e8f1fe` |
| 100 | `#d9e6ff` |
| 200 | `#c5d7fb` |
| 300 | `#9db7f9` |
| 400 | `#7096f8` |
| 500 | `#4979f5` |
| 600 | `#3460fb` |
| 700 | `#264af4` |
| 800 | `#0031d8` |
| 900 | `#0017c1` |
| 1000 | `#00118f` |
| 1100 | `#000071` |
| 1200 | `#000060` |

### ニュートラル

| 名前 | 値 |
| --- | --- |
| White | `#ffffff` |
| Black | `#000000` |
| SolidGray 50 | `#f2f2f2` |
| SolidGray 100 | `#e6e6e6` |
| SolidGray 200 | `#cccccc` |
| SolidGray 300 | `#b3b3b3` |
| SolidGray 400 | `#999999` |
| SolidGray 420 | `#949494` |
| SolidGray 500 | `#7f7f7f` |
| SolidGray 536 | `#767676` |
| SolidGray 600 | `#666666` |
| SolidGray 700 | `#4d4d4d` |
| SolidGray 800 | `#333333` |
| SolidGray 900 | `#1a1a1a` |
| OpacityGray 50 | `rgba(0,0,0,0.05)` |
| OpacityGray 100 | `rgba(0,0,0,0.1)` |
| OpacityGray 200 | `rgba(0,0,0,0.2)` |
| OpacityGray 300 | `rgba(0,0,0,0.3)` |
| OpacityGray 400 | `rgba(0,0,0,0.4)` |
| OpacityGray 420 | `rgba(0,0,0,0.42)` |
| OpacityGray 500 | `rgba(0,0,0,0.5)` |
| OpacityGray 536 | `rgba(0,0,0,0.536)` |
| OpacityGray 600 | `rgba(0,0,0,0.6)` |
| OpacityGray 700 | `rgba(0,0,0,0.7)` |
| OpacityGray 800 | `rgba(0,0,0,0.8)` |
| OpacityGray 900 | `rgba(0,0,0,0.9)` |

### セマンティック（成功・エラー・警告）

| 名前 | 参照先 | 値 |
| --- | --- | --- |
| Semantic.Success.1 | `{Color.Primitive.Green.600}` | `#259d63` |
| Semantic.Success.2 | `{Color.Primitive.Green.800}` | `#197a4b` |
| Semantic.Error.1 | `{Color.Primitive.Red.800}` | `#ec0000` |
| Semantic.Error.2 | `{Color.Primitive.Red.900}` | `#ce0000` |
| Semantic.Warning.Yellow.1 | `{Color.Primitive.Yellow.700}` | `#b78f00` |
| Semantic.Warning.Yellow.2 | `{Color.Primitive.Yellow.900}` | `#927200` |
| Semantic.Warning.Orange.1 | `{Color.Primitive.Orange.600}` | `#fb5b01` |
| Semantic.Warning.Orange.2 | `{Color.Primitive.Orange.800}` | `#c74700` |

### プリミティブ（色相ごと）

- **Blue**: 50 `#e8f1fe`、100 `#d9e6ff`、200 `#c5d7fb`、300 `#9db7f9`、400 `#7096f8`、500 `#4979f5`、600 `#3460fb`、700 `#264af4`、800 `#0031d8`、900 `#0017c1`、1000 `#00118f`、1100 `#000071`、1200 `#000060`
- **LightBlue**: 50 `#f0f9ff`、100 `#dcf0ff`、200 `#c0e4ff`、300 `#97d3ff`、400 `#57b8ff`、500 `#39abff`、600 `#008bf2`、700 `#0877d7`、800 `#0066be`、900 `#0055ad`、1000 `#00428c`、1100 `#00316a`、1200 `#00234b`
- **Cyan**: 50 `#e9f7f9`、100 `#c8f8ff`、200 `#99f2ff`、300 `#79e2f2`、400 `#2bc8e4`、500 `#01b7d6`、600 `#00a3bf`、700 `#008da6`、800 `#008299`、900 `#006f83`、1000 `#006173`、1100 `#004c59`、1200 `#003741`
- **Green**: 50 `#e6f5ec`、100 `#c2e5d1`、200 `#9bd4b5`、300 `#71c598`、400 `#51b883`、500 `#2cac6e`、600 `#259d63`、700 `#1d8b56`、800 `#197a4b`、900 `#115a36`、1000 `#0c472a`、1100 `#08351f`、1200 `#032213`
- **Lime**: 50 `#ebfad9`、100 `#d0f5a2`、200 `#c0f354`、300 `#ade830`、400 `#9ddd15`、500 `#8cc80c`、600 `#7eb40d`、700 `#6fa104`、800 `#618e00`、900 `#507500`、1000 `#3e5a00`、1100 `#2c4100`、1200 `#1e2d00`
- **Yellow**: 50 `#fbf5e0`、100 `#fff0b3`、200 `#ffe380`、300 `#ffd43d`、400 `#ffc700`、500 `#ebb700`、600 `#d2a400`、700 `#b78f00`、800 `#a58000`、900 `#927200`、1000 `#806300`、1100 `#6e5600`、1200 `#604b00`
- **Orange**: 50 `#ffeee2`、100 `#ffdfca`、200 `#ffc199`、300 `#ffa66d`、400 `#ff8d44`、500 `#ff7628`、600 `#fb5b01`、700 `#e25100`、800 `#c74700`、900 `#ac3e00`、1000 `#8b3200`、1100 `#6d2700`、1200 `#541e00`
- **Red**: 50 `#fdeeee`、100 `#ffdada`、200 `#ffbbbb`、300 `#ff9696`、400 `#ff7171`、500 `#ff5454`、600 `#fe3939`、700 `#fa0000`、800 `#ec0000`、900 `#ce0000`、1000 `#a90000`、1100 `#850000`、1200 `#620000`
- **Magenta**: 50 `#f3e5f4`、100 `#ffd0ff`、200 `#ffaeff`、300 `#ff8eff`、400 `#f661f6`、500 `#f137f1`、600 `#db00db`、700 `#c000c0`、800 `#aa00aa`、900 `#8b008b`、1000 `#6c006c`、1100 `#500050`、1200 `#3b003b`
- **Purple**: 50 `#f1eafa`、100 `#ecddff`、200 `#ddc2ff`、300 `#cda6ff`、400 `#bb87ff`、500 `#a565f8`、600 `#8843e1`、700 `#6f23d0`、800 `#5c10be`、900 `#5109ad`、1000 `#41048e`、1100 `#30016c`、1200 `#21004b`

## 文字

| 種類 | 値 |
| --- | --- |
| FontFamily | Sans: `'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif`、Mono: `'Noto Sans Mono', monospace` |
| FontWeight | 400: `400`、700: `700` |
| FontSize | 14: `14px`、16: `16px`、17: `17px`、18: `18px`、20: `20px`、22: `22px`、24: `24px`、26: `26px`、28: `28px`、32: `32px`、36: `36px`、45: `45px`、48: `48px`、57: `57px`、64: `64px` |
| LineHeight | 100: `100%`、120: `120%`、130: `130%`、140: `140%`、150: `150%`、160: `160%`、170: `170%`、175: `175%` |

## 角丸

| 名前 | 値 |
| --- | --- |
| 4 | `4px` |
| 6 | `6px` |
| 8 | `8px` |
| 12 | `12px` |
| 16 | `16px` |
| 24 | `24px` |
| 32 | `32px` |
| Full | `9999px` |

## 影（エレベーション）

| スタイル | box-shadow |
| --- | --- |
| 1 | `0 2px 8px 1px rgba(0,0,0,0.1), 0 1px 5px 0 rgba(0,0,0,0.3)` |
| 2 | `0 2px 12px 2px rgba(0,0,0,0.1), 0 1px 6px 0 rgba(0,0,0,0.3)` |
| 3 | `0 4px 16px 3px rgba(0,0,0,0.1), 0 1px 6px 0 rgba(0,0,0,0.3)` |
| 4 | `0 6px 20px 4px rgba(0,0,0,0.1), 0 2px 6px 0 rgba(0,0,0,0.3)` |
| 5 | `0 8px 24px 5px rgba(0,0,0,0.1), 0 2px 10px 0 rgba(0,0,0,0.3)` |
| 6 | `0 10px 30px 6px rgba(0,0,0,0.1), 0 3px 12px 0 rgba(0,0,0,0.3)` |
| 7 | `0 12px 36px 7px rgba(0,0,0,0.1), 0 3px 14px 0 rgba(0,0,0,0.3)` |
| 8 | `0 14px 40px 7px rgba(0,0,0,0.1), 0 3px 16px 0 rgba(0,0,0,0.3)` |
