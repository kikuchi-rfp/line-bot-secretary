# ローカル開発セットアップガイド

秘書 AI エージェントと LINE Bot をローカルで動作確認するための手順です。

## 📋 前提条件

- Python 3.9+
- pip
- 認証情報（Gmail OAuth トークン、Google Calendar Service Account）

## 🚀 セットアップ手順

### ステップ 1: 秘書 AI エージェント環境設定

```bash
cd 05_秘書

# 1. 依存パッケージをインストール
pip install -r requirements.txt

# 2. .env ファイルを作成
cp .env.example .env

# 3. .env に認証情報を記入
#    GMAIL_REFRESH_TOKEN=...
#    GMAIL_CLIENT_ID=...
#    GMAIL_CLIENT_SECRET=...
#    ANTHROPIC_API_KEY=...
#    GOOGLE_SERVICE_ACCOUNT_FILE=config/service_account.json

# 4. 認証情報ファイルを配置
#    config/gmail_refresh_token.json（すでにあるはず）
#    config/service_account.json（Google Calendar Service Account JSON）
```

### ステップ 2: LINE Bot 環境設定

```bash
cd 06_開発/01_LINE_Bot

# 1. 依存パッケージをインストール
pip install -r requirements.txt

# 2. .env ファイルを確認/作成
# LINE_CHANNEL_SECRET=...
# LINE_CHANNEL_ACCESS_TOKEN=...
# SECRETARY_AGENT_URL=http://localhost:5000/api/secretary
```

## 🧪 テスト実行

### ターミナル 1: 秘書 AI API サーバーを起動

```bash
cd 05_秘書
python api.py

# 出力例：
# 秘書 AI API サーバー起動中... (http://localhost:5000)
# * Running on http://0.0.0.0:5000
```

### ターミナル 2: LINE Bot を起動

```bash
cd 06_開発/01_LINE_Bot
python main.py

# 出力例：
# LINE Bot 秘書 - シンプル版（プロキシ）
# 秘書 AI エージェント: http://localhost:5000/api/secretary
# Flask サーバーを起動します...
# Listening on http://0.0.0.0:8080
```

### ターミナル 3: API をテスト

#### 秘書 AI エージェントのテスト

```bash
# ヘルスチェック
curl http://localhost:5000/health

# 秘書 AI を呼び出し
curl -X POST http://localhost:5000/api/secretary \
  -H "Content-Type: application/json" \
  -d '{"message": "今週の予定を教えて"}'
```

**レスポンス例：**
```json
{
    "result": "菊池代表の今週の予定は以下の通りです:\n- 会議 1\n  時間: 2026-04-03T10:00:00〜2026-04-03T11:00:00\n..."
}
```

#### LINE Bot のテスト

```bash
# ヘルスチェック
curl http://localhost:8080/

# LINE Webhook をシミュレート
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: your-signature-here" \
  -d '{
    "events": [
      {
        "type": "message",
        "replyToken": "test-token",
        "message": {
          "type": "text",
          "text": "明日の予定は？"
        }
      }
    ]
  }'
```

## 🔍 ログ確認

### 秘書 AI エージェント

```bash
# ターミナル 1 の出力を確認
# ステップ実行ログが表示されます
```

### LINE Bot

```bash
# ターミナル 2 の出力を確認
# Webhook 受信ログが表示されます
```

## 🐛 トラブルシューティング

### 秘書 AI が起動しない

```
ERROR: Anthropic クライアント初期化エラー
```

**対処：**
1. ANTHROPIC_API_KEY が設定されているか確認
2. `.env` ファイルが正しく読み込まれているか確認
3. `pip install -r requirements.txt` を実行

### Gmail 認証エラー

```
ERROR: Gmail 認証情報エラー
```

**対処：**
1. `.env` に GMAIL_REFRESH_TOKEN が設定されているか確認
2. `config/gmail_refresh_token.json` が存在するか確認
3. リフレッシュトークンが有効か確認

### Google Calendar 認証エラー

```
ERROR: Calendar 認証情報エラー: Google Service Account情報が見つかりません
```

**対処：**
1. `config/service_account.json` を配置
2. または GOOGLE_SERVICE_ACCOUNT_JSON 環境変数を設定

### LINE Bot が秘書 AI に接続できない

```
Secretary agent call error: Cannot connect to secretary agent at http://localhost:5000/api/secretary
```

**対処：**
1. 秘書 AI が起動しているか確認（ターミナル 1）
2. SECRETARY_AGENT_URL が正しいか確認
3. ファイアウォール設定を確認

## 📚 便利なコマンド

### ログレベルを上げる

```bash
# 秘書 AI
LOG_LEVEL=DEBUG python api.py

# LINE Bot
LOG_LEVEL=DEBUG python main.py
```

### 単一のツールをテスト

```bash
# Python REPL で直接テスト
python

# Google Calendar をテスト
from tools.calendar import list_calendar_events
print(list_calendar_events(7))

# Gmail をテスト
from tools.gmail import search_emails
print(search_emails("from:example@example.com"))
```

## 🎯 動作確認チェックリスト

- [ ] 秘書 AI が起動できる
- [ ] 秘書 AI ヘルスチェック（/health）が成功
- [ ] LINE Bot が起動できる
- [ ] LINE Bot が秘書 AI に接続できる
- [ ] `curl` で秘書 AI API が呼び出せる
- [ ] Google Calendar から予定が取得できる
- [ ] Gmail からメールが検索できる
- [ ] 実際の LINE から LINE Bot にメッセージを送信できる（要 Cloud Functions デプロイ）

## 🚀 次のステップ

すべてのテストが成功したら、Phase 4 の本番環境へのデプロイに進みます。

---

作成日：2026-04-04
