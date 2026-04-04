"""
Gmail API ツール実装

菊池代表のメール（Gmail）への操作を提供
"""

import base64
import logging
from typing import Optional

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.credentials import ConfigManager

logger = logging.getLogger(__name__)

# グローバル Gmail サービス（遅延初期化）
_gmail_service = None


def get_gmail_service():
    """Gmail API サービスを取得（キャッシュあり）"""
    global _gmail_service

    if _gmail_service is not None:
        return _gmail_service

    try:
        ConfigManager.validate_gmail_credentials()

        refresh_token = ConfigManager.gmail.get_refresh_token()
        client_id = ConfigManager.gmail.get_client_id()
        client_secret = ConfigManager.gmail.get_client_secret()
        scopes = ConfigManager.gmail.get_scopes()

        # Credentials オブジェクトを再構築
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes
        )

        # トークンをリフレッシュ
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)

        _gmail_service = build('gmail', 'v1', credentials=credentials)
        logger.info("✅ Gmail サービス初期化成功")
        return _gmail_service

    except ValueError as e:
        logger.error(f"Gmail 認証情報エラー: {e}")
        raise
    except Exception as e:
        logger.error(f"Gmail API 初期化エラー: {e}")
        raise


def search_emails(query: str, max_results: int = 5) -> str:
    """
    メール検索

    Args:
        query: 検索キーワード（例: from:山田 subject:提案）
        max_results: 取得件数（デフォルト: 5）

    Returns:
        フォーマットされたメール一覧
    """
    try:
        service = get_gmail_service()

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return "該当するメールはありません"

        message_list = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = msg_data['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

            message_list.append(f"- {subject}\n  From: {sender}\n  Date: {date}\n  ID: {msg['id']}")

        return "\n".join(message_list)

    except ValueError as e:
        logger.error(f"Gmail 認証エラー: {e}")
        return f"エラー: {str(e)}"
    except Exception as e:
        logger.error(f"メール検索エラー: {e}")
        return f"エラー: {str(e)}"


def read_email(message_id: str) -> str:
    """
    メール内容を読む

    Args:
        message_id: メッセージ ID

    Returns:
        フォーマットされたメール内容
    """
    try:
        service = get_gmail_service()

        msg_data = service.users().messages().get(
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

        result = f"""Subject: {subject}
From: {sender}
Date: {date}

{body_text[:2000]}"""

        return result

    except ValueError as e:
        logger.error(f"Gmail 認証エラー: {e}")
        return f"エラー: {str(e)}"
    except Exception as e:
        logger.error(f"メール読込エラー: {e}")
        return f"エラー: {str(e)}"


def clear_gmail_cache():
    """Gmail サービスキャッシュをクリア（テスト用）"""
    global _gmail_service
    _gmail_service = None
