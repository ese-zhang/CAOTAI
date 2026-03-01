import yaml
import threading
import os

class ConfigManager:
    def __init__(self, path):
        """
        初始化 ConfigManager
        :param path: YAML 文件路径
        """
        self.path = path
        self._lock = threading.Lock()
        self._dirty = False  # 标记配置是否被修改
        self._config = {}
        self.load()

    def load(self):
        """从 YAML 文件加载配置到内存"""
        try:
            if os.path.exists(self.path):
                with open(self.path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            else:
                self._config = {}
        except yaml.YAMLError as e:
            raise RuntimeError(f"YAML parse error: {e}")

    def get(self, path, default=None):
        """
        获取嵌套配置
        path 支持 "section.key.subkey" 形式
        """
        keys = path.split(".")
        data = self._config
        for k in keys:
            if not isinstance(data, dict):
                return default
            data = data.get(k, default)
        return data

    def set(self, path, value):
        """
        设置嵌套配置，自动创建中间字典
        """
        keys = path.split(".")
        with self._lock:
            data = self._config
            for k in keys[:-1]:
                if k not in data or not isinstance(data[k], dict):
                    data[k] = {}
                data = data[k]
            data[keys[-1]] = value
            self._dirty = True

    def save(self):
        """将内存中的配置写回 YAML 文件（如果有修改）"""
        with self._lock:
            if not self._dirty:
                return
            with open(self.path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._config, f, allow_unicode=True)
            self._dirty = False

    def reload_if_modified(self):
        """可选方法：检查文件是否被外部修改并重新加载"""
        try:
            mtime = os.path.getmtime(self.path)
        except FileNotFoundError:
            return
        if getattr(self, '_last_mtime', None) != mtime:
            self.load()
            self._last_mtime = mtime