"""인메모리 세션 저장소. Phase 2-A에서는 dict 기반."""

import time
import uuid

MAX_HISTORY_TURNS = 20
SESSION_TTL_SECONDS = 1800  # 30분


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    def create(self) -> str:
        sid = str(uuid.uuid4())
        self._sessions[sid] = {"messages": [], "last_access": time.time()}
        return sid

    def get(self, session_id: str) -> list:
        entry = self._sessions.get(session_id)
        if entry is None:
            return []
        if time.time() - entry["last_access"] > SESSION_TTL_SECONDS:
            del self._sessions[session_id]
            return []
        entry["last_access"] = time.time()
        return entry["messages"]

    def save(self, session_id: str, messages: list) -> None:
        self._sessions[session_id] = {
            "messages": messages,
            "last_access": time.time(),
        }

    def trim_history(self, messages: list) -> list:
        max_messages = MAX_HISTORY_TURNS * 2
        if len(messages) <= max_messages:
            return messages
        return messages[-max_messages:]
