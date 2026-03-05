"""
消息存储抽象：infra 内仅依赖此协议，不互相 import 具体实现。
上层（app）负责创建具体实现（如 MessageDB）并注入到 Stream_Buffer 等。
"""
from typing import Dict, List, Optional, Protocol


class MessageStore(Protocol):
    """会话消息存储协议：load/append/update，供 Stream_Buffer 等使用。"""

    def load_messages(self, session_id: str) -> List[Dict]:
        """按 session_id 加载消息列表，无则返回 []。"""
        ...

    def append_message(self, session_id: str, msg: Dict) -> None:
        """追加一条消息。"""
        ...

    def update_last_message(
        self,
        session_id: str,
        content: Optional[str] = None,
        reasoning: Optional[str] = None,
        tool_calls: Optional[List] = None,
    ) -> None:
        """更新该 session 最后一条消息的 content / reasoning / tool_calls。"""
        ...
