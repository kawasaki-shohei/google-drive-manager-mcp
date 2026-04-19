# google-drive-manager

Google Drive を操作する Claude Code 用カスタム MCP サーバー。

## 機能

| ツール | 説明 |
|---|---|
| `list_files` | ファイル一覧取得（フォルダ・名前・MIMEタイプでフィルタ可） |
| `read_file` | ファイル内容をテキストとして読み込む |
| `upload_file` | ローカルファイルを Drive にアップロード |
| `upload_markdown_as_google_doc` | Markdown（ローカル画像付き）を pandoc 経由で Google Docs に変換してアップロード |
| `create_folder` | フォルダ作成 |
| `rename_file` | ファイル・フォルダのリネーム |
| `delete_file` | ファイル・フォルダを完全削除 |
| `list_permissions` | 共有権限の一覧取得 |
| `share_file` | メールアドレスに共有権限を付与 |
| `revoke_permission` | 共有権限を削除 |

## セットアップ

### 1. 前提

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- [pandoc](https://pandoc.org/)（`upload_markdown_as_google_doc` を使う場合）

```bash
brew install pandoc
```

### 2. GCP OAuth 設定

詳細は [docs/gcp_oauth_setup.md](docs/gcp_oauth_setup.md) を参照。

### 3. 認証

```bash
cd ~/.claude/mcp-servers/google-drive-manager
uv run google-drive-manager-auth
```

ブラウザが開くので Google アカウントで認証する。トークンは `credentials/token.json` に保存される。

### 4. Claude Code に登録

```bash
claude mcp add google-drive-manager -- uv --directory ~/.claude/mcp-servers/google-drive-manager run google-drive-manager
```

## 開発

```bash
uv run pytest tests/
```
