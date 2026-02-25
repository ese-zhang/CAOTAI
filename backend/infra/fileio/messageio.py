import time
import threading
from typing import Dict, List, Optional
from .load_message import save_messages, load_messages


class SessionState:
    """
    单个 session 的完整状态
    """
    def __init__(self, session_path: str, messages: List[Dict]):
        self.session_path = session_path
        self.messages = messages
        self.message = messages[-1]          # 当前 streaming 的 assistant message
        self.dirty = False
        self.last_flush = 0.0
        self.streaming = True
        self.lock = threading.Lock()


class MessageIO:
    """
    职责：
    - 路由 session -> SessionState
    - 提供 stream 生命周期 API
    - 后台低频 flush
    """

    def __init__(self, flush_interval: float = 0.5):
        self.sessions: Dict[str, SessionState] = {}
        self.flush_interval = flush_interval

        self.global_lock = threading.Lock()
        self.running = True

        self.worker = threading.Thread(
            target=self._flush_loop,
            daemon=True
            )
        self.worker.start()

    # ---------- 生命周期 ----------

    def start_stream(self, session_path: str) -> Dict:
        """
        stream 开始前调用
        - 加载或初始化历史
        - 插入占位 assistant message
        """
        with self.global_lock:
            if session_path in self.sessions:
                # 语义选择：复用已有 session（也可以 raise）
                return self.sessions[session_path].message

            try:
                messages = load_messages(session_path)
                if not isinstance(messages, list):
                    messages = []
            except FileNotFoundError:
                messages = []

            assistant_message = {
                "role": "assistant",
                "content": None,
                "model_extra": {"reasoning_content": ""}
                }
            messages.append(assistant_message)

            state = SessionState(session_path, messages)
            self.sessions[session_path] = state

            save_messages(messages, session_path)
            return assistant_message

    def end_stream(
            self,
            session_path: str,
            tool_calls: Optional[List[Dict]] = None
            ):
        """
        stream 正常结束或被中断
        """
        with self.global_lock:
            state = self.sessions.pop(session_path, None)

        if not state:
            return

        with state.lock:
            if tool_calls:
                state.message["tool_calls"] = tool_calls

            save_messages(state.messages, session_path)
            state.streaming = False
            state.dirty = False

    # ---------- 增量写入 ----------

    def append_content(self, session_path: str, chunk: str):
        state = self.sessions.get(session_path)
        if not state:
            return

        with state.lock:
            msg = state.message
            msg["content"] = (msg["content"] or "") + chunk
            state.dirty = True

    def append_reasoning(self, session_path: str, chunk: str):
        state = self.sessions.get(session_path)
        if not state:
            return

        with state.lock:
            reasoning = state.message["model_extra"].get("reasoning_content", "")
            state.message["model_extra"]["reasoning_content"] = reasoning + chunk
            state.dirty = True

    def append_message(self, session_path: str, message: Dict):
        """
        向 session 追加一条完整 message。
        语义：
        - 如果 session 仍在 streaming，则先 end_stream
        - append_message 等价于“一个新的非 streaming 消息”
        """

        # 1. 如果还在 streaming，先 finalize
        state = self.sessions.get(session_path)
        if state:
            # 不传 tool_calls，纯 finalize
            self.end_stream(session_path)

        # 2. 读取完整历史
        try:
            messages = load_messages(session_path)
            if not isinstance(messages, list):
                messages = []
        except FileNotFoundError:
            messages = []

        # 3. 追加新 message
        messages.append(message)

        # 4. 立即落盘（append_message 是强一致语义）
        save_messages(messages, session_path)

    # ---------- 读取 ----------

    def read_messages(self, session_path: str) -> List[Dict]:
        state = self.sessions.get(session_path)
        if state:
            with state.lock:
                import copy
                return copy.deepcopy(state.messages)

        # 如果内存没有，去磁盘读
        try:
            return load_messages(session_path)
        except:
            return []

    # ---------- 后台 flush ----------

    def _flush_loop(self):
        while self.running:
            time.sleep(0.1)
            # 这里的 states 只是引用快照
            with self.global_lock:
                states = list(self.sessions.values())

            now = time.time()
            for state in states:
                # 检查过期逻辑 (可选)
                # if now - state.last_flush > 3600: self.end_stream(state.session_path)

                if not state.dirty or now - state.last_flush < self.flush_interval:
                    continue

                if state.lock.acquire(blocking=False):
                    try:
                        # 重点：快照后再写，减少锁占用时间
                        messages_to_save = list(state.messages)
                        state.dirty = False
                        state.last_flush = now
                    finally:
                        state.lock.release()

                    # 在锁外执行 IO
                    save_messages(messages_to_save, state.session_path)

    def shutdown(self):
        self.running = False
        self.worker.join()

    def _debug(self, where: str, session_path: str, state: Optional[SessionState]):
        tid = threading.get_ident()
        if not state:
            print(f"[{where}] tid={tid} session={session_path} state=None")
            return

        print(
            f"[{where}] tid={tid} session={session_path} "
            f"id(state)={id(state)} "
            f"streaming={state.streaming} "
            f"dirty={state.dirty} "
            f"messages_id={id(state.messages)} "
            f"messages_len={len(state.messages) if state.messages else 'None'} "
            f"message_id={id(state.message) if state.message else 'None'}"
        )