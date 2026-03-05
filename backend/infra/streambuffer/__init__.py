from backend.infra.streambuffer.stream_buffer_module import Stream_Buffer

# 不在此创建单例；由上层（如 app.global_resource）注入 MessageStore 后创建并导出 stream_buffer
__all__ = ["Stream_Buffer"]
