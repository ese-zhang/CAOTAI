import concurrent.futures
import threading
import time
from unittest.mock import patch

import pytest

from backend.core.memory import MemoryManager
from backend.core.memory.memory_manager import SessionState


@pytest.fixture
def mock_db():
    with patch("backend.core.memory.memory_manager.db") as mock:
        mock.load_messages.side_effect = lambda path: []
        yield mock


@pytest.fixture
def manager(mock_db):
    mgr = MemoryManager(flush_interval=0.05)
    yield mgr
    mgr.shutdown()


class TestMemoryManager:

    def _get_arg(self, call_args, index, name):
        args, kwargs = call_args
        if name in kwargs:
            return kwargs[name]
        if len(args) > index:
            return args[index]
        return None

    def test_sessions_are_isolated(self):
        s1 = SessionState("A")
        s2 = SessionState("B")

        s1.add_message({"msg": "1"})
        assert len(s2.messages) == 0

    def test_start_stream_initializes_session(self, manager, mock_db):
        path = "session_init"
        manager.start_stream(path)

        assert path in manager.sessions
        mock_db.load_messages.assert_called_with(path)

    def test_append_content_updates_state(self, manager):
        path = "append_test"
        manager.start_stream(path)
        manager.append_content(path, "Hello")

        state = manager.sessions[path]
        assert state.messages[-1]["content"] == "Hello"
        assert state.dirty is True

    def test_background_flush_updates_db(self, manager, mock_db):
        path = "flush_test"
        manager.start_stream(path)
        manager.append_content(path, "Streaming...")

        for _ in range(10):
            if mock_db.update_last_message.called:
                call = mock_db.update_last_message.call_args
                if self._get_arg(call, 1, "content") == "Streaming...":
                    return
            time.sleep(0.1)

        pytest.fail("后台 flush 未触发")

    def test_end_stream_finalizes(self, manager, mock_db):
        path = "end_test"
        manager.start_stream(path)
        manager.append_content(path, "Done.")

        mock_db.update_last_message.reset_mock()
        tools = [{"name": "calculator"}]

        manager.end_stream(path, tool_calls=tools)

        assert path not in manager.sessions
        call = mock_db.update_last_message.call_args
        assert self._get_arg(call, 1, "content") == "Done."
        assert self._get_arg(call, 3, "tool_calls") == tools

    def test_append_message_forces_end_stream(self, manager, mock_db):
        path = "interrupt"
        manager.start_stream(path)

        new_msg = {"role": "user", "content": "New prompt"}
        manager.append_message(path, new_msg)

        assert path not in manager.sessions
        mock_db.append_message.assert_called_with(path, new_msg)

    def test_reasoning_persistence(self, manager, mock_db):
        path = "reasoning"
        manager.start_stream(path)
        manager.append_reasoning(path, "Thinking")
        manager.append_content(path, "Result")

        mock_db.update_last_message.reset_mock()
        manager.end_stream(path)

        call = mock_db.update_last_message.call_args
        assert self._get_arg(call, 1, "content") == "Result"
        assert self._get_arg(call, 2, "reasoning") == "Thinking"


class TestConcurrencyStress:

    def test_atomic_append(self, manager):
        path = "atomic"
        manager.start_stream(path)

        def worker(char):
            for _ in range(100):
                manager.append_content(path, char * 10)

        with concurrent.futures.ThreadPoolExecutor(20) as ex:
            ex.map(worker, "ABCDEFGHIJKLMNOPQRST")

        content = manager.sessions[path].messages[-1]["content"]
        for i in range(0, len(content), 10):
            assert len(set(content[i:i + 10])) == 1

    def test_sequence_integrity_and_routing(self, manager):
        sessions = ["A", "B", "C", "D"]
        for s in sessions:
            manager.start_stream(s)

        def worker(tid):
            target = sessions[tid // 5]
            for i in range(100):
                manager.append_content(target, f"{tid}:{i},")

        with concurrent.futures.ThreadPoolExecutor(20) as ex:
            ex.map(worker, range(20))

        for idx, name in enumerate(sessions):
            state = manager.sessions[name]
            items = [x for x in state.messages[-1]["content"].split(",") if x]

            assert len(items) == 500

            for item in items:
                tid, seq = map(int, item.split(":"))
                assert tid in range(idx * 5, (idx + 1) * 5)
                assert seq >= 0

    def test_flush_and_write_no_deadlock(self, manager):
        path = "flush_lock"
        manager.start_stream(path)
        manager.flush_interval = 0.01

        stop = threading.Event()

        def writer():
            while not stop.is_set():
                manager.append_content(path, "a")
                manager.recall(path)

        threads = [threading.Thread(target=writer) for _ in range(10)]
        for t in threads:
            t.start()

        time.sleep(1)
        stop.set()

        for t in threads:
            t.join()

        assert True

    def test_session_identity_stable(self, manager):
        paths = ["X", "Y", "Z"]
        for p in paths:
            manager.start_stream(p)

        ids = {p: id(manager.sessions[p]) for p in paths}

        def worker(p):
            return id(manager.sessions[p])

        with concurrent.futures.ThreadPoolExecutor(10) as ex:
            results = ex.map(worker, paths * 3)

        for p, obj_id in zip(paths * 3, results):
            assert obj_id == ids[p]