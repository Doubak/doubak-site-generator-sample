# doubak-site-generator-sample

[![test-scripts](https://github.com/Doubak/doubak-site-generator-sample/actions/workflows/test-scripts.yml/badge.svg?branch=main)](https://github.com/Doubak/doubak-site-generator-sample/actions/workflows/test-scripts.yml?query=branch%3Amain)

[**sample.doubak.com**](https://sample.doubak.com) —— 豆备 (Doubak) 生成的示例站点，数据是我自己的豆瓣账号。

项目主页在 **<https://doubak.com>** —— 那里讲清楚这套东西是什么、怎么用。
本仓库只是它的一份产出。

这个仓库里除了本文件、`LICENSE`、`CNAME` 与 `.github/`，**其余全部是生成的**，不要手改：下一次生成会把它们清掉重铺。

## 它是怎么来的

```sh
# 1. 浏览器扩展在自己的浏览器里抓，产出 bundle（WARC + 索引 + 清单）
# 2. bundle → canonical（结构化、带修订历史）
node bin/parse.js  ~/downloads/exports ~/downloads/canonical

# 3. canonical + bundle → 这个仓库
node bin/deploy.js ~/downloads/canonical ~/downloads/exports <这个目录> --include-private
```

**这一份是带 `--include-private` 生成的**，所以豆瓣上不公开的东西也在里面（页面上带
🔒，页脚每一页都写着这句话）。样张站要展示的正是这个能力；**不加那个开关是默认，
私密日记、私密豆列、只有自己看得见的广播都不会发出去**。见〈关于内容〉。

三步分别在 [doubak-extension](https://github.com/Doubak/doubak-extension)、[doubak-data-parser](https://github.com/Doubak/doubak-data-parser)、[doubak-site-generator](https://github.com/Doubak/doubak-site-generator)。

### sitemap 是 GitHub Actions 自己长出来的

`.github/workflows/sitemap.yml` 在每次推到 `main` 之后重新生成 `sitemap.xml`，
默认开一个 PR 让你合（把文件顶上的 `MODE` 从 `pr` 改成 `push` 就直接提交到
`main`）。生成用 [cicirello/generate-sitemap](https://github.com/cicirello/generate-sitemap)，
之后再过一遍 `.github/scripts/fix_sitemap.py`：去掉分页的「第 1 页」跳转壳子
（那是 meta refresh，不是页面），并把中日文 tag 路径按 RFC 3986 转义。
这个脚本有测试，只用标准库，`python3 .github/scripts/test_fix_sitemap.py` 就能跑。

`deploy.js` 重铺站点时保留 `.github/`，所以这套东西不会被清掉；`sitemap.xml`
会被当成上次的残留删掉，再由这次部署推送触发的运行重新生成。

**所以下一次 `deploy.js` 之前要先 `git pull`。** sitemap 是在 GitHub 上提交的，
本地仓库没有那一笔，不拉下来的话推送会被拒（non-fast-forward）。这是「让机器
自动提交」换来的，不是出了问题。

## 这份示例里有什么

| | |
|---|---|
| 标记 | 2966 条（影视 2123 · 游戏 608 · 书 145 · 音乐 85 · 舞台剧 5） |
| 广播 | 3429 条，其中 2224 条带正文，按月归档成 155 页 |
| 长文 | 日记 4 篇 · 评论 2 篇，全文 |
| 豆列 | 6 份（其中 1 份在豆瓣上是私密的，页面上带 🔒） |
| 作品信息 | 2321 个作品页有导演／作者／类型等（来自作品详情页） |
| 图片 | 2939 张 |
| 页面 | 4826 个 HTML，153 MB |
| 时间线 | 2404 个作品页有「说过什么」（2966 的 81%） |
| 搜索 | 5201 条可搜条目（2033 条带又名、2321 条带导演等信息），索引 gzip 后 466 KB |

## 「什么时候 → 说了什么」

作品页上除了当前那条短评，还有一段时间线，把**标记的历次修订**与**提到这个作品的广播**按时间合在一起。

这是这套东西真正想买的：豆瓣的标记页只剩最新那条短评，改一次覆盖一次；而**广播发布即冻结、带秒级时间戳**，所以它替你记住了标记页上早就没有的话，包括第一次备份之前说的。

```
2026-08-01           标记 · 看过    确实还不错…之前就说能上6分…
2026-07-18 12:44:56  广播 · 想看    能上6分我觉得都是国产好片
```

没有短评的状态也算历史 —— 「2023-03-24 想玩 / 2023-03-31 在玩 / 2026-07-19 玩过」一个字都没有，却是这条标记完整的经过。

**但它不下「改过」的判断。** 实测那 342 条与当前短评不同的发言里，305 条是状态推进（想看时说一句，看过之后又说一句），只有 15 条是同一状态下说了别的。呈现成「检测到编辑」的话 89% 都是冤枉的。所以只按时间列出来，判断留给你。

每一条都标出处，归并之后时间与短评来自不同地方时也会写明 —— 因为「广播 · 玩过」后面跟一段短评，很容易被读成「那条广播里写着这句话」，而广播里其实什么都没写。

## 搜索

站内搜索在 [/search.html](https://sample.doubak.com/search.html)，**没有索引结构、没有依赖、没有外部请求** —— 全量扫一遍 0.1–0.5 毫秒，键入即出结果。

作品的**又名**（台译名 / 港译名 / 原文名）与标题同权重 —— 搜「重返沉默之丘」和搜「重返寂静岭」是一样的结果。导演、作者、类型也能搜（搜「宫崎骏」找得到 21 部）；主演刻意不进索引，理由见 site-generator 的 README。

索引是 `.js` 不是 `.json`：浏览器在 `file://` 下会拦掉 `fetch`，而这份档案要能双击打开就用。

## 两条可以自己验的性质

**页面打开时不发任何外部请求。** 图片全部导出到本地，`src` 里没有一个外部域名。这是整件事的要点：一份要联网、而且要豆瓣还在才能看的备份，不叫备份。

**不需要服务器也能看。** 把这个仓库整个下下来，双击 `index.html` 就能浏览 —— 站内每一个链接都是相对路径且指向真实文件。它要在很多年后被人从一块硬盘上打开，那时候「起一个静态服务器」不该是先决条件。

## 关于内容

站点里的标记、短评、广播、日记都是我自己写的，作品封面来自豆瓣的目录数据。

**这一份里有几样在豆瓣上并不公开**，因为它是带 `--include-private` 生成的——样张站
要展示的正是这个能力。它们在页面上各带一枚 🔒：

| | |
|---|---|
| 1 篇日记 | 我自己设成「仅自己可见」的（内容是一句测试） |
| 1 份豆列 | `SELECTS`，豆瓣上只有我自己看得见 |
| 1 条广播 | 发那篇私密日记时豆瓣同步出来的，正文与日记一字不差 |
| 1 篇日记 | **被豆瓣锁成「仅自己可见」的**——它本来是公开的，页面上逐字引着豆瓣给的说法 |

最后那一行不受这个开关影响：**默认就发**，理由是它之所以不公开恰恰因为它曾经是公开的，
跟着豆瓣一起收起来这份存档就白存了。前三行才是 `--include-private` 管的，
**不加那个开关它们一条都不会出现**。

那条广播值得单说，它是这个开关存在的原因：豆瓣发一篇私密日记时会同步一条广播，
**正文一字不差**，而抓取跑在自己的登录态下，所以只有自己看得见的那条也进了档案。
09-07 给日记补可见性时漏了广播这一侧，于是那篇日记的正文一度出现在这个站的首页上——
日记那一页发没发根本不重要，**内容从旁边那条路漏了出去**。

站点**不含任何第三方内容**：抓取时就不抓别人的回复、关注列表与豆邮，转发进来的别人的广播按 `data-uid` 过滤掉，别人上传的图片也不抓。

## 主题是可以换的

这个站点用的是 site-generator 自带的那个最小骨架（五个文件的 Hugo 布局）。生成器真正的产物是 **Markdown + YAML front matter**，换任何一个现成的 Hugo 主题只要删掉 `layouts/`；换 Astro / Eleventy / Jekyll 也行 —— 见 site-generator 的 README。
