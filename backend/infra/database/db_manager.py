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
            # Migration: add agent_name to sessions if missing
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN agent_name TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists
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
            # 3. Agents table (agent_name PK, role_settings_yaml, system_prompt_text)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_name TEXT PRIMARY KEY,
                    role_settings_yaml TEXT,
                    system_prompt_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.commit()

    # ---------- Sessions (agent binding) ----------

    def get_new_session_id(self) -> str:
        """
        返回一个之前没有使用过的会话 id(格式 session_<数字>, 取当前最大数字 +1)
        """
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT session_id FROM sessions WHERE session_id LIKE 'session_%'")
        max_num = 0
        for row in cursor.fetchall():
            sid = row["session_id"]
            try:
                num = int(sid.split("_", 1)[1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                continue
        return f"session_{max_num + 1}"

    def create_session_for_agent(self, session_id: str, agent_name: str):
        """Create a session bound to the agent and append system message. No-op if session already exists."""
        if self.get_session_agent_name(session_id) is not None:
            return
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO sessions (session_id, agent_name) VALUES (?, ?)",
            (session_id, agent_name),
        )
        conn.commit()
        agent = self.get_agent(agent_name)
        system_prompt_text = (agent.get("system_prompt_text") or "") if agent else ""
        self.append_message(session_id, {"role": "system", "content": system_prompt_text})

    def get_session_agent_name(self, session_id: str) -> Optional[str]:
        """Return agent_name for the session, or None if not found."""
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT agent_name FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return row["agent_name"]

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

    # ---------- Agents ----------

    def upsert_agent(self, agent_name: str, role_settings_yaml: str, system_prompt_text: str):
        """Insert or replace agent; set updated_at to CURRENT_TIMESTAMP."""
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO agents (agent_name, role_settings_yaml, system_prompt_text, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (agent_name, role_settings_yaml, system_prompt_text))
        conn.commit()

    def list_agent_names(self) -> List[str]:
        """Return list of all agent names in the agents table."""
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT agent_name FROM agents")
        return [row["agent_name"] for row in cursor.fetchall()]

    def get_agent(self, agent_name: str) -> Optional[Dict]:
        """Return one row as dict with keys agent_name, role_settings_yaml, system_prompt_text, created_at, updated_at, or None."""
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_name = ?", (agent_name,))
        row = cursor.fetchone()
        if row is None:
            return None
        return {k: row[k] for k in row.keys()}

    def delete_agent(self, agent_name: str):
        """删除Agent与相关联的对话"""
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM messages WHERE session_id IN (SELECT session_id FROM sessions WHERE agent_name = ?)",
            (agent_name,),
        )
        conn.execute("DELETE FROM sessions WHERE agent_name = ?", (agent_name,))
        conn.execute("DELETE FROM agents WHERE agent_name = ?", (agent_name,))
        conn.commit()

    def self_check(self):
        def run_agent_yaml_self_check() -> None:
            """当原有的role_settings.yaml被丢失了，从数据库中重新写入(除了llm_setttings设置为默认)"""
            from pathlib import Path
            root = Path(__file__).resolve().parents[3]
            for agent_name in self.list_agent_names():
                path = root / "agent" / agent_name / "role_setting.yaml"
                if path.exists():
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                row = self.get_agent(agent_name)
                yaml_content = (row.get("role_settings_yaml") or "").rstrip()
                body = yaml_content + "\nllm_settings: \"default\"\n"
                path.write_text(body, encoding="utf-8")
        run_agent_yaml_self_check()