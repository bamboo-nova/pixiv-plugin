---
description: Pixivイラストをダウンロードする
argument: イラストID（カンマ区切りで複数指定可）
allowedTools:
  - mcp: pixiv-artwork
    tools:
      - get_illust_detail
      - download_illust
      - batch_download
---

ユーザーの引数「$ARGUMENTS」に指定されたイラストIDをダウンロードしてください。

## 手順

1. 引数からイラストIDを解析する（カンマ区切りの場合は複数）
2. 単一IDの場合：
   - `get_illust_detail` で詳細を取得し、タイトル・作者・ページ数を表示
   - `download_illust` でオリジナルサイズをダウンロード
3. 複数IDの場合：
   - `batch_download` で一括ダウンロード
4. ダウンロード結果（ファイルパス・サイズ）を報告

## 注意
- ダウンロードは個人利用の範囲で行うこと
- 著作権に配慮し、再配布目的でのダウンロードは推奨しない
