from .configmanager import ConfigManager
from pathlib import Path
import shutil
#有办法不写这么丑吗
setting_yaml_path = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"
# 加载默认配置 如果配置文件不存在，则基于模板创建，并给出warning
if not setting_yaml_path.exists():
    print("settings.yaml not found, creating from template")
    setting_template_path = Path(__file__).parent.parent.parent.parent / "config" / "settings_template.yaml"
    shutil.copy(setting_template_path, setting_yaml_path)
    default_settings = ConfigManager(path=setting_yaml_path)
else:
    default_settings = ConfigManager(path=setting_yaml_path)


# 获取默认参数，直接使用嵌套路径
default_api_key = default_settings.get("default_llm_settings.default_api_key")
default_url = default_settings.get("default_llm_settings.default_url")
default_model = default_settings.get("default_llm_settings.default_model")