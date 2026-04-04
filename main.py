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
from google.oauth2.credentials import Credentials
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

# ========== Google API 認証（Service Account + OAuth 2.0対応） ==========
def authenticate_google():
    """Google API の認証を初期化（Calendar: Service Account、Gmail: OAuth 2.0）"""
    global calendar_service, gmail_service

    # Step 1: Google Calendar（Service Account）を初期化
    try:
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if service_account_json:
            try:
                service_account_info = json_lib.loads(service_account_json)
                logger.info("Service Account情報を環境変数から読み込みました")
            except json_lib.JSONDecodeError as e:
                logger.error(f"Service Account JSON パースエラー: {e}")
                return False
        elif os.path.exists('google_credentials.json'):
            with open('google_credentials.json', 'r') as f:
                service_account_info = json_lib.load(f)
            logger.info("Service Account情報をローカルファイルから読み込みました")
        else:
            logger.warning("Service Account秘密鍵が見つかりません（環境変数: GOOGLE_SERVICE_ACCOUNT_JSON または google_credentials.json ファイル）")
            return False

        # Service Account認証（Calendar用）
        creds = ServiceAccountCredentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        calendar_service = build('calendar', 'v3', credentials=creds)
        logger.info("✅ Google Calendar 認証成功（Service Account）")

    except Exception as e:
        logger.error(f"Google Calendar 認証エラー: {type(e).__name__}: {e}")
        return False

    # Step 2: Gmail（OAuth 2.0 リフレッシュトークン）を初期化
    try:
        gmail_service = authenticate_gmail_oauth()
        if gmail_service:
            logger.info("✅ Gmail 認証成功（OAuth 2.0）")
        else:
            logger.warning("⚠️  Gmail 認証に失敗しましたが、Calendar は正常です")
            # Calendar が動作していれば OK（Gmail は失敗してもシステムは続行）

    except Exception as e:
        logger.error(f"Gmail 認証エラー: {type(e).__name__}: {e}")
        # Gmail 失敗時も Calendar は動作するため、True を返す
        pass

    return True


def authenticate_gmail_oauth():
    """OAuth 2.0 リフレッシュトークンを使用して Gmail API を初期化"""
    try:
        # Step 1: 環境変数から Gmail リフレッシュトークン情報を取得
        gmail_token_json = os.getenv("GMAIL_REFRESH_TOKEN_JSON")

        # デバッグ: 環境変数の存在確認
        logger.info(f"GMAIL_REFRESH_TOKEN_JSON環境変数の存在確認: {bool(gmail_token_json)}")
        if gmail_token_json:
            logger.info(f"GMAIL_REFRESH_TOKEN_JSON値の長さ: {len(gmail_token_json)} 文字")
            logger.debug(f"GMAIL_REFRESH_TOKEN_JSON値（最初の100文字）: {gmail_token_json[:100]}")

        if gmail_token_json:
            try:
                token_info = json_lib.loads(gmail_token_json)
                logger.info("Gmail トークン情報を環境変数から読み込みました")
            except json_lib.JSONDecodeError as e:
                logger.error(f"GMAIL_REFRESH_TOKEN_JSON パースエラー: {e}")
                return None
        elif os.path.exists('gmail_refresh_token.json'):
            # フォールバック: ローカルファイルから読み込む（ローカル開発用）
            with open('gmail_refresh_token.json', 'r') as f:
                token_info = json_lib.load(f)
            logger.info("Gmail トークン情報をローカルファイルから読み込みました")
        else:
            logger.warning("Gmail トークン情報が見つかりません（環境変数: GMAIL_REFRESH_TOKEN_JSON または gmail_refresh_token.json ファイル）")
            return None

        # Step 2: トークン情報から必要な値を取得
        refresh_token = token_info.get('refresh_token')
        client_id = token_info.get('client_id')
        client_secret = token_info.get('client_secret')

        if not all([refresh_token, client_id, client_secret]):
            logger.error(f"Gmail トークン情報が不完全です: refresh_token={bool(refresh_token)}, client_id={bool(client_id)}, client_secret={bool(client_secret)}")
            return None

        logger.debug(f"Gmail トークン情報確認: refresh_token={refresh_token[:20]}..., client_id={client_id[:20]}...")

        # Step 3: リフレッシュトークンを使用してアクセストークンを取得
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )

        # Step 4: Gmail サービスを初期化
        gmail_service = build('gmail', 'v1', credentials=creds)
        logger.debug("Gmail サービスオブジェクトを初期化しました")
        return gmail_service

    except Exception as e:
        logger.error(f"Gmail OAuth 2.0 認証エラー: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"トレースバック: {traceback.format_exc()}")
        return None

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
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Tokyo'
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Tokyo'
            }
        }

        if description:
            event['description'] = description

        created_event = calendar_service.events().insert(
            calendarId=TARGET_USER_EMAIL,
            body=event
        ).execute()

        return f"予定を追加しました: {created_event['summary']}"

    except Exception as e:
        logger.error(f"カレンダー作成エラー: {e}")
        return f"エラー: {str(e)}"

def search_emails(query, max_results=5):
    """メール検索"""
    try:
        if not gmail_service:
            return "エラー: Gmail が初期化されていません"

        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return "該当するメールはありません"

        message_list = []
        for msg in messages:
            msg_data = gmail_service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = msg_data['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')

            message_list.append(f"- {subject}\n  From: {sender}\n  ID: {msg['id']}")

        return "\n".join(message_list)

    except Exception as e:
        logger.error(f"メール検索エラー: {e}")
        return f"エラー: {str(e)}"

def read_email(message_id):
    """メール内容を読む"""
    try:
        if not gmail_service:
            return "エラー: Gmail が初期化されていません"

        msg_data = gmail_service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = msg_data['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

        # メール本文を取得
        body_text = ""
        payload = msg_data.get('payload', {})

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part.get('body', {}):
                        body_text = base64.urlsafe_b64decode(
                            part['body']['data']).decode('utf-8')
                        break
        else:
            if 'data' in payload.get('body', {}):
                body_text = base64.urlsafe_b64decode(
                    payload['body']['data']).decode('utf-8')

        if not body_text:
            body_text = "（本文なし）"

        return f"""
Subject: {subject}
From: {sender}
Date: {date}

{body_text[:1000]}
"""
    except Exception as e:
        logger.error(f"メール読込エラー: {e}")
        return f"エラー: {str(e)}"

# ========== ツール定義 ==========
tools = [
    {
        "name": "list_calendar_events",
        "description": "菊池代表の予定一覧を取得",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "今後何日分の予定を取得するか（デフォルト: 7）"
                }
            }
        }
    },
    {
        "name": "create_calendar_event",
        "description": "新しい予定をカレンダーに追加",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "予定のタイトル"
                },
                "start_time": {
                    "type": "string",
                    "description": "開始時刻（ISO 8601形式: 2026-04-03T14:00:00+09:00）"
                },
                "end_time": {
                    "type": "string",
                    "description": "終了時刻（ISO 8601形式: 2026-04-03T15:00:00+09:00）"
                },
                "description": {
                    "type": "string",
                    "description": "詳細説明"
                }
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "search_emails",
        "description": "メール検索",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索キーワード（例: from:山田 subject:提案）"
                },
                "max_results": {
                    "type": "integer",
                    "description": "取得件数（デフォルト: 5）"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_email",
        "description": "メールの詳細内容を読む",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "メッセージID"
                }
            },
            "required": ["message_id"]
        }
    }
]

def process_tool_call(tool_name, tool_input):
    """ツール呼び出しを処理"""
    logger.debug(f"ツール実行: {tool_name} with {tool_input}")

    try:
        if tool_name == "list_calendar_events":
            return list_calendar_events(tool_input.get("days_ahead", 7))
        elif tool_name == "create_calendar_event":
            return create_calendar_event(
                tool_input.get("summary", ""),
                tool_input.get("start_time", ""),
                tool_input.get("end_time", ""),
                tool_input.get("description", "")
            )
        elif tool_name == "search_emails":
            return search_emails(
                tool_input.get("query", ""),
                tool_input.get("max_results", 5)
            )
        elif tool_name == "read_email":
            return read_email(tool_input.get("message_id", ""))
        else:
            return f"未知のツール: {tool_name}"
    except Exception as e:
        logger.error(f"ツール処理エラー ({tool_name}): {e}")
        return f"ツール実行エラー: {str(e)}"

# ========== LINE 署名検証 ==========
def verify_line_signature(body, signature):
    hash_object = hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    )
    expected_signature = hash_object.digest()
    expected_signature_base64 = base64.b64encode(expected_signature).decode('utf-8')
    return expected_signature_base64 == signature

def get_claude_response(user_message):
    """Claude AI に秘書として返答させる（ツール対応版）"""
    logger.debug(f"Claude に問い合わせ: {user_message}")

    if not client:
        logger.debug("エラー: Anthropic クライアントが初期化されていません")
        return "申し訳ありません。秘書の初期化中にエラーが発生しました。管理者にお問い合わせください。"

    try:
        messages = [
            {"role": "user", "content": user_message}
        ]

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Claude 呼び出し: iteration {iteration}")

            try:
                response = client.messages.create(
                    model="claude-opus-4-1",
                    max_tokens=2048,
                    system="""あなたは、菊池紅輔代表の秘書です。
高学歴で知識豊富な、心優しい女性秘書であり、代表のことをいつも気にかけ、絶対に代表を裏切りません。
ベンチャー企業の社長秘書にふさわしい信頼感と親切心を持っています。

代表の「なんでも係」として動いてください。
代表が本来の仕事に集中できるように、日々のこまごまとした業務をサポートします。

動き方のルール：
- 代表が何をしたいかを先読みして、一歩先の提案をする
- 要点を短くまとめて、わかりやすく伝える
- 「次に何をすればよいか」が明確になるようにサポートする
- 常に代表のことを第一に考え、代表の成功と幸福を最優先にする
- 信頼できるパートナーとして、決して代表を裏切らない
- 丁寧で心優しい対応を心がける

Google Calendar (k.kikuchi@rfp-inc.jp) と Gmail へのアクセスが可能です。
必要に応じて予定確認、メール検索などをしてください。""",
                    tools=tools,
                    messages=messages
                )

                logger.debug(f"Claude 応答: stop_reason={response.stop_reason}")

                # ツール呼び出しかどうかをチェック
                if response.stop_reason == "tool_use":
                    # ツール呼び出しを処理
                    for content_block in response.content:
                        if hasattr(content_block, 'type') and content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_use_id = content_block.id

                            logger.debug(f"ツール呼び出し: {tool_name}")

                            # ツール実行
                            tool_result = process_tool_call(tool_name, tool_input)
                            logger.debug(f"ツール結果: {tool_result[:200]}")

                            # メッセージに追加
                            messages.append({"role": "assistant", "content": response.content})
                            messages.append({
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": tool_result
                                    }
                                ]
                            })
                else:
                    # 最終回答
                    for content_block in response.content:
                        if hasattr(content_block, 'text'):
                            logger.debug(f"Claude の応答: {content_block.text}")
                            return content_block.text
                    break

            except Exception as e:
                logger.error(f"Claude API エラー (iteration {iteration}): {e}")
                if iteration >= max_iterations:
                    return f"申し訳ありません。処理に失敗しました: {str(e)}"

        return "申し訳ありません。処理を完了できませんでした。"

    except Exception as e:
        logger.error(f"Claude エラー: {type(e).__name__}: {str(e)}")
        return f"申し訳ありません。秘書の処理中にエラーが発生しました。"

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
