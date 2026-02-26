import copy
import time
import threading
import warnings
from typing import Dict, List, Optional
from backend.infra.database import db


class SessionState:
    """
    单个 session 的完整状态
    """
    def __init__(self, session_path: str):
        self.session_path = session_path
        try:
            raw_data = db.load_messages(session_path)
            # 使用深拷贝，确保即便 db 模块抽风返回了共享对象，内存也是隔离的
            self.messages = copy.deepcopy(raw_data) if raw_data else []
        except FileNotFoundError:
            self.messages = []
        self.dirty = False
        self.last_flush = 0.0
        self.streaming = True
        self.lock = threading.Lock()

    def add_message(self, msg: Dict):
        self.messages.append(msg)
        self.mark_dirty()

    def append_content(self, chunk: str):
        if not self.messages:
            return
        self.messages[-1]["content"] = (self.messages[-1].get("content") or "") + chunk
        self.mark_dirty()

    def append_reasoning(self, chunk: str):
        if not self.messages:
            return
        reasoning = self.messages[-1]["model_extra"].get("reasoning_content", "")
        self.messages[-1]["model_extra"]["reasoning_content"] = reasoning + chunk
        self.mark_dirty()

    def mark_dirty(self):
        self.dirty = True

    def snapshot_messages(self) -> List[Dict]:
        import copy
        return copy.deepcopy(self.messages)


class MemoryManager:
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
            state = self.sessions.get(session_path)
            if not state:
                # 初始化内存 session
                state = SessionState(session_path)
                self.sessions[session_path] = state

            assistant_message = {
                "role": "assistant",
                "content": None,
                "model_extra": {"reasoning_content": ""}
                }
            with state.lock:
                state.add_message(assistant_message)  # 内存中增加

            return assistant_message


    def end_stream(self, session_path: str, tool_calls: Optional[List[Dict]] = None):
        with self.global_lock:
            state = self.sessions.pop(session_path, None)
        if not state: return

        with state.lock:
            # 获取内存中最后一条 assistant 消息的状态
            last_msg = state.messages[-1]
            # 增量更新数据库中对应的最后一行
            db.update_last_message(
                session_path, 
                content=last_msg.get("content"),
                reasoning=last_msg.get("model_extra", {}).get("reasoning_content"),
                tool_calls=tool_calls
            )

    # ---------- 增量写入 ----------

    def append_content(self, session_path: str, chunk: str):
        state = self.sessions.get(session_path)
        if not state:
            return
        with state.lock:
            state.append_content(chunk)
            state.mark_dirty()

    def append_reasoning(self, session_path: str, chunk: str):
        state = self.sessions.get(session_path)
        if not state:
            return
        with state.lock:
            state.append_reasoning(chunk)
            state.mark_dirty()

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
            messages = db.load_messages(session_path)
            if not isinstance(messages, list):
                messages = []
        except FileNotFoundError:
            messages = []

        # 4. 立即落盘（append_message 是强一致语义）
        db.append_message(session_path, message)

    # ---------- 读取 ----------

    def recall(self, session_path: str) -> List[Dict]:
        """
        返回经过 memory 策略处理后的消息：
        - 高频消息权重高
        - 最近消息优先
        - 可以加 embedding/semantic retrieval
        """
        state = self.sessions.get(session_path)
        if not state:
            warnings.warn(f"Session {session_path} 不存在", UserWarning)
            return []

        with state.lock:
            # 这里做 memory 策略处理，而不是直接返回全量 messages
            messages = state.messages
            filtered = self.memory_filter(messages)
            return filtered

    @staticmethod
    def memory_filter(messages: List[Dict]) -> List[Dict]:
        """
        示例策略：
        - 最近 5 条必选
        - 热门 message（被访问/引用次数高）保留
        - 可选：embedding 检索相关内容
        """
        recent = messages[-5:]
        hot = sorted(messages, key=lambda m: m.get("access_count", 0), reverse=True)
        # 合并去重
        seen_ids = set()
        result = []
        for msg in recent + hot:
            mid = id(msg)
            if mid not in seen_ids:
                result.append(msg)
                seen_ids.add(mid)
        return result
    # ---------- 后台 flush ----------

    def _flush_loop(self):
        while self.running:
            time.sleep(0.1)
            with self.global_lock:
                states = list(self.sessions.values())

            now = time.time()
            for state in states:
                if not state.dirty or now - state.last_flush < self.flush_interval:
                    continue

                if state.lock.acquire(blocking=False):
                    try:
                        # 获取最后一条消息（正在流式增长的那条）
                        if not state.messages:
                            state.dirty = False
                            continue

                        last_msg = state.messages[-1]
                        # 准备快照数据
                        content = last_msg.get("content", "")
                        reasoning = last_msg.get("model_extra", {}).get("reasoning_content", "")

                        state.dirty = False
                        state.last_flush = now

                        # 在锁内完成快照后，去锁外执行数据库操作
                        session_id = state.session_path
                    finally:
                        state.lock.release()

                    # 增量同步：更新数据库中该 Session 的最后一条记录
                    # 这样即便用户没流完，数据库里也能看到当前进度
                    db.update_last_message(session_id, content, reasoning)

    def shutdown(self):
        self.running = False
        self.worker.join()