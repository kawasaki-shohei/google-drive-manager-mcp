# GCP OAuth セットアップ手順

google-drive-manager MCP を動作させるための GCP OAuth 設定手順です。

## Step 1: GCP プロジェクト作成

1. https://console.cloud.google.com/ を `kawasaki.shohei.1@gmail.com` でログイン
2. 画面上部のプロジェクトセレクタ → **「新しいプロジェクト」**
3. プロジェクト名: `google-drive-manager-mcp`
4. 「作成」

## Step 2: Google Drive API を有効化

1. 左メニュー → **「API とサービス」→「ライブラリ」**
2. `Google Drive API` を検索 → **「有効にする」**

## Step 3: OAuth 同意画面（Google Auth Platform）

4ステップのウィザードが表示されます。

| ステップ | 設定内容 |
|---|---|
| Step 1（アプリ情報） | アプリ名: `drive-manager-mcp`、サポートメール: `kawasaki.shohei.1@gmail.com` |
| Step 2（対象） | **External** を選択（個人 Gmail では選択肢なし） |
| Step 3（連絡先） | デベロッパーメール: `kawasaki.shohei.1@gmail.com` |
| Step 4 | 規約に同意 → **「作成」** |

### ウィザード完了後に設定する項目

**スコープ追加**
- 左メニュー「データアクセス」→ `drive` スコープを追加

**本番公開**
- 左メニュー「対象」→ **「本番環境に公開」**
- 「アプリの検証が必要です」警告は**無視してOK**（100ユーザー未満の個人利用は審査不要）

> **注意**: Testing モードのままにしておくと認証時に「テスト中でテスターのみアクセス可能」エラーが出る。必ず本番公開すること。
> テストユーザーに `kawasaki.shohei.1@gmail.com` を追加するだけでも回避可能（https://console.cloud.google.com/auth/audience）。

## Step 4: OAuth クライアント ID 作成

1. 「API とサービス」→「認証情報」→ **「認証情報を作成」** → 「OAuth クライアント ID」
2. アプリケーションの種類: **デスクトップアプリ**（Desktop app）
   - Web application ではなく Desktop app を選ぶこと（ローカル MCP はブラウザ不要のため）
3. 名前: 任意。例: `google-drive-manager-mcp`
4. 「作成」→ **`credentials.json` をダウンロード**
5. ダウンロードしたファイルを以下に配置:
   ```
   ~/.claude/mcp-servers/google-drive-manager/credentials/client_secrets.json
   ```

## Step 5: 認証実行

```bash
!cd ~/.claude/mcp-servers/google-drive-manager && uv run google-drive-manager-auth
```

実行すると:
1. ブラウザが自動起動
2. Google アカウントを選択（`kawasaki.shohei.1@gmail.com`）
3. 「未検証アプリ」警告が出た場合 → 「詳細」→「安全でないページへ移動」でスキップ
4. 権限を許可 → 認証完了

認証トークンは `~/.claude/mcp-servers/google-drive-manager/credentials/` に保存され、以後は自動更新される。

## 動作確認

Claude Code を再起動後:

```
claude mcp list
```

`google-drive-manager ✓ Connected` と表示されれば完了。
