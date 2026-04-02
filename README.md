# LINE Bot 秘書 🤖

リージョンフードパートナー秘書AI用 LINE Bot

---

## 📋 概要

菊池代表が LINE から秘書AI に指示・相談できる Bot です。

**主な機能：**
- ✅ スケジュール管理（Google Calendar連携）
- ✅ メモ記録（memos/フォルダに保存）
- ✅ メール確認（Gmail連携）
- ✅ ちょっとした相談（Claude AI対応）

---

## 🚀 クイックスタート

### 前提条件
- Python 3.11+
- Railway.app アカウント（無料）
- GitHub アカウント（推奨：コード管理用）
- LINE Business Account
- Google Service Account キー
- Anthropic API キー

### デプロイ（約30分）

**詳細手順は `DEPLOYMENT_GUIDE.md` を参照してください。**

簡潔には：
1. GitHub に `line-bot-secretary` リポジトリを作成してコードをプッシュ
2. Railway.app でプロジェクトを作成（GitHub 自動連携）
3. 環境変数を Railway に設定
4. Webhook URL を LINE Developers に設定
5. 実機テストで動作確認

---

## 💬 使用方法（ユーザー向け）

### スケジュール確認
```
菊池：「今日の予定は？」
Bot：「本日のスケジュール：
• 10:00 営業会議
• 14:00 経営会議」
```

### メール確認
```
菊池：「メールを見て」
Bot：「最新のメール：
• From: 営業先@example.com
  Subject: 新規案件について」
```

### メモ記録
```
菊池：「メモ：新店舗の構想について営業会議で確認」
Bot：「メモを記録しました：新店舗の構想について営業会議で確認」
```

### 相談
```
菊池：「新商品の販促案について、いい案ありますか？」
Bot：「以下の販促案をお勧めします：
1. SNS キャンペーン...」
```

---

## 🔧 ファイル構成

```
projects/LINE_Bot_秘書/
├── main.py                    # メインコード（Flask サーバー）
├── config.py                  # 設定ファイル
├── requirements.txt           # Python 依存パッケージ
├── Procfile                   # Railway デプロイメント設定
├── DEPLOYMENT_GUIDE.md        # Railway.app デプロイ詳細手順
└── README.md                  # このファイル
```

---

## 🔑 環境変数

Railway.app のダッシュボードで以下の環境変数を設定してください：

| 環境変数 | 説明 | 取得元 |
|---------|------|--------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Channel Access Token | LINE Developers |
| `LINE_CHANNEL_SECRET` | LINE Channel Secret | LINE Developers |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Service Account JSON 全体 | Google Cloud Console |
| `ANTHROPIC_API_KEY` | Anthropic API キー | Anthropic |

---

## 🧪 テスト

### ローカルテスト
```bash
# 環境変数を設定
export LINE_CHANNEL_ACCESS_TOKEN="your_token"
export LINE_CHANNEL_SECRET="your_secret"
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
export ANTHROPIC_API_KEY="your_key"

# サーバー起動
python main.py
```

### Railway でのテスト
1. LINE アプリで秘書 Bot を友だち追加
2. テストメッセージを送信
3. Railway ダッシュボール → **Logs** でログを確認

---

## 📊 ログ監視

Railway ダッシュボードで実行ログを確認：
```
Railway Dashboard → プロジェクト → Deployments → Logs
```

---

## 🚀 ロードマップ

### Phase 1 (本日 9:00～)
- [x] MVP機能実装
- [x] AWS Lambda デプロイ
- [x] 本運用開始

### Phase 2 (1週間後)
- [ ] 自然言語処理強化（複合キーワード対応）
- [ ] エラーハンドリング拡張
- [ ] メール返信下書き機能
- [ ] セキュリティレビュー

### Phase 3 (1ヶ月後)
- [ ] ログ・分析機能
- [ ] 複数案件同時対応
- [ ] 各AI社員との連携自動化
- [ ] 本運用化（安定版）

---

## ⚠️ セキュリティに関する注意

- ❌ **Git リポジトリに環境変数を保存しないこと**
- ✅ AWS Lambda の環境変数設定機能を使用
- ✅ Channel Access Token は定期的に更新
- ✅ Service Account キーは安全に管理

---

## 🐛 トラブルシューティング

問題が発生した場合：

1. **DEPLOYMENT_GUIDE.md** のトラブルシューティングセクションを確認
2. **CloudWatch ログ** で詳細を確認
3. 秘書AI に相談

---

## 📞 サポート

質問や問題があれば、秘書AI に相談してください。

---

**作成日：** 2026-04-02
**Version：** 1.0 (MVP - Railway.app 版)
**プラットフォーム：** Railway.app（無料）
