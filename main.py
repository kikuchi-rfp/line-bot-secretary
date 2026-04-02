from flask import Flask, request
import hmac
import hashlib
import base64
import json
import requests
import os

app = Flask(__name__)

# 環境変数から取得
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.biz/v2/bot/message/reply"

# LINE の署名を検証する関数
def verify_line_signature(body, signature):
    """LINE からのリクエストが本物か確認する"""
    hash_object = hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    )
    expected_signature = hash_object.digest()
    expected_signature_base64 = base64.b64encode(expected_signature).decode('utf-8')
    return expected_signature_base64 == signature

# ヘルスチェック用エンドポイント
@app.route("/")
def hello():
    return "Hello World!"

# LINE webhook エンドポイント
@app.route("/webhook", methods=["POST"])
def webhook():
    """LINE からのメッセージを受け取り、処理する"""
    
    # リクエストボディと署名を取得
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature")
    
    # 署名検証
    if not verify_line_signature(body, signature):
        print("Signature verification failed")
        return "Unauthorized", 401
    
    # JSON をパース
    try:
        events = json.loads(body).get("events", [])
    except Exception as e:
        print(f"JSON parse error: {e}")
        return "Bad Request", 400
    
    # イベント処理
    for event in events:
        event_type = event.get("type")
        
        if event_type == "message":
            # メッセージイベント
            reply_token = event.get("replyToken")
            message = event.get("message", {})
            
            # テスト用：受け取ったメッセージをそのまま返す（エコー）
            text = message.get("text", "メッセージが空です")
            send_reply_message(reply_token, text)
        
        elif event_type == "follow":
            # フォローイベント
            reply_token = event.get("replyToken")
            send_reply_message(reply_token, "フォローありがとうございます！\n秘書AIです。何かお手伝いできることはありますか？")
    
    return "OK", 200

def send_reply_message(reply_token, text):
    """LINE に返信メッセージを送る"""
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
        response = requests.post(LINE_API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"LINE API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request error: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
