"""
認証情報の統一管理モジュール

ローカル開発：.env ファイルから読み込み
本番環境：環境変数から読み込み
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class GmailConfig:
    """Gmail OAuth 2.0 認証設定"""

    @staticmethod
    def get_refresh_token() -> Optional[str]:
        """Gmail リフレッシュトークンを取得"""
        # 環境変数から取得
        if token := os.getenv("GMAIL_REFRESH_TOKEN"):
            return token

        # ローカルファイルから取得（後方互換性）
        config_file = Path(__file__).parent / "gmail_refresh_token.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)
                return data.get('refresh_token')

        return None

    @staticmethod
    def get_client_id() -> Optional[str]:
        """Gmail クライアント ID を取得"""
        # 環境変数から取得
        if client_id := os.getenv("GMAIL_CLIENT_ID"):
            return client_id

        # ローカルファイルから取得（後方互換性）
        config_file = Path(__file__).parent / "gmail_refresh_token.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)
                return data.get('client_id')

        return None

    @staticmethod
    def get_client_secret() -> Optional[str]:
        """Gmail クライアント秘密鍵を取得"""
        # 環境変数から取得
        if secret := os.getenv("GMAIL_CLIENT_SECRET"):
            return secret

        # ローカルファイルから取得（後方互換性）
        config_file = Path(__file__).parent / "gmail_refresh_token.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = json.load(f)
                return data.get('client_secret')

        return None

    @staticmethod
    def get_scopes() -> list:
        """Gmail API スコープを取得"""
        scopes_env = os.getenv("GMAIL_SCOPES")
        if scopes_env:
            # カンマ区切りで複数指定できる
            return [s.strip() for s in scopes_env.split(',')]

        # デフォルトスコープ
        return ['https://www.googleapis.com/auth/gmail.modify']


class GoogleCalendarConfig:
    """Google Calendar Service Account 認証設定"""

    @staticmethod
    def get_service_account_info() -> Optional[Dict[str, Any]]:
        """Service Account 情報を取得"""
        # 環境変数から取得（JSON 文字列）
        if service_account_json := os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
            try:
                return json.loads(service_account_json)
            except json.JSONDecodeError:
                pass

        # ファイルパスから取得
        file_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "config/service_account.json")
        full_path = Path(__file__).parent / file_path

        if full_path.exists():
            with open(full_path, 'r') as f:
                return json.load(f)

        # ローカルファイルをチェック（後方互換性）
        legacy_path = Path(__file__).parent / "google_credentials.json"
        if legacy_path.exists():
            with open(legacy_path, 'r') as f:
                return json.load(f)

        return None

    @staticmethod
    def get_target_user_email() -> str:
        """対象ユーザーのメールアドレスを取得"""
        return os.getenv("GOOGLE_TARGET_USER_EMAIL", "k.kikuchi@rfp-inc.jp")

    @staticmethod
    def get_scopes() -> list:
        """Google Calendar API スコープを取得"""
        return [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.readonly'
        ]


class ConfigManager:
    """統一設定管理"""

    gmail = GmailConfig()
    calendar = GoogleCalendarConfig()

    @staticmethod
    def validate_credentials() -> Dict[str, bool]:
        """
        認証情報の妥当性をチェック

        Returns:
            {'gmail': bool, 'calendar': bool}
        """
        validation = {
            'gmail': all([
                ConfigManager.gmail.get_refresh_token(),
                ConfigManager.gmail.get_client_id(),
                ConfigManager.gmail.get_client_secret()
            ]),
            'calendar': ConfigManager.calendar.get_service_account_info() is not None
        }
        return validation

    @staticmethod
    def validate_gmail_credentials() -> None:
        """Gmail 認証情報をチェック。不足している場合は例外を発生"""
        if not ConfigManager.gmail.get_refresh_token():
            raise ValueError("GMAIL_REFRESH_TOKEN が設定されていません")
        if not ConfigManager.gmail.get_client_id():
            raise ValueError("GMAIL_CLIENT_ID が設定されていません")
        if not ConfigManager.gmail.get_client_secret():
            raise ValueError("GMAIL_CLIENT_SECRET が設定されていません")

    @staticmethod
    def validate_calendar_credentials() -> None:
        """Google Calendar 認証情報をチェック。不足している場合は例外を発生"""
        if not ConfigManager.calendar.get_service_account_info():
            raise ValueError("Google Service Account 情報が見つかりません")
