# LINE Bot 秘書 - Railway.app デプロイメントガイド

**作成日：** 2026-04-02
**期限：** 本日 9:00 運用開始
**プラットフォーム：** Railway.app（無料）

---

## 📋 デプロイ前の準備物チェック

以下がすべて揃っているか確認してください：

- [x] LINE Business Account 作成済み
- [x] LINE Channel Access Token 取得済み
- [x] LINE Channel Secret 取得済み
- [x] Google Service Account キー（JSON）取得済み
- [x] Anthropic API キー取得済み
- [ ] Railway.app アカウント（新規作成予定）
- [ ] GitHub アカウント（推奨：コード管理用）

---

## 🚀 デプロイ手順（全体で約30分）

### ステップ 1️⃣: Railway.app にサインアップ

1. **Railway.app にアクセス**
   - URL: https://railway.app
   - 右上の **Sign Up** をクリック

2. **ログイン方法を選択**
   - **GitHub** でログイン（推奨）
   - または Google でログイン

3. リダイレクト後、ダッシュボードが表示される ✅

---

### ステップ 2️⃣: GitHub に LINE Bot コードをアップロード

Railway.app は GitHub リポジトリから自動でデプロイするため、まず GitHub にコードをアップロードします。

#### 2-1: GitHub リポジトリ作成

1. **GitHub にサインイン**
   - URL: https://github.com/login

2. **新しいリポジトリを作成**
   - 左上の **+** アイコン → **New repository**
   - リポジトリ名：`line-bot-secretary`
   - 説明：`Line Bot 秘書 - RFP 用`
   - **Public** を選択
   - **Create repository** をクリック

#### 2-2: ローカルからコードをプッシュ

ターミナルで以下のコマンドを実行：

```bash
# 作業ディレクトリに移動
cd "C:\Users\kikuc\OneDrive\デスクトップ\Claude Code\projects\LINE_Bot_秘書"

# Git リポジトリを初期化
git init

# GitHub リポジトリをリモートに設定
git remote add origin https://github.com/{YourUsername}/line-bot-secretary.git

# ファイルをステージング
git add .

# コミット
git commit -m "Initial commit: LINE Bot Secretary"

# メインブランチにプッシュ
git branch -M main
git push -u origin main
```

> ✅ GitHub リポジトリにコードがアップロードされました！

---

### ステップ 3️⃣: Railway.app でプロジェクト作成

1. **Railway ダッシュボードに戻る**
   - https://railway.app/dashboard

2. **新しいプロジェクトを作成**
   - **New Project** をクリック

3. **デプロイ方法を選択**
   - **GitHub Repo** をクリック

4. **GitHub リポジトリを接続**
   - **Configure GitHub App** をクリック
   - GitHub 認可画面で **Authorize railway** をクリック
   - リポジトリリストから `line-bot-secretary` を選択
   - **Deploy** をクリック

> ⏳ Railway が自動で Python コードをビルド・デプロイします（2～5分）

---

### ステップ 4️⃣: 環境変数を設定

デプロイ完了後、環境変数を設定します。

1. **Railway ダッシュボード**
   - プロジェクト `line-bot-secretary` をクリック

2. **Environment Variables を開く**
   - 左側メニューから **Variables** をクリック

3. **以下の環境変数を追加**

```
LINE_CHANNEL_ACCESS_TOKEN = （LINE Developers から取得した Token）
LINE_CHANNEL_SECRET = （LINE Developers から取得した Secret）
GOOGLE_SERVICE_ACCOUNT_JSON = （Google JSON ファイル全体をコピペ）
ANTHROPIC_API_KEY = （Anthropic から取得した API キー）
```

> 例：
> ```
> LINE_CHANNEL_ACCESS_TOKEN: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
> LINE_CHANNEL_SECRET: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
> GOOGLE_SERVICE_ACCOUNT_JSON: {"type": "service_account", "project_id": "...", ...}
> ANTHROPIC_API_KEY: sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
> ```

4. **Save を押す**
   - Railway が自動で再デプロイされます

---

### ステップ 5️⃣: Webhook URL を確認

1. **Railway ダッシュボード**
   - 左側メニューから **Deployments** をクリック

2. **アプリケーションの URL を確認**
   - 画面に表示される URL をコピー（例：`https://line-bot-secretary-production.up.railway.app`）

3. **Webhook URL を構成**
   - LINE Bot 用の Webhook URL：`https://line-bot-secretary-production.up.railway.app/webhook`

---

### ステップ 6️⃣: LINE Developers で Webhook URL を設定

1. **LINE Developers にログイン**
   - URL: https://developers.line.biz/ja/

2. **チャネル設定を開く**
   - リージョンフードパートナー → Messaging API チャネル → **チャネル設定**

3. **Webhook URL を設定**
   - **Webhook設定** セクションを探す
   - Webhook URL 欄に以下を入力：
     ```
     https://line-bot-secretary-production.up.railway.app/webhook
     ```

4. **Webhook を有効化**
   - **Webhook を使用** を **オン** に切り替える
   - **Webhook URL の検証** をクリック（✓ 成功 が表示されればOK）

---

### ステップ 7️⃣: 実機テスト

1. **LINE アプリで秘書 Bot を友だち追加**

2. **テストメッセージを送信**

```
【テスト1】スケジュール確認
送信：「今日の予定は？」
期待：本日のスケジュールが表示される

【テスト2】メール確認
送信：「メールを見て」
期待：最新メール 3 件が表示される

【テスト3】メモ記録
送信：「メモ：新店舗について営業会議で確認」
期待：「メモを記録しました：...」と返信

【テスト4】相談
送信：「新商品の販促案について、いい案ありますか？」
期待：Claude AI からの提案が返信される
```

すべてのテストが成功したら **完成** ✅

---

## 🔧 トラブルシューティング

### LINE から返信がない

**原因1：Webhook URL が正しく設定されていない**
- 対策：LINE Developers で `Webhook URL の検証` をクリック
- エラーが出たら、Railway の Deployment URL を確認し直す

**原因2：環境変数が設定されていない**
- 対策：Railway ダッシュボード → Variables を確認
- すべての変数が正しく入力されているか確認

**原因3：Railway のビルドが失敗している**
- 対策：Railway ダッシュボール → Deployments を確認
- **Build Logs** を見て、エラーメッセージを確認

### エラーメッセージが表示される

**エラー：`Invalid signature`**
- 原因：LINE_CHANNEL_SECRET が間違っている
- 対策：LINE Developers から正しい Secret をコピーし直す

**エラー：`401 Unauthorized (Google API)`**
- 原因：GOOGLE_SERVICE_ACCOUNT_JSON が無効
- 対策：Google Cloud Console で新しい JSON キーを作成

**エラー：`401 Unauthorized (Anthropic API)`**
- 原因：ANTHROPIC_API_KEY が間違っている
- 対策：Anthropic コンソールから新しい API キーを取得

---

## 📊 デプロイ完了チェックリスト

本日 9:00 に向けて、以下をすべて完了してください：

- [ ] GitHub に `line-bot-secretary` リポジトリを作成
- [ ] ローカルコードを GitHub にプッシュ
- [ ] Railway.app でプロジェクトを作成
- [ ] Railway で環境変数を設定
- [ ] Webhook URL を確認
- [ ] LINE Developers で Webhook URL を設定
- [ ] `Webhook URL の検証` が成功
- [ ] 実機テスト 4 ケース すべて成功
- [ ] 本運用開始 🚀

---

## 💡 本運用開始後の確認事項

1. **秘書AI への連絡**
   - LINE Bot が使用可能になったことを通知

2. **ユーザー（菊池代表）への説明**
   - LINE Bot の基本的な使い方（キーワード）を説明
   - 予期しない動作があれば報告を依頼

3. **ログ監視**
   - Railway ダッシュボール → **Logs** で実行ログを確認
   - エラーがないか定期的に確認

4. **メモ保存先の設定（本番対応）**
   - 現在：`/tmp/memos` に一時保存（再起動で削除される）
   - 本番：memos/ ディレクトリに保存（Git 管理または外部ストレージ推奨）

---

## 🌐 Railway.app のメリット

| 項目 | 内容 |
|-----|------|
| **料金** | 完全無料（月 $5 相当の無料クレジット） |
| **セットアップ** | GitHub 接続で自動デプロイ |
| **スケーリング** | 自動スケール対応 |
| **カスタムドメイン** | 無料で設定可能 |
| **ログ管理** | ダッシュボードから確認可能 |

---

## 📞 問い合わせ

デプロイ中に問題が発生した場合：
1. このガイドのトラブルシューティングセクションを確認
2. Railway ダッシュボール → **Logs** で詳細を確認
3. 秘書AI に相談

**がんばってください！** 🚀

---

**Version：** 2.0 (Railway.app 対応)
**作成者：** Claude AI
