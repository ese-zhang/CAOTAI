from backend.infra.skills.skillsmanager import SkillsManager

skills_manager = SkillsManager()
# 确保工具在 Agent 使用前完成注册（infra 层 register_tool 的副作用）
import backend.infra.function_calling.register_tool  # noqa: F401, E402

