#!/usr/bin/env python3
"""
LINE Bot - 秘書 AI エージェントプロキシ

役割：LINE Webhook のみを処理し、秘書 AI への REST API 呼び出しを委譲
- LINE Webhook 受信・署名検証
- メッセージ抽出
- 秘書 AI エージェント（secretary-agent002）へ REST API 呼び出し
- LINE Reply API で結果を返信
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

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ========== 環境変数設定 ==========
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"

# 秘書 AI エージェントの URL
# 本番環境: Cloud Run service の URL (例: https://secretary-agent002.run.app)
# ローカル開発: http://localhost:8000
SECRETARY_AGENT_URL = os.getenv(
    "SECRETARY_AGENT_URL",
    "http://localhost:8000"
)

# ========== LINE 署名検証 ==========
def verify_line_signature(body, signature):
    """LINE 署名を検証"""
    try:
        hash_object = hmac.new(
            CHANNEL_SECRET.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        )
        expected_signature = hash_object.digest()
        expected_signature_base64 = base64.b64encode(expected_signature).decode('utf-8')
        return expected_signature_base64 == signature
    except Exception as e:
        logger.error(f"署名検証エラー: {e}")
        return False

# ========== 秘書 AI エージェント呼び出し ==========
def call_secretary_agent(user_message):
    """秘書 AI エージェント（secretary-agent002）を REST API で呼び出し"""
    try:
        logger.info(f"秘書 AI を呼び出し: {user_message[:100]}")

        response = requests.post(
            f"{SECRETARY_AGENT_URL}/api/secretary",
            json={"message": user_message},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json().get("result", "")
            logger.info(f"秘書 AI からの応答: {result[:100]}")
            return result
        else:
            logger.error(
                f"秘書 AI エラー (status={response.status_code}): {response.text}"
            )
            return "申し訳ありません。秘書 AI との通信に問題が発生しました。"

    except requests.exceptions.Timeout:
        logger.error("秘書 AI との通信がタイムアウトしました")
        return "申し訳ありません。処理がタイムアウトしました。"

    except requests.exceptions.ConnectionError as e:
        logger.error(f"秘書 AI との接続エラー: {e}")
        return "申し訳ありません。秘書 AI に接続できません。"

    except Exception as e:
        logger.error(f"秘書 AI 呼び出しエラー: {e}")
        return "申し訳ありません。エラーが発生しました。"

# ========== LINE 返信 ==========
def send_reply_message(reply_token, text):
    """LINE で返信"""
    logger.info(f"LINE で返信: {text[:100]}")

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
        response = requests.post(
            LINE_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            logger.error(
                f"LINE API エラー (status={response.status_code}): {response.text}"
            )

    except Exception as e:
        logger.error(f"LINE 返信エラー: {e}")

# ========== Flask エンドポイント ==========
@app.route("/", methods=["GET"])
def health_check():
    """ヘルスチェック"""
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    LINE Webhook エンドポイント

    LINE メッセージを受け取り、秘書 AI エージェントに処理を委譲
    """
    logger.info("Webhook 受信")

    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")

    # LINE 署名検証
    if not verify_line_signature(body, signature):
        logger.warning("署名検証失敗")
        return "Unauthorized", 401

    logger.info("署名検証成功")

    # JSON パース
    try:
        events = json.loads(body).get("events", [])
    except Exception as e:
        logger.error(f"JSON パースエラー: {e}")
        return "Bad Request", 400

    # イベント処理
    for event in events:
        event_type = event.get("type")
        logger.info(f"イベントタイプ: {event_type}")

        if event_type == "message":
            reply_token = event.get("replyToken")
            message = event.get("message", {})
            user_message = message.get("text", "")

            logger.info(f"メッセージ受信: {user_message}")

            if user_message:
                # 秘書 AI エージェントを呼び出し
                ai_response = call_secretary_agent(user_message)
                # LINE で返信
                send_reply_message(reply_token, ai_response)

        elif event_type == "follow":
            reply_token = event.get("replyToken")
            logger.info("フォローイベント")
            send_reply_message(
                reply_token,
                "フォローありがとうございます！秘書 AI です。何かお手伝いできることはありますか？"
            )

    return "OK", 200

# ========== アプリケーション初期化 ==========
if __name__ == "__main__":
    logger.info("="*60)
    logger.info("LINE Bot - 秘書 AI エージェントプロキシ")
    logger.info("="*60)
    logger.info(f"秘書 AI URL: {SECRETARY_AGENT_URL}")

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Flask サーバーを起動 (http://0.0.0.0:{port})")
    app.run(host="0.0.0.0", port=port, debug=False)
