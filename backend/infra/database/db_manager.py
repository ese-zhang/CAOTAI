"""
Message 持久化：存储模型与语义模型解耦，抗 OpenAI message 协议演化。

设计原则：
- SQL 只存最小索引信息（session_id, role, created_at），用于查询/排序。
- 完整 message 以 JSON 原样存入 payload，不假设字段集合稳定。
- 新增/变更 message 字段（如 name、multimodal、tool 扩展）无需改 schema。
"""
import sqlite3
import json
import threading
from typing import List, Dict, Optional, Any

# ---------------------------------------------------------------------------
# 表结构（稳定、少迁移）
# ---------------------------------------------------------------------------
# sessions: session_id PK, created_at, agent_name
#   - 职责：会话元数据与 agent 绑定，与 message 协议无关。
#
# messages:
#   - id: 自增主键，保证顺序。
#   - session_id: 归属会话，索引列，用于 load_messages(session_id)。
#   - role: 索引列，用于按角色过滤（如“最后一条 assistant”），且为 OpenAI 稳定核心字段。
#   - created_at: 排序与时间查询。
#   - payload: TEXT，完整 message 的 JSON；所有业务字段（content / tool_calls / model_extra / name / ...）均在此，不单独建列。
#
# 不进 SQL 列的理由：content / reasoning_content / tool_calls / tool_call_id / name / 任何扩展
# 均可能随 API 演化或厂商扩展，放入 payload 可避免后续 migration。
# ---------------------------------------------------------------------------

_SCHEMA_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name TEXT
)
"""

_SCHEMA_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payload TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
)
"""

_SCHEMA_AGENTS = """
CREATE TABLE IF NOT EXISTS agents (
    agent_name TEXT PRIMARY KEY,
    role_settings_yaml TEXT,
    system_prompt_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class MessageDB:
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_SCHEMA_SESSIONS)
            conn.execute(_SCHEMA_AGENTS)
            self._ensure_messages_schema(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.commit()

    def _ensure_messages_schema(self, conn: sqlite3.Connection) -> None:
        """若 messages 表为旧版（无 payload），则迁移到新 schema；否则跳过。"""
        cursor = conn.execute("PRAGMA table_info(messages)")
        columns = [row[1] for row in cursor.fetchall()]
        if "payload" in columns:
            return
        if not columns:
            conn.execute(_SCHEMA_MESSAGES)
            return
        # 旧表存在：按列存在情况迁移
        conn.execute(_SCHEMA_MESSAGES.replace("messages (", "messages_new ("))
        select_cols = ["id", "session_id", "role", "created_at", "content"]
        if "reasoning_content" in columns:
            select_cols.append("reasoning_content")
        if "tool_calls_json" in columns:
            select_cols.append("tool_calls_json")
        if "tool_call_id" in columns:
            select_cols.append("tool_call_id")
        sql = "SELECT " + ", ".join(select_cols) + " FROM messages"
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        for row in rows:
            r = dict(zip(select_cols, row))
            payload: Dict[str, Any] = {"role": r.get("role"), "content": r.get("content")}
            if r.get("reasoning_content"):
                payload["model_extra"] = {"reasoning_content": r["reasoning_content"]}
            if r.get("tool_calls_json"):
                payload["tool_calls"] = json.loads(r["tool_calls_json"])
            if r.get("tool_call_id"):
                payload["tool_call_id"] = r["tool_call_id"]
            conn.execute(
                "INSERT INTO messages_new (id, session_id, role, created_at, payload) VALUES (?, ?, ?, ?, ?)",
                (r["id"], r["session_id"], r["role"], r.get("created_at"), json.dumps(payload, ensure_ascii=False)),
            )
        conn.execute("DROP TABLE messages")
        conn.execute("ALTER TABLE messages_new RENAME TO messages")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")

    # ---------- Sessions (agent binding) ----------

    def get_new_session_id(self) -> str:
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
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT agent_name FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return row["agent_name"] if row is not None else None

    # ---------- 增量写入（协议不可知：整条 message 存 JSON）----------

    def append_message(self, session_id: str, msg: Dict) -> None:
        """插入单条消息。msg 为任意 dict，原样序列化进 payload，不依赖固定字段。"""
        conn = self._get_conn()
        conn.execute("INSERT OR IGNORE INTO sessions (session_id) VALUES (?)", (session_id,))
        role = msg.get("role") or ""
        payload_json = json.dumps(msg, ensure_ascii=False)
        conn.execute(
            "INSERT INTO messages (session_id, role, payload) VALUES (?, ?, ?)",
            (session_id, role, payload_json),
        )
        conn.commit()

    def update_last_message(
        self,
        session_id: str,
        content: Optional[str] = None,
        reasoning: Optional[str] = None,
        tool_calls: Optional[List] = None,
    ) -> None:
        """更新该 session 最后一条消息的 content / reasoning / tool_calls（用于流式结束同步）。"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, payload FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return
        msg_id, payload_json = row["id"], row["payload"]
        payload: Dict[str, Any] = json.loads(payload_json)
        if content is not None:
            payload["content"] = content
        if reasoning is not None:
            payload.setdefault("model_extra", {})["reasoning_content"] = reasoning
        if tool_calls is not None:
            payload["tool_calls"] = tool_calls
        conn.execute("UPDATE messages SET payload = ? WHERE id = ?", (json.dumps(payload, ensure_ascii=False), msg_id))
        conn.commit()

    # ---------- 读取（还原为 API 可用的 message 列表）----------

    def load_messages(self, session_id: str) -> List[Dict]:
        """按 id 顺序返回 message 列表，每项为完整 dict（含 role/content/tool_calls/model_extra 等），可直接用于 OpenAI 风格 API。"""
        cursor = self._get_conn().cursor()
        cursor.execute(
            "SELECT payload FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        return [json.loads(row["payload"]) for row in cursor.fetchall()]

    def clear_session(self, session_id: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        print(f"--- 已清理 Session: {session_id} ---")

    # ---------- Agents ----------

    def upsert_agent(self, agent_name: str, role_settings_yaml: str, system_prompt_text: str) -> None:
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO agents (agent_name, role_settings_yaml, system_prompt_text, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (agent_name, role_settings_yaml, system_prompt_text))
        conn.commit()

    def list_agent_names(self) -> List[str]:
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT agent_name FROM agents")
        return [row["agent_name"] for row in cursor.fetchall()]

    def get_agent(self, agent_name: str) -> Optional[Dict]:
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_name = ?", (agent_name,))
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    def delete_agent(self, agent_name: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM messages WHERE session_id IN (SELECT session_id FROM sessions WHERE agent_name = ?)",
            (agent_name,),
        )
        conn.execute("DELETE FROM sessions WHERE agent_name = ?", (agent_name,))
        conn.execute("DELETE FROM agents WHERE agent_name = ?", (agent_name,))
        conn.commit()

    def self_check(self) -> None:
        def run_agent_yaml_self_check() -> None:
            from pathlib import Path
            root = Path(__file__).resolve().parents[3]
            for agent_name in self.list_agent_names():
                path = root / "agent" / agent_name / "role_setting.yaml"
                if path.exists():
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                row = self.get_agent(agent_name)
                yaml_content = (row.get("role_settings_yaml") or "").rstrip()
                path.write_text(yaml_content + "\nllm_settings: \"default\"\n", encoding="utf-8")
        run_agent_yaml_self_check()
