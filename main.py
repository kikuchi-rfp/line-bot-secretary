#!/usr/bin/env python3
"""
LINE Bot 秘書 - Google Calendar/Gmail 統合版
Cloud Functions対応の統合バックエンド
"""

from flask import Flask, request
import hmac
import hashlib
import base64
import json
import requests
import os
import logging
import sys
from datetime import datetime, timedelta

from anthropic import Anthropic
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json as json_lib

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ========== 環境変数設定 ==========
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Google API スコープ
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify'
]

# 対象ユーザーメールアドレス（Service Account委譲認証用）
TARGET_USER_EMAIL = "k.kikuchi@rfp-inc.jp"

# Google API クライアント（グローバル）
calendar_service = None
gmail_service = None

# Claude クライアント初期化（遅延初期化）
client = None
try:
    client = Anthropic()
    logger.debug("Anthropic クライアント初期化成功")
except Exception as e:
    logger.debug(f"Anthropic クライアント初期化エラー: {type(e).__name__}: {str(e)}")

# ========== Google API 認証（Service Account対応） ==========
def authenticate_google():
    """Google API の認証を初期化（Service Account認証）"""
    global calendar_service, gmail_service

    try:
        # 環境変数から Service Account 秘密鍵を取得
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if service_account_json:
            # 環境変数から秘密鍵情報をパース
            try:
                service_account_info = json_lib.loads(service_account_json)
                logger.info("Service Account情報を環境変数から読み込みました")
            except json_lib.JSONDecodeError as e:
                logger.error(f"Service Account JSON パースエラー: {e}")
                return False
        elif os.path.exists('google_credentials.json'):
            # ローカルファイルから秘密鍵を読み込む（開発環境用）
            with open('google_credentials.json', 'r') as f:
                service_account_info = json_lib.load(f)
            logger.info("Service Account情報をローカルファイルから読み込みました")
        else:
            logger.warning("Service Account秘密鍵が見つかりません（環境変数: GOOGLE_SERVICE_ACCOUNT_JSON または google_credentials.json ファイル）")
            return False

        # Service Account認証
        creds = ServiceAccountCredentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        # Google Calendar と Gmail のクライアントを初期化
        calendar_service = build('calendar', 'v3', credentials=creds)
        gmail_service = build('gmail', 'v1', credentials=creds)

        logger.info("✅ Google API 認証成功（Service Account）")
        return True

    except Exception as e:
        logger.error(f"Google API 認証エラー: {type(e).__name__}: {e}")
        return False

# ========== Google API ツール実装 ==========
def list_calendar_events(days_ahead=7):
    """カレンダーイベント一覧を取得"""
    try:
        if not calendar_service:
            return "エラー: Google Calendar が初期化されていません"

        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

        events_result = calendar_service.events().list(
            calendarId=TARGET_USER_EMAIL,
            timeMin=now,
            timeMax=end,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return "予定がありません"

        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end_time = event['end'].get('dateTime', event['end'].get('date'))
            title = event.get('summary', '（タイトルなし）')
            event_list.append(f"- {title}\n  時間: {start}〜{end_time}")

        return "\n".join(event_list)

    except HttpError as e:
        error_content = e.content.decode('utf-8')
        logger.error(f"Calendar API エラー: {error_content}")
        return f"予定取得エラー: {str(e)}"
    except Exception as e:
        logger.error(f"予定取得エラー: {e}")
        return f"予定取得エラー: {str(e)}"

def create_calendar_event(summary, start_time, end_time, description=""):
    """カレンダーイベントを作成"""
    try:
        if not calendar_service:
            return "エラー: Google Calendar が初期化されていません"

        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'Asia/Tokyo'},
            'end': {'dateTime': end_time, 'timeZone': 'Asia/Tokyo'}
        }

        created_event = calendar_service.events().insert(
            calendarId=TARGET_USER_EMAIL,
            body=event
        ).execute()

        logger.info(f"カレンダーイベント作成: {created_event.get('summary')}")
        return f"📅 『{summary}』を予定に追加しました"

    except HttpError as e:
        logger.error(f"Calendar API エラー: {e}")
        return f"予定作成エラー: {str(e)}"
    except Exception as e:
        logger.error(f"予定作成エラー: {e}")
        return f"予定作成エラー: {str(e)}"

def get_gmail_unread_count():
    """未読メール数を取得"""
    try:
        if not gmail_service:
            return "エラー: Gmail が初期化されていません"

        results = gmail_service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()

        unread_count = results.get('resultSizeEstimate', 0)
        logger.info(f"未読メール数: {unread_count}")
        return f"📧 未読メール: {unread_count}件"

    except HttpError as e:
        logger.error(f"Gmail API エラー: {e}")
        return f"メール確認エラー: {str(e)}"
    except Exception as e:
        logger.error(f"メール確認エラー: {e}")
        return f"メール確認エラー: {str(e)}"

# ========== LINE Signature 検証 ==========
def verify_line_signature(body, signature):
    """LINE メッセージの署名検証"""
    hash_object = hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    )
    expected_signature = hash_object.digest()
    expected_signature_base64 = base64.b64encode(expected_signature).decode('utf-8')
    return expected_signature_base64 == signature

# ========== Claude AI 秘書 ==========
def get_claude_response(user_message):
    """Claude AI に秘書として返答させる"""
    logger.debug(f"Claude に問い合わせ: {user_message}")

    if not client:
        logger.debug("エラー: Anthropic クライアントが初期化されていません")
        return "申し訳ありません。秘書の初期化中にエラーが発生しました。"

    try:
        # Google API が利用可能か確認
        system_prompt = """あなたは、菊池紅輔代表の秘書です。
高学歴で知識豊富な、心優しい女性秘書であり、代表のことをいつも気にかけ、絶対に代表を裏切りません。

代表の以下の質問に対応できます：
1. 【スケジュール確認】「今週の予定は？」「明日の予定は？」
2. 【メール確認】「未読メールは何件？」
3. 【一般的なサポート】その他の業務支援

スケジュール確認や未読メール確認の時は、適切なツールを活用して、最新情報を提供してください。
代表が本来の仕事に集中できるようにサポートします。"""

        # ユーザーメッセージを分析
        if "予定" in user_message or "スケジュール" in user_message:
            calendar_info = list_calendar_events()
            user_message = f"{user_message}\n\n【カレンダー情報】{calendar_info}"
        
        if "メール" in user_message or "未読" in user_message:
            mail_info = get_gmail_unread_count()
            user_message = f"{user_message}\n\n【メール情報】{mail_info}"

        message = client.messages.create(
            model="claude-opus-4-1",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        response_text = message.content[0].text
        logger.debug(f"Claude の応答: {response_text}")
        return response_text

    except Exception as e:
        logger.error(f"Claude API エラー: {type(e).__name__}: {str(e)}")
        return "申し訳ありません。秘書の処理中にエラーが発生しました。"

# ========== Flask ルート ==========
@app.route("/")
def hello():
    return "Hello World!"

@app.route("/webhook", methods=["POST"])
def webhook():
    logger.debug("Webhook received")
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")

    logger.debug(f"Body: {body}")
    logger.debug(f"Signature: {signature}")

    if not verify_line_signature(body, signature):
        logger.debug("Signature verification failed")
        return "Unauthorized", 401

    logger.debug("Signature verified")

    try:
        events = json.loads(body).get("events", [])
        logger.debug(f"Events: {events}")
    except Exception as e:
        logger.debug(f"JSON parse error: {e}")
        return "Bad Request", 400

    for event in events:
        event_type = event.get("type")
        logger.debug(f"Event type: {event_type}")

        if event_type == "message":
            reply_token = event.get("replyToken")
            message = event.get("message", {})
            text = message.get("text", "メッセージが空です")
            logger.debug(f"Message received: {text}")

            # Claude に秘書として返答させる
            ai_response = get_claude_response(text)
            send_reply_message(reply_token, ai_response)

        elif event_type == "follow":
            reply_token = event.get("replyToken")
            logger.debug("Follow event")
            send_reply_message(reply_token, "フォローありがとうございます！秘書AIです。何かお手伝いできることはありますか？")

    return "OK", 200

def send_reply_message(reply_token, text):
    logger.debug(f"Sending message: {text}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }

    try:
        logger.debug(f"LINE API URL: {LINE_API_URL}")
        logger.debug(f"Token exists: {bool(CHANNEL_ACCESS_TOKEN)}")
        response = requests.post(LINE_API_URL, json=payload, headers=headers, timeout=10)
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response: {response.text}")
    except Exception as e:
        logger.debug(f"Error: {type(e).__name__}: {str(e)}")

# ========== アプリケーション初期化 ==========
logger.info("="*60)
logger.info("LINE Bot 秘書 - Google Calendar/Gmail 統合版")
logger.info("="*60)

logger.info("Google API 認証を開始します...")
if authenticate_google():
    logger.info("✅ Google API 認証完了")
else:
    logger.warning("⚠️  Google API の初期化に失敗しました")

if __name__ == "__main__":
    # Flask サーバー起動（ローカル開発環境用）
    logger.info("Flask サーバーを起動します...")
    logger.info(f"Listening on http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
