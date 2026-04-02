from flask import Flask, request
import hmac
import hashlib
import base64
import json
import requests
import os

app = Flask(__name__)

# 環境変数の定義（最初）
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.biz/v2/bot/message/reply"

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
    print("DEBUG: Webhook received")
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")
    
    print(f"DEBUG: Body: {body}")
    print(f"DEBUG: Signature: {signature}")
    
    if not verify_line_signature(body, signature):
        print("DEBUG: Signature verification failed")
        return "Unauthorized", 401
    
    print("DEBUG: Signature verified")
    
    try:
        events = json.loads(body).get("events", [])
        print(f"DEBUG: Events: {events}")
    except Exception as e:
        print(f"DEBUG: JSON parse error: {e}")
        return "Bad Request", 400
    
    for event in events:
        event_type = event.get("type")
        print(f"DEBUG: Event type: {event_type}")
        
        if event_type == "message":
            reply_token = event.get("replyToken")
            message = event.get("message", {})
            text = message.get("text", "メッセージが空です")
            print(f"DEBUG: Message received: {text}")
            send_reply_message(reply_token, text)
        
        elif event_type == "follow":
            reply_token = event.get("replyToken")
            print("DEBUG: Follow event")
            send_reply_message(reply_token, "フォローありがとうございます！秘書AIです。何かお手伝いできることはありますか？")
    
    return "OK", 200

def send_reply_message(reply_token, text):
    print(f"DEBUG: Sending message: {text}")
    
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
        print(f"DEBUG: LINE API URL: {LINE_API_URL}")
        print(f"DEBUG: Token exists: {bool(CHANNEL_ACCESS_TOKEN)}")
        response = requests.post(LINE_API_URL, json=payload, headers=headers, timeout=10)
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response: {response.text}")
    except Exception as e:
        print(f"DEBUG: Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
