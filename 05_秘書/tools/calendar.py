"""
Google Calendar API ツール実装

菊池代表のカレンダー（k.kikuchi@rfp-inc.jp）への操作を提供
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.credentials import ConfigManager

logger = logging.getLogger(__name__)

# グローバル Calendar サービス（遅延初期化）
_calendar_service = None


def get_calendar_service():
    """Google Calendar API サービスを取得（キャッシュあり）"""
    global _calendar_service

    if _calendar_service is not None:
        return _calendar_service

    try:
        ConfigManager.validate_calendar_credentials()

        service_account_info = ConfigManager.calendar.get_service_account_info()
        credentials = ServiceAccountCredentials.from_service_account_info(
            service_account_info,
            scopes=ConfigManager.calendar.get_scopes()
        )

        _calendar_service = build('calendar', 'v3', credentials=credentials)
        logger.info("✅ Google Calendar サービス初期化成功")
        return _calendar_service

    except ValueError as e:
        logger.error(f"Calendar 認証情報エラー: {e}")
        raise
    except Exception as e:
        logger.error(f"Calendar API 初期化エラー: {e}")
        raise


def list_calendar_events(days_ahead: int = 7) -> str:
    """
    カレンダーイベント一覧を取得

    Args:
        days_ahead: 今後何日分の予定を取得するか（デフォルト: 7）

    Returns:
        フォーマットされたイベント一覧
    """
    try:
        service = get_calendar_service()
        target_user_email = ConfigManager.calendar.get_target_user_email()

        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=target_user_email,
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

    except ValueError as e:
        logger.error(f"Calendar 認証エラー: {e}")
        return f"エラー: {str(e)}"
    except HttpError as e:
        error_content = e.content.decode('utf-8') if hasattr(e.content, 'decode') else str(e.content)
        logger.error(f"Calendar API エラー: {error_content}")
        return f"予定取得エラー: {str(e)}"
    except Exception as e:
        logger.error(f"予定取得エラー: {e}")
        return f"予定取得エラー: {str(e)}"


def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = ""
) -> str:
    """
    カレンダーイベントを作成

    Args:
        summary: 予定のタイトル
        start_time: 開始時刻（ISO 8601形式）
        end_time: 終了時刻（ISO 8601形式）
        description: 詳細説明（オプション）

    Returns:
        作成結果メッセージ
    """
    try:
        service = get_calendar_service()
        target_user_email = ConfigManager.calendar.get_target_user_email()

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

        created_event = service.events().insert(
            calendarId=target_user_email,
            body=event
        ).execute()

        logger.info(f"カレンダーイベント作成: {created_event['summary']}")
        return f"予定を追加しました: {created_event['summary']}"

    except ValueError as e:
        logger.error(f"Calendar 認証エラー: {e}")
        return f"エラー: {str(e)}"
    except Exception as e:
        logger.error(f"カレンダー作成エラー: {e}")
        return f"エラー: {str(e)}"


def clear_calendar_cache():
    """Calendar サービスキャッシュをクリア（テスト用）"""
    global _calendar_service
    _calendar_service = None
