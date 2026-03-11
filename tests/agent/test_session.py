"""SessionStore 단위 테스트 — CRUD + TTL + trim_history."""

import time
from unittest.mock import patch

import pytest

from session import SessionStore


@pytest.fixture
def store():
    return SessionStore()


class TestCreate:
    def test_create_returns_string(self, store):
        sid = store.create()
        assert isinstance(sid, str)
        assert len(sid) == 36  # uuid4 format

    def test_create_unique_ids(self, store):
        ids = {store.create() for _ in range(10)}
        assert len(ids) == 10


class TestGetSave:
    def test_get_unknown_session_returns_empty(self, store):
        assert store.get("nonexistent") == []

    def test_save_and_get_roundtrip(self, store):
        sid = store.create()
        messages = [{"role": "user", "text": "hello"}]
        store.save(sid, messages)
        assert store.get(sid) == messages

    def test_save_overwrites_previous(self, store):
        sid = store.create()
        store.save(sid, [{"role": "user", "text": "first"}])
        store.save(sid, [{"role": "user", "text": "second"}])
        result = store.get(sid)
        assert len(result) == 1
        assert result[0]["text"] == "second"


class TestTTL:
    def test_expired_session_returns_empty(self, store):
        sid = store.create()
        store.save(sid, [{"role": "user", "text": "hello"}])

        # TTL 만료 시뮬레이션
        with patch("session.time") as mock_time:
            mock_time.time.return_value = time.time() + 1801  # 30분 + 1초
            assert store.get(sid) == []

    def test_active_session_within_ttl(self, store):
        sid = store.create()
        store.save(sid, [{"role": "user", "text": "hello"}])

        with patch("session.time") as mock_time:
            mock_time.time.return_value = time.time() + 1799  # 30분 - 1초
            assert len(store.get(sid)) == 1


class TestTrimHistory:
    def test_trim_under_limit_no_change(self, store):
        messages = [{"role": "user", "text": f"msg-{i}"} for i in range(10)]
        trimmed = store.trim_history(messages)
        assert len(trimmed) == 10

    def test_trim_over_limit_keeps_recent(self, store):
        # 50개 메시지 (user+assistant 쌍 25개) → MAX_HISTORY_TURNS * 2 = 40개로 트림
        messages = [{"role": "user", "text": f"msg-{i}"} for i in range(50)]
        trimmed = store.trim_history(messages)
        assert len(trimmed) == 40
        # 최근 40개 유지
        assert trimmed[0]["text"] == "msg-10"
        assert trimmed[-1]["text"] == "msg-49"
