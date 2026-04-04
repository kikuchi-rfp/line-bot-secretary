"""
秘書 AI エージェント

役割：ユーザーの自然言語の指示を理解して、必要なツールを選択・実行するシステム
"""

import logging
from typing import Optional, List, Dict, Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)

# ツール定義（JSON Schema形式）
TOOLS = [
    {
        "name": "list_calendar_events",
        "description": "菊池代表の予定一覧を取得します",
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
        "description": "新しい予定をカレンダーに追加します",
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
                    "description": "詳細説明（オプション）"
                }
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "search_emails",
        "description": "メールを検索します",
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
        "description": "メールの詳細内容を読みます",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "メッセージ ID（search_emails から取得）"
                }
            },
            "required": ["message_id"]
        }
    }
]


class SecretaryAgent:
    """菊池代表の秘書 AI エージェント"""

    def __init__(self):
        """初期化"""
        try:
            self.client = Anthropic()
            logger.info("✅ Anthropic クライアント初期化成功")
        except Exception as e:
            logger.error(f"❌ Anthropic クライアント初期化エラー: {e}")
            raise

        self.system_prompt = """あなたは、菊池紅輔代表の秘書です。
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

利用可能なツール：
- Google Calendar（予定管理）：代表のスケジュール確認・予定追加
- Gmail（メール対応）：メール検索・詳細確認
- Google Sheets（タスク管理）：準備中
- Indeed API（採用管理）：準備中

代表の指示を理解して、最適なツールを自動選択し、効率的にサポートしてください。"""

    def process_user_request(self, user_message: str) -> str:
        """
        ユーザーの依頼を処理

        Flow:
        1. Claude AI がメッセージを理解
        2. 必要なツールを自動選択・実行
        3. ツール実行結果を取得
        4. 結果を自然言語で整理して返す

        Args:
            user_message: ユーザーからの依頼メッセージ

        Returns:
            処理結果メッセージ
        """
        logger.info(f"秘書に処理依頼: {user_message}")

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Agent ループ iteration {iteration}/{max_iterations}")

            try:
                # Claude API を呼び出し
                response = self.client.messages.create(
                    model="claude-opus-4-1",
                    max_tokens=2048,
                    system=self.system_prompt,
                    tools=TOOLS,
                    messages=messages
                )

                logger.debug(f"Claude 応答: stop_reason={response.stop_reason}")

                # ツール呼び出しのチェック
                if response.stop_reason == "tool_use":
                    # ツール呼び出しを処理
                    tool_results_added = False

                    for content_block in response.content:
                        if hasattr(content_block, 'type') and content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_use_id = content_block.id

                            logger.debug(f"ツール呼び出し: {tool_name} with input: {tool_input}")

                            # ツール実行
                            tool_result = self.execute_tool(tool_name, tool_input)
                            logger.debug(f"ツール結果（最初の200文字）: {str(tool_result)[:200]}")

                            # メッセージに追加
                            if not tool_results_added:
                                messages.append({"role": "assistant", "content": response.content})
                                tool_results_added = True

                            messages.append({
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": str(tool_result)
                                    }
                                ]
                            })

                else:
                    # 最終回答を返す
                    for content_block in response.content:
                        if hasattr(content_block, 'text'):
                            final_response = content_block.text
                            logger.info(f"秘書からの応答: {final_response[:100]}...")
                            return final_response

                    break

            except Exception as e:
                logger.error(f"❌ Agent ループエラー (iteration {iteration}): {e}")
                if iteration >= max_iterations:
                    return f"申し訳ありません。処理に失敗しました: {str(e)}"

        return "申し訳ありません。処理を完了できませんでした。"

    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        ツール実装を呼び出す

        Args:
            tool_name: ツール名
            tool_input: ツール入力パラメータ

        Returns:
            ツール実行結果
        """
        try:
            # Calendar ツール
            if tool_name == "list_calendar_events":
                from tools.calendar import list_calendar_events
                return list_calendar_events(tool_input.get("days_ahead", 7))

            elif tool_name == "create_calendar_event":
                from tools.calendar import create_calendar_event
                return create_calendar_event(
                    tool_input.get("summary", ""),
                    tool_input.get("start_time", ""),
                    tool_input.get("end_time", ""),
                    tool_input.get("description", "")
                )

            # Gmail ツール
            elif tool_name == "search_emails":
                from tools.gmail import search_emails
                return search_emails(
                    tool_input.get("query", ""),
                    tool_input.get("max_results", 5)
                )

            elif tool_name == "read_email":
                from tools.gmail import read_email
                return read_email(tool_input.get("message_id", ""))

            # Google Sheets ツール（準備中）
            elif tool_name == "get_tasks":
                from tools.sheets import get_tasks
                return get_tasks()

            elif tool_name == "add_task":
                from tools.sheets import add_task
                return add_task(
                    tool_input.get("title", ""),
                    tool_input.get("description", "")
                )

            # Indeed ツール（準備中）
            elif tool_name == "get_job_postings":
                from tools.indeed import get_job_postings
                return get_job_postings()

            else:
                logger.warning(f"未知のツール: {tool_name}")
                return f"未知のツール: {tool_name}"

        except ValueError as e:
            logger.error(f"ツール実行エラー ({tool_name}): 認証エラー - {e}")
            return f"認証エラー: {str(e)}"
        except Exception as e:
            logger.error(f"ツール実行エラー ({tool_name}): {e}")
            return f"ツール実行エラー: {str(e)}"
