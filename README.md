# doubak-site-generator-sample

[**sample.doubak.com**](https://sample.doubak.com) —— 豆备 (Doubak) 生成的示例站点，数据是我自己的豆瓣账号。

这个仓库里除了本文件、`LICENSE` 与 `CNAME`，**其余全部是生成的**，不要手改：下一次生成会把它们清掉重铺。

## 它是怎么来的

```sh
# 1. 浏览器扩展在自己的浏览器里抓，产出 bundle（WARC + 索引 + 清单）
# 2. bundle → canonical（结构化、带修订历史）
node bin/parse.js  ~/downloads/20260806 ~/downloads/20260806-canonical

# 3. canonical + bundle → 这个仓库
node bin/deploy.js ~/downloads/20260806-canonical ~/downloads/20260806 <这个目录>
```

三步分别在 [doubak-extension](https://github.com/Doubak/doubak-extension)、[doubak-data-parser](https://github.com/Doubak/doubak-data-parser)、[doubak-site-generator](https://github.com/Doubak/doubak-site-generator)。

## 这份示例里有什么

| | |
|---|---|
| 标记 | 2940 条（影视 2102 · 游戏 604 · 书 145 · 音乐 84 · 舞台剧 5） |
| 广播 | 3394 条，其中 804 条带正文，按月归档成 152 页 |
| 长文 | 日记 3 篇 · 评论 2 篇，全文 |
| 图片 | 3045 张 = 作品封面 2921 + 自己上传的 124 |
| 页面 | 4694 个 HTML，129 MB |

## 两条可以自己验的性质

**页面打开时不发任何外部请求。** 图片全部导出到本地，`src` 里没有一个外部域名。这是整件事的要点：一份要联网、而且要豆瓣还在才能看的备份，不叫备份。

**不需要服务器也能看。** 把这个仓库整个下下来，双击 `index.html` 就能浏览 —— 站内 3633 个链接全部是相对路径且指向真实文件。它要在很多年后被人从一块硬盘上打开，那时候「起一个静态服务器」不该是先决条件。

## 关于内容

这个账号的豆瓣内容本来就是公开的，站点里的标记、短评、广播、日记都是我自己写的。作品封面来自豆瓣的目录数据。

站点**不含任何第三方内容**：抓取时就不抓别人的回复、关注列表与豆邮，转发进来的别人的广播按 `data-uid` 过滤掉，别人上传的图片也不抓。

## 主题是可以换的

这个站点用的是 site-generator 自带的那个最小骨架（五个文件的 Hugo 布局）。生成器真正的产物是 **Markdown + YAML front matter**，换任何一个现成的 Hugo 主题只要删掉 `layouts/`；换 Astro / Eleventy / Jekyll 也行 —— 见 site-generator 的 README。
