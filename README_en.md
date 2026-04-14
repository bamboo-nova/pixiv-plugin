# pixiv-plugin

A Claude Code MCP plugin for Pixiv illustration search, trending retrieval, download, and AI-generated content filtering.
It supports Pixiv-powered illustration exploration through a three-layer architecture: Skill / Command / MCP Tool.

## Structure

```
pixiv-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest (Docker startup definition)
├── .mcp.json                    # MCP server configuration (docker run)
├── Dockerfile                   # Docker image definition
├── .dockerignore
├── main.py                      # MCP server entry point (Pixiv API / stdio)
├── setup_token.py               # Pixiv authentication setup (PKCE OAuth flow)
├── pyproject.toml               # Python dependencies
├── .env.example                 # Environment variable template
├── commands/
│   ├── search-illusts.md        # /search-illusts command (illustration search)
│   ├── trending.md              # /trending command (rankings)
│   └── download.md              # /download command (download)
└── skills/
    └── pixiv-explorer/
        ├── SKILL.md             # Main skill (exploration / analysis / download)
        └── references/
            └── pixiv-api-guide.md  # API reference
```

## Three-layer architecture

| Layer | File | Role |
|-------|------|------|
| **MCP Tool** | `main.py` | 10 tools that call the Pixiv API |
| **Command** | `commands/*.md` | Shortcuts for quick usage like `/search-illusts Hatsune Miku` |
| **Skill** | `skills/pixiv-explorer/SKILL.md` | Orchestrator combining trend analysis, author research, and themed collection |

### MCP tool list

| Tool | Description |
|------|-------------|
| `search_illusts` | Search illustrations by keyword/tag |
| `search_by_hashtag` | Exact hashtag match search |
| `get_trending` | Rankings (daily / weekly / R18, etc.) |
| `get_trending_tags` | List of trending tags |
| `get_user_illusts` | Works by a specific user |
| `get_illust_detail` | Detailed illustration info |
| `search_users` | Search users (authors) |
| `get_recommended` | Recommended illustrations |
| `download_illust` | Download an illustration |
| `batch_download` | Batch download |

### Command list

| Command | Description |
|---------|-------------|
| `/search-illusts <keyword>` | Search illustrations by keyword or tag |
| `/trending` | Show today's trending rankings |
| `/download <illust ID>` | Download illustrations (comma-separated for multiple) |

### Skill list

| Skill | Description |
|-------|-------------|
| `/pixiv-plugin:pixiv-explorer` | Integrated illustration exploration combining trend analysis, themed exploration, author research, and recommendations |

## Filtering

The following filters are available across all search tools:

- **`exclude_ai`**: Exclude AI-generated works (based on `illust_ai_type`)
- **`only_ai`**: Show only AI-generated works
- **`allow_r18`**: Include R-18 works (default: excluded)

## Requirements

- Docker
- A Pixiv account (required to obtain a refresh token)

For development only:
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

### 1. Obtain a Pixiv refresh token

```bash
# Run the setup script in a development environment
uv sync
uv run python setup_token.py
```

When executed:
1. A login URL to open in your browser is shown
2. In the browser, press **F12** → open the **Network** tab → type `callback` into the filter
3. Log in to Pixiv using the displayed URL
4. Copy the `code` value from the `callback?...&code=XXXXXXXX` URL shown in the Network tab
5. Paste it into the terminal and press Enter → it is automatically saved to `.env`

Other options:

```bash
# Refresh an existing refresh token
uv run python setup_token.py --refresh <existing-token>

# Save a refresh token to .env manually
uv run python setup_token.py --token <token-string>
```

### 2. Prepare `.env`

```bash
cp .env.example .env
# Fill in PIXIV_REFRESH_TOKEN in .env (skip if already auto-saved by setup_token.py)
```

### 3. Build the Docker image

Use this if you want to run it as an MCP server. Not required when used as a plugin.

```bash
docker build -t pixiv-plugin .
```

## Installation

### Option 1: Development / testing (easiest)

```bash
claude --plugin-dir ./pixiv-plugin
```

### Option 2: Via a local marketplace (recommended)

Run the following in a Claude Code session:

```
# Register the local path as a marketplace
/plugin marketplace add ./

# Install the plugin
/plugin install pixiv-plugin@pixiv-artwork
```

You can also specify an installation scope:

| Scope | Purpose |
|-------|---------|
| `--scope user` | Personal use (default) |
| `--scope project` | Shared with a team (tracked by git) |
| `--scope local` | Project-local (gitignored) |

### Option 3: Via a Git repository (for team sharing)

```
# Register a GitHub repository as a marketplace
/plugin marketplace add <owner>/<repo>

# Install the plugin
/plugin install pixiv-plugin@<marketplace-name>
```

## Usage

### Quick search via commands

```
/search-illusts Hatsune Miku
/search-illusts Genshin scenery
/trending
/download 12345678
/download 12345678,23456789,34567890
```

### Full exploration via the skill

Phrases like "Analyze Pixiv trends", "Find popular Hatsune Miku illustrations", or "I want to see original works excluding AI-generated ones" will trigger the pixiv-explorer skill.

1. Clarify the purpose, filter conditions (AI/R18), and quantity
2. Run trend analysis, themed search, and author research in parallel
3. Organize and display the results in a table
4. Download the works you like

## License & Disclaimer

This project is an unofficial, personal-use OSS project; it is not provided or endorsed by Pixiv.

### Usage notes

- **Comply with the terms of service**: When using this plugin, you must follow the [Pixiv Terms of Service](https://policies.pixiv.net/terms.html) and [Privacy Policy](https://policies.pixiv.net/privacy.html).
- **Respect copyright**: All copyrights of the illustrations you retrieve or download belong to their respective authors. **Do not redistribute, use commercially, redistribute derivatively, or use them as training data beyond the scope of personal use.**
- **Reasonable API usage**: Excessive requests place a burden on Pixiv's servers. Avoid high-volume access or automated crawling in a short period, and use the API at a reasonable pace (this plugin inserts a 1.5-second sleep between paginated requests).
- **Handling of personal information**: `PIXIV_REFRESH_TOKEN` is a credential. **Manage it carefully to prevent leakage**, e.g., by including `.env` in `.gitignore`. This plugin never transmits the token outside your local environment.
- **Handling of AI-generated works**: Filtering is provided based on `illust_ai_type` and related tags, but judgement depends on the author's self-declaration and tags. Complete classification is not guaranteed.

### Disclaimer

The authors assume no responsibility for any damage or trouble (including account suspension, data loss, or rights infringement) arising from the use of this plugin. Use it at your own risk.
