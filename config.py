"""
LINE Bot 秘書 - 設定ファイル
"""

import os

# ===== LINE 設定 =====
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# ===== Google API 設定 =====
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_CALENDAR_ID = "primary"

# ===== Anthropic API 設定 =====
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-opus-4-6"

# ===== アプリケーション設定 =====
MAX_EMAIL_LIMIT = 3  # メール確認時の最大件数
MEMO_DIR = "/tmp/memos"  # メモ保存ディレクトリ
TIMEZONE = "Asia/Tokyo"

# ===== キーワード定義 =====
KEYWORDS = {
    "schedule": ["予定", "スケジュール", "今日", "カレンダー", "予定は", "schedule"],
    "email": ["メール", "mail", "メッセージ", "email"],
    "memo": ["メモ", "memo"],
    "consultation": []  # そのほかすべて
}
