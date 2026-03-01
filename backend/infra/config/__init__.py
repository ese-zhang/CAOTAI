from ..predefined.llm_settings_property import LLMSettingsProperty
from .configmanager import ConfigManager
from pathlib import Path
import shutil
setting_yaml_path = Path(__file__).resolve().parents[3] / "config" / "settings.yaml"
# 加载默认配置 如果配置文件不存在，则基于模板创建，并给出warning
if not setting_yaml_path.exists():
    print("settings.yaml not found, creating from template")
    setting_template_path = Path(__file__).parent.parent.parent.parent / "config" / "settings_template.yaml"
    shutil.copy(setting_template_path, setting_yaml_path)
    default_settings = ConfigManager(path=setting_yaml_path)
else:
    default_settings = ConfigManager(path=setting_yaml_path)


# 获取默认参数，直接使用嵌套路径
DEFAULT_API_KEY = default_settings.get("default_llm_settings.default_api_key")
DEFAULT_URL = default_settings.get("default_llm_settings.default_url")
DEFAULT_MODEL = default_settings.get("default_llm_settings.default_model")
DOCUMENT_ROOT = default_settings.get("document_root")
AGENT_ROOT = f"{DOCUMENT_ROOT}/agent"

#获取可选参数
"""
llm_settings_options:
  option_1:
    model: Pro/MiniMaxAI/MiniMax-M2.5
    url: https://api.siliconflow.cn/v1
    api_key: sk-12112121121
"""
try:
    LLM_SETTINGS_OPTIONS = default_settings.get("llm_settings_options")
    # 通过循环，读取可选项，并保存为一组默认配置结构体, 如OPTION_1 = ...
    for key, value in LLM_SETTINGS_OPTIONS.items():
        var_name = key.upper()
        globals()[var_name] = LLMSettingsProperty(
            url=value.get("url"),
            model=value.get("model"),
            api_key=value.get("api_key")
        )
except:
    LLM_SETTINGS_OPTIONS = []