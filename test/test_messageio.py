import json
import os
import shutil
import threading
import time
import random
import string

import pytest

from backend.infra.fileio.messageio import MessageIO

# -------------------------
# test helpers
# -------------------------

BASE_DIR = "./_test_sessions"


def setup_env():
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    os.makedirs(BASE_DIR, exist_ok=True)


def session_file(name: str) -> str:
    return os.path.join(BASE_DIR, f"{name}.json")


def init_empty_session(path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"messages": []}, f, ensure_ascii=False)


def read_messages(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["messages"]


def random_chunk(prefix: str, i: int) -> str:
    tail = "".join(random.choices(string.ascii_letters, k=5))
    return f"{prefix}-{i}-{tail}\n"


# -------------------------
# tests
# -------------------------

def test_assistant_message_structure():
    setup_env()
    path = session_file("basic")
    init_empty_session(path)

    io = MessageIO(flush_interval=0.05)

    io.start_stream(path)
    io.append_content(path, "hello")
    io.end_stream(path)

    time.sleep(0.1)
    io.shutdown()

    messages = read_messages(path)

    assert isinstance(messages, list)
    assert len(messages) == 1

    msg = messages[0]
    assert msg["role"] == "assistant"
    assert msg["content"] == "hello"
    assert "model_extra" in msg
    assert "reasoning_content" in msg["model_extra"]


def test_content_is_append_only():
    setup_env()
    path = session_file("append_only")
    init_empty_session(path)

    io = MessageIO(flush_interval=0.02)

    io.start_stream(path)

    chunks = []
    for i in range(10):
        c = random_chunk("A", i)
        chunks.append(c)
        io.append_content(path, c)

    io.end_stream(path)
    time.sleep(0.1)
    io.shutdown()

    messages = read_messages(path)
    content = messages[-1]["content"]

    assert content == "".join(chunks)


def test_abort_preserves_partial_content():
    setup_env()
    path = session_file("abort")
    init_empty_session(path)

    io = MessageIO(flush_interval=0.05)

    io.start_stream(path)
    io.append_content(path, "part1\n")
    io.append_content(path, "part2\n")

    # 模拟用户 stop
    io.end_stream(path)

    time.sleep(0.1)
    io.shutdown()

    messages = read_messages(path)
    content = messages[-1]["content"]

    assert content == "part1\npart2\n"


def test_concurrent_start_stream_same_session():
    """
    同一 session 并发 start：
    不要求逻辑正确，只要求：
    - 不 crash
    - JSON 最终可读
    """
    setup_env()
    path = session_file("same_session")
    init_empty_session(path)

    io = MessageIO(flush_interval=0.05)

    def worker():
        io.start_stream(path)
        time.sleep(0.01)
        io.end_stream(path)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    time.sleep(0.1)
    io.shutdown()

    messages = read_messages(path)

    # 至少能读出来
    assert isinstance(messages, list)
    for m in messages:
        assert m["role"] == "assistant"


def test_concurrent_multi_session_isolated():
    """
    核心并发测试：
    多 session 并发写，互不影响
    """
    setup_env()

    io = MessageIO(flush_interval=0.02)

    session_paths = []
    for i in range(5):
        path = session_file(f"s{i}")
        init_empty_session(path)
        session_paths.append(path)

    def writer(path: str, prefix: str):
        io.start_stream(path)
        for i in range(5):
            io.append_content(path, f"{prefix}-{i}\n")
            time.sleep(0.005)
        io.end_stream(path)

    threads = []
    for i, path in enumerate(session_paths):
        t = threading.Thread(
            target=writer,
            args=(path, f"S{i}")
            )
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    time.sleep(0.2)
    io.shutdown()

    for i, path in enumerate(session_paths):
        messages = read_messages(path)
        assert len(messages) == 1
        content = messages[0]["content"]
        for j in range(5):
            assert f"S{i}-{j}\n" in content