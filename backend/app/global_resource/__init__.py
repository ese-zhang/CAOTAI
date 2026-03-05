# 上层在此组装 infra：只在此处做「infra 之间的装配」，避免 infra 内部互相 import
from backend.infra.database import db
from backend.infra.function_calling import ToolManager, tool_manager
from backend.infra.streambuffer import Stream_Buffer

# 注入 MessageStore，避免 streambuffer 直接依赖 database
stream_buffer = Stream_Buffer(message_store=db)

__all__ = ["ToolManager", "tool_manager", "stream_buffer", "db"]
