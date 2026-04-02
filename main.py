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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 環境変数の定義（最初）
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message/reply"

# 関数の定義（その後）
def verify_line_signature(body, signature):
    hash_object = hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    )
    expected_signature = hash_object.digest()
    expected_signature_base64 = base64.b64encode(expected_signature).decode('utf-8')
    return expected_signature_base64 == signature

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
            send_reply_message(reply_token, text)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
