# pixiv-plugin

Pixivイラスト検索・トレンド取得・ダウンロード・AI生成フィルタリング対応のClaude Code MCPプラグイン。
Skill / Command / MCP Tool の3層構造で、Pixiv APIを活用したイラスト探索を支援します。

## 構成

```
pixiv-plugin/
├── .claude-plugin/
│   └── plugin.json              # プラグインマニフェスト（Docker起動定義）
├── .mcp.json                    # MCPサーバー設定（docker run）
├── Dockerfile                   # Dockerイメージ定義
├── .dockerignore
├── main.py                      # MCPサーバー本体（Pixiv API / stdio）
├── setup_token.py               # Pixiv認証セットアップ（PKCE OAuthフロー）
├── pyproject.toml               # Python依存関係
├── .env.example                 # 環境変数テンプレート
├── commands/
│   ├── search-illusts.md        # /search-illusts コマンド（イラスト検索）
│   ├── trending.md              # /trending コマンド（ランキング）
│   └── download.md              # /download コマンド（ダウンロード）
└── skills/
    └── pixiv-explorer/
        ├── SKILL.md             # メインスキル（探索・分析・ダウンロード）
        └── references/
            └── pixiv-api-guide.md  # APIリファレンス
```

## 3層構造

| 層 | ファイル | 役割 |
|----|---------|------|
| **MCP Tool** | `main.py` | Pixiv API を叩く10個のツール |
| **Command** | `commands/*.md` | `/search-illusts 初音ミク` のように手軽に使うショートカット |
| **Skill** | `skills/pixiv-explorer/SKILL.md` | トレンド分析・作者調査・テーマ別収集を組み合わせたオーケストレーター |

### MCPツール一覧

| ツール | 説明 |
|--------|------|
| `search_illusts` | キーワード・タグでイラスト検索 |
| `search_by_hashtag` | ハッシュタグ完全一致検索 |
| `get_trending` | ランキング（デイリー/ウィークリー/R18等） |
| `get_trending_tags` | トレンドタグ一覧 |
| `get_user_illusts` | 特定ユーザーの作品一覧 |
| `get_illust_detail` | イラスト詳細情報 |
| `search_users` | ユーザー（作者）検索 |
| `get_recommended` | おすすめイラスト |
| `download_illust` | イラストダウンロード |
| `batch_download` | 一括ダウンロード |

### コマンド一覧

| コマンド | 説明 |
|----------|------|
| `/search-illusts <キーワード>` | イラストをキーワードやタグで検索 |
| `/trending` | 今日のトレンド・ランキングを表示 |
| `/download <イラストID>` | イラストをダウンロード（カンマ区切りで複数可） |

### スキル一覧

| スキル | 説明 |
|--------|------|
| `/pixiv-plugin:pixiv-explorer` | トレンド分析・テーマ別探索・作者調査・おすすめ探索を組み合わせた総合イラスト探索 |

## フィルタリング

全検索ツールで以下のフィルタが利用可能：

- **`exclude_ai`**: AI生成作品を除外（`illust_ai_type` に基づく）
- **`only_ai`**: AI生成作品のみ表示
- **`allow_r18`**: R-18作品を含める（デフォルト: 除外）

## 動作要件

- Docker
- Pixivアカウント（refresh token取得に必要）

開発時のみ：
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー

## セットアップ

### 1. Pixiv refresh token の取得

```bash
# 開発環境でセットアップスクリプトを実行
uv sync
uv run python setup_token.py
```

実行すると：
1. ブラウザで開くログインURLが表示される
2. ブラウザで **F12** → **Network** タブ → Filter に `callback` と入力
3. 表示されたURLでPixivにログイン
4. Networkタブに表示される `callback?...&code=XXXXXXXX` の `code` 値をコピー
5. ターミナルに貼り付けてEnter → `.env` に自動保存

その他のオプション：

```bash
# 既存のrefresh tokenをリフレッシュ
uv run python setup_token.py --refresh 既存のトークン

# 手動でrefresh tokenを.envに保存
uv run python setup_token.py --token トークン文字列
```

トークンなどは、`.env` や手元に控えておいてくd

```bash
cp .env.example .env
# .env に PIXIV_REFRESH_TOKEN を記入（setup_token.pyで自動保存済みならスキップ）
```

### 3. Docker イメージのビルド
mcpサーバーとして運用したい場合はこちらを使用する。プラグインの場合は必要ない。

```bash
docker build -t pixiv-plugin .
```

## インストール

### 方法1: 開発・テスト用（最も手軽）

```bash
claude --plugin-dir ./pixiv-plugin
```

### 方法2: ローカルマーケットプレース経由(推奨)

Claude Code セッション内で以下を実行します:

```
# マーケットプレースとしてローカルパスを登録
/plugin marketplace add ./

# プラグインをインストール
/plugin install pixiv-plugin@pixiv-artwork
```

インストールスコープを指定することもできます:

| スコープ | 用途 |
|---------|------|
| `--scope user` | 個人用（デフォルト） |
| `--scope project` | チーム共有（git管理される） |
| `--scope local` | プロジェクトローカル（gitignore対象） |

### 方法3: Git リポジトリ経由（配布・チーム共有向け）

本リポジトリ直下には [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) を配置しており、リポジトリ自体がマーケットプレースとして機能します。

```
# GitHubリポジトリをマーケットプレースとして登録
/plugin marketplace add bamboo-nova/pixiv-plugin

# プラグインをインストール（`pixiv-plugin@<マーケットプレース名>`）
/plugin install pixiv-plugin@pixiv-plugin

# プラグインをインストールできたら、/pluginでpixiv-pluginを選択して、Configure optionsにsetup_token.pyで取得したリフレッシュトークンを追加してください。
```

マーケットプレース名は `marketplace.json` の `name` フィールド（= `pixiv-plugin`）に対応します。

更新・管理:

```
# マーケットプレースを最新化（リポジトリから再取得）
/plugin marketplace update pixiv-plugin

# プラグインの有効/無効切替・アンインストール
/plugin
```

## 使い方

### コマンドで手軽に検索

```
/search-illusts 初音ミク
/search-illusts 原神 風景
/trending
/download 12345678
/download 12345678,23456789,34567890
```

### スキルでフル探索

「Pixivのトレンドを分析して」「初音ミクの人気イラストを探して」「AI生成を除いたオリジナル作品を見たい」のように話しかけると、pixiv-explorer スキルが起動します。

1. 目的・フィルタ条件（AI/R18）・数量をヒアリング
2. トレンド分析・テーマ検索・作者調査を並列実行
3. 結果を整理してテーブル表示
4. 気に入った作品のダウンロード

## ライセンス・免責事項

本プロジェクトはPixivが公式に提供・承認するものではなく、非公式の個人利用向けOSSです。

### 利用上の注意

- **利用規約の遵守**: 本プラグインを使用する際は、必ず [Pixiv利用規約](https://policies.pixiv.net/terms.html) および [プライバシーポリシー](https://policies.pixiv.net/privacy.html) に従ってください。
- **著作権の尊重**: 取得・ダウンロードしたイラストの著作権はすべて各作者に帰属します。**私的利用の範囲を超える再配布・商用利用・二次配布・学習データへの利用等は行わないでください。**
- **API利用の節度**: 過度なリクエストはPixivサーバーへの負荷となります。短時間での大量アクセスや自動巡回を避け、常識的なペースで利用してください（本プラグインはページング時に1.5秒のスリープを挟んでいます）。
- **個人情報の取り扱い**: `PIXIV_REFRESH_TOKEN` は認証情報です。`.env` ファイルは `.gitignore` に含めるなど、**外部に漏洩しないよう厳重に管理してください**。本プラグインはトークンをローカル環境外には送信しません。
- **AI生成作品の扱い**: `illust_ai_type` および関連タグに基づくフィルタリングを提供しますが、判定は作者申告およびタグに依存します。完全な分類は保証されません。

### 免責

本プラグインの利用によって生じたいかなる損害・トラブル（アカウント凍結、データ損失、権利侵害等を含む）についても、作者は一切の責任を負いません。自己責任のうえでご利用ください。