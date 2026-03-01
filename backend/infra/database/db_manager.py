import sqlite3
import json
import threading
from typing import List, Dict, Optional

class MessageDB:
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, "conn"):
            # 使用 check_same_thread=False 配合 Lock 使用
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # 1. 存储 Session 元数据
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 2. 存储单条 Message，增加索引以优化查询
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    reasoning_content TEXT,
                    tool_calls_json TEXT,
                    tool_call_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id)")
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.commit()

    # ---------- 增量写入接口 ----------

    def append_message(self, session_id: str, msg: Dict):
        """增量插入单条消息"""
        conn = self._get_conn()
        # 确保 session 存在
        conn.execute("INSERT OR IGNORE INTO sessions (session_id) VALUES (?)", (session_id,))
        
        # 解析数据（兼容你现有的字典结构）
        # 在 append_message 方法内增加解析
        tool_call_id = msg.get("tool_call_id")  # 获取字段
        role = msg.get("role")
        content = msg.get("content")
        model_extra = msg.get("model_extra", {})
        reasoning = model_extra.get("reasoning_content", "")
        tool_calls = json.dumps(msg.get("tool_calls")) if msg.get("tool_calls") else None

        # 并在 SQL 执行时存入
        conn.execute("""
            INSERT INTO messages (session_id, role, content, reasoning_content, tool_calls_json, tool_call_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, role, content, reasoning, tool_calls, tool_call_id))
        conn.commit()

    def update_last_message(self, session_id: str, content: str, reasoning: str, tool_calls: Optional[List] = None):
        """更新该 session 的最后一条消息（用于 Streaming 结束时的最终同步）"""
        conn = self._get_conn()
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        
        # 找到最后一条消息的 ID 并更新
        conn.execute("""
            UPDATE messages 
            SET content = ?, reasoning_content = ?, tool_calls_json = ?
            WHERE id = (SELECT MAX(id) FROM messages WHERE session_id = ?)
        """, (content, reasoning, tool_calls_json, session_id))
        conn.commit()

    # ---------- 读取接口 ----------

    def load_messages(self, session_id: str) -> List[Dict]:
        """全量读取并还原为 Dict 格式"""
        cursor = self._get_conn().cursor()
        cursor.execute("""
            SELECT role, content, reasoning_content, tool_calls_json 
            FROM messages WHERE session_id = ? ORDER BY id ASC
        """, (session_id,))
        
        results = []
        for row in cursor.fetchall():
            msg = {
                "role": row["role"],
                "content": row["content"],
            }
            if row["tool_calls_json"]:
                msg["tool_calls"] = json.loads(row["tool_calls_json"])
            results.append(msg)
            if row["reasoning_content"]:
                msg["reasoning_content"] = row["reasoning_content"]
        return results

    # 在 db_manager.py 的 MessageDB 类中添加
    def clear_session(self, session_id: str):
        """清空指定 session 的所有历史记录"""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        print(f"--- 已清理 Session: {session_id} ---")