---
description: Pixivの今日のトレンド・ランキングを表示する
allowedTools:
  - mcp: pixiv-artwork
    tools:
      - get_trending
      - get_trending_tags
      - get_illust_detail
---

Pixivの最新トレンドを取得して表示してください。

## 手順

1. `get_trending_tags` でトレンドタグ一覧を取得
2. `get_trending` で本日のデイリーランキング（mode: "day", limit: 20）を取得
3. 以下の形式で表示：

### トレンドタグ
タグ名を箇条書きで表示（上位10件）

### デイリーランキング TOP 20
| 順位 | タイトル | 作者 | タグ | AI | ブクマ | 閲覧数 |
|------|---------|------|------|-----|-------|--------|

4. ユーザーが特定作品の詳細を知りたい場合は `get_illust_detail` で取得

## 注意
- デフォルトではR-18は除外
- AI生成作品にはAIラベルを表示
