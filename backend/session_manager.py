import uuid
from datetime import datetime, timedelta

class SessionManager:
    """
    会话管理器，负责存储和管理所有对话会话的历史记录。
    当前使用内存存储，后续可替换为 Redis 或 SQLite。
    """
    def __init__(self, max_history_length: int = 50):
        self._sessions = {}  # session_id -> list of messages
        self._last_activity = {}  # session_id -> last access time
        self._max_history_length = max_history_length

    def _cleanup_expired(self, max_idle_hours: int = 24):
        """清理超过指定时间未活动的会话（可选功能）"""
        now = datetime.now()
        expired = [
            sid for sid, last_time in self._last_activity.items()
            if now - last_time > timedelta(hours=max_idle_hours)
        ]
        for sid in expired:
            del self._sessions[sid]
            del self._last_activity[sid]

    def _update_activity(self, session_id: str):
        """更新会话的最后活动时间"""
        self._last_activity[session_id] = datetime.now()

    def get_or_create_session(self, session_id: str = None) -> tuple[str, list[dict]]:
        """
        获取或创建会话。
        如果传入 session_id 且存在，返回该会话；
        如果传入 session_id 但不存在，创建新会话并返回；
        如果未传入 session_id，生成新的 session_id 并创建会话。
        返回: (session_id, messages)
        """
        if session_id is None or session_id not in self._sessions:
            # 生成新的 session_id
            new_id = str(uuid.uuid4())
            self._sessions[new_id] = []
            self._update_activity(new_id)
            return new_id, self._sessions[new_id]

        self._update_activity(session_id)
        return session_id, self._sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str, extra: dict = None):
        """
        向指定会话添加一条消息。
        role: "user" 或 "assistant" 或 "system"
        extra: 可选附加字段，如 {"sources": [...]}
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        message = {"role": role, "content": content}
        if extra:
            message.update(extra)
        self._sessions[session_id].append(message)

        # 如果消息长度超过限制，截断最早的消息（保留最近的）
        if len(self._sessions[session_id]) > self._max_history_length:
            self._sessions[session_id] = self._sessions[session_id][-self._max_history_length:]

        self._update_activity(session_id)

    def get_full_context(self, session_id: str) -> list[dict]:
        """获取会话的完整消息历史"""
        if session_id not in self._sessions:
            return []
        self._update_activity(session_id)
        return self._sessions[session_id].copy()

    def clear_session(self, session_id: str):
        """清空指定会话的历史记录"""
        if session_id in self._sessions:
            self._sessions[session_id] = []
            self._update_activity(session_id)

    def delete_session(self, session_id: str):
        """删除指定会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._last_activity:
                del self._last_activity[session_id]

    def get_all_sessions(self) -> dict:
        """
        获取所有会话的摘要信息（用于前端显示会话列表）
        返回: {session_id: {"first_message": str, "message_count": int, "last_activity": str}}
        """
        result = {}
        for sid, messages in self._sessions.items():
            if messages:
                first_user_msg = next((m["content"] for m in messages if m["role"] == "user"), None)
                # /ask 存的是 "[资料参考]...\n[用户问题]..." 包装格式，预览时只展示原始问题
                if first_user_msg and "[用户问题]" in first_user_msg:
                    first_user_msg = first_user_msg.split("[用户问题]", 1)[1].strip()
                result[sid] = {
                    "preview": first_user_msg[:50] + "..." if first_user_msg else "(空对话)",
                    "message_count": len(messages),
                    "last_activity": self._last_activity.get(sid, datetime.now()).isoformat()
                }
            else:
                result[sid] = {
                    "preview": "(空对话)",
                    "message_count": 0,
                    "last_activity": self._last_activity.get(sid, datetime.now()).isoformat()
                }
        return result