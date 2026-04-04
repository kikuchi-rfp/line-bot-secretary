#!/usr/bin/env python3
"""
Flask API エンドポイント
"""
import os
import logging
import json
from flask import Flask, request, jsonify

from secretary_agent import SecretaryAgent

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask アプリケーション
app = Flask(__name__)

# 秘書 AI エージェント（遅延初期化）
secretary_agent = None


def get_secretary_agent() -> SecretaryAgent:
    """秘書 AI エージェントを取得(シングルトン)"""
    global secretary_agent
    if secretary_agent is None:
        logger.info("秘書 AI エージェントを初期化中...")
        try:
            secretary_agent = SecretaryAgent()
            logger.info("✅ 秘書 AI エージェント初期化成功")
        except Exception as e:
            logger.error(f"❌ 秘書 AI エージェント初期化失敗: {e}")
            raise
    return secretary_agent


@app.route("/", methods=["GET"])
def health_check():
    """ヘルスチェック"""
    return jsonify({"status": "ok", "service": "secretary-agent-api"}), 200


@app.route("/api/secretary", methods=["POST"])
def secretary_endpoint():
    """
    秘書 AI エージェントのエンドポイント

    LINE Bot からのリクエストを処理して、秘書 AI に処理させる

    Request JSON:
    {
        "message": "ユーザーからのメッセージ"
    }

    Response JSON:
    {
        "result": "秘書からの応答メッセージ"
    }
    """
    logger.info("秘書エンドポイントへのリクエスト受信")

    try:
        # リクエストボディを取得
        data = request.get_json()

        if not data:
            logger.error("リクエストボディが空です")
            return jsonify({"error": "リクエストボディが必要です"}), 400

        user_message = data.get("message", "")

        if not user_message:
            logger.error("message フィールドが空です")
            return jsonify({"error": "message フィールドが必要です"}), 400

        logger.info(f"ユーザーメッセージ: {user_message[:100]}")

        # 秘書 AI エージェントで処理
        try:
            agent = get_secretary_agent()
            result = agent.process_user_request(user_message)
            logger.info(f"秘書処理完了: {result[:100]}...")

            return jsonify({"result": result}), 200

        except ValueError as e:
            logger.error(f"認証エラー: {e}")
            return jsonify({"error": f"認証エラー: {str(e)}"}), 500

        except Exception as e:
            logger.error(f"秘書処理エラー: {e}")
            return jsonify({"error": f"処理エラー: {str(e)}"}), 500

    except json.JSONDecodeError as e:
        logger.error(f"JSON パースエラー: {e}")
        return jsonify({"error": "無効な JSON です"}), 400

    except Exception as e:
        logger.error(f"エンドポイントエラー: {e}")
        return jsonify({"error": "内部エラーが発生しました"}), 500


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック（詳細版）"""
    try:
        from config.credentials import ConfigManager

        validation = ConfigManager.validate_credentials()

        return jsonify({
            "status": "healthy",
            "credentials": {
                "gmail": validation.get('gmail', False),
                "calendar": validation.get('calendar', False)
            }
        }), 200

    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    # Cloud Run は PORT 環境変数を使う（ローカル開発は 5000）
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"秘書 AI API サーバー起動中... (http://0.0.0.0:{port})")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False  # 本番環境なので debug=False
    )
