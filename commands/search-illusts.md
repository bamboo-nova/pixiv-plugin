---
description: Pixivでイラストを検索する
argument: 検索キーワードまたはタグ
allowedTools:
  - mcp: pixiv-artwork
    tools:
      - search_illusts
      - search_by_hashtag
      - get_illust_detail
---

ユーザーの引数「$ARGUMENTS」をもとにPixivでイラストを検索してください。

## 手順

1. `search_illusts` ツールを使って「$ARGUMENTS」で検索する（limit: 20）
2. 結果を以下のテーブル形式で表示する：

| # | タイトル | 作者 | タグ | AI | R18 | ブクマ | 閲覧数 |
|---|---------|------|------|-----|-----|-------|--------|

3. AI生成・R18のステータスも表示する
4. ユーザーが特定のイラストについて詳細を知りたい場合は `get_illust_detail` で取得する

## 注意
- デフォルトではR-18は除外（ユーザーが明示的に要求した場合のみ `allow_r18: true`）
- AI生成フィルタはユーザーの指定に従う
