"""
LINE Bot 秘書 - メイン実装
リージョンフードパートナー秘書AI用LINE Bot

機能：
- スケジュール管理（Google Calendar確認）
- メモ記録（memos/フォルダに保存）
- メール確認（Gmail最新メール）
- ちょっとした相談（Claude API利用）
"""

import os
import json
from datetime import datetime
from typing import Optional
from flask import Flask, request, abort

from linebot import Bot, WebhookHandler
from linebot.v3.client import LineBotApi
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import anthropic

# ===== Flask app =====
app = Flask(__name__)

# ===== 設定 =====
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Google APIs認証
def get_google_credentials():
    """Google APIの認証情報を取得"""
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.compose'
        ]
    )
    return credentials

# ===== 機能: スケジュール確認 =====
def get_today_schedule() -> str:
    """本日のスケジュールを Google Calendar から取得"""
    try:
        creds = get_google_credentials()
        service = build('calendar', 'v3', credentials=creds)

        # 本日の日付
        today = datetime.now().date()
        start_time = f"{today}T00:00:00+09:00"
        end_time = f"{today}T23:59:59+09:00"

        events = service.events().list(
            calendarId='primary',
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        items = events.get('items', [])

        if not items:
            return "本日は予定がありません。"

        schedule_text = "本日のスケジュール：\n"
        for event in items:
            start = event['start'].get('dateTime', event['start'].get('date'))
            title = event.get('summary', 'タイトルなし')
            # 時刻部分だけ抽出（ISO形式から）
            if 'T' in start:
                time_str = start.split('T')[1][:5]
            else:
                time_str = "終日"
            schedule_text += f"• {time_str} {title}\n"

        return schedule_text.strip()

    except Exception as e:
        return f"スケジュール取得中にエラーが発生しました：{str(e)}"

# ===== 機能: メール確認 =====
def get_latest_emails(limit: int = 3) -> str:
    """Gmail から最新メールを取得"""
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)

        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=limit
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return "新しいメールはありません。"

        email_text = "最新のメール：\n"
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = msg_data['payload']['headers']
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '不明')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '（なし）')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

            email_text += f"• From: {sender}\n  Subject: {subject}\n"

        return email_text.strip()

    except Exception as e:
        return f"メール取得中にエラーが発生しました：{str(e)}"

# ===== 機能: メモ記録 =====
def save_memo(memo_text: str) -> str:
    """メモをファイルに保存"""
    try:
        memo_dir = "/tmp/memos"  # Lambda環境での一時保存（本番はS3推奨）
        os.makedirs(memo_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{memo_dir}/{timestamp}_memo.txt"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"記録時刻：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"内容：{memo_text}\n")

        return f"メモを記録しました：{memo_text}"

    except Exception as e:
        return f"メモ保存中にエラーが発生しました：{str(e)}"

# ===== 機能: ちょっとした相談 =====
def ask_consultation(question: str) -> str:
    """Claude APIを使用して相談に対応"""
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""あなたはリージョンフードパートナーの秘書AIです。
菊池代表から以下の相談を受けました。簡潔に答えてください。

相談：{question}

回答："""
                }
            ]
        )

        return message.content[0].text

    except Exception as e:
        return f"相談処理中にエラーが発生しました：{str(e)}"

# ===== メッセージ処理 =====
def process_message(text: str) -> str:
    """受け取ったメッセージをキーワード判定して処理"""
    text_lower = text.lower()

    # スケジュール確認
    if any(kw in text_lower for kw in ["予定", "スケジュール", "今日", "カレンダー"]):
        return get_today_schedule()

    # メール確認
    elif any(kw in text_lower for kw in ["メール", "mail", "メッセージ"]):
        return get_latest_emails()

    # メモ記録
    elif text.startswith("メモ："):
        memo_content = text.replace("メモ：", "").strip()
        return save_memo(memo_content)

    # 相談
    else:
        return ask_consultation(text)

# ===== Webhook ハンドラー =====
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """テキストメッセージを受け取ったときの処理"""
    user_message = event.message.text

    # メッセージを処理
    response_text = process_message(user_message)

    # LINE に返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_text)
    )

# ===== Flask エンドポイント =====
@app.route("/webhook", methods=['POST'])
def webhook():
    """LINE Webhook エンドポイント"""

    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(403)

    return 'OK', 200

@app.route("/health", methods=['GET'])
def health():
    """ヘルスチェック"""
    return {'status': 'ok'}, 200

# ===== ローカル実行用 =====
if __name__ == "__main__":
    # ローカルでの実行
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
