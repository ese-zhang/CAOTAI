from pathlib import Path
from .db_manager import MessageDB
from ..config import DOCUMENT_ROOT

db_path = Path(DOCUMENT_ROOT) / "chat_history.db"
db = MessageDB(db_path=str(db_path))
__all__ = [
    "db"
]