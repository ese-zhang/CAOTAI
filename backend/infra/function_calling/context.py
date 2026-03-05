"""
工具执行上下文：与外界解耦，可插拔。
- 所有路径类工具在 workspace_root 下解析，实现 per-Agent 目录隔离。
- skills 通过 SkillsProvider 注入，测试时可替换为 Mock，无需依赖 app/skills_manager。
"""
from pathlib import Path
from typing import Optional, Protocol

from backend.config import DOCUMENT_ROOT


class SkillsProvider(Protocol):
    """技能提供者协议：测试时可注入 Mock，无需依赖全局 skills_manager。"""

    def get_skill_content(self, skill_name: str) -> str: ...
    def search_skills(self, query: str, n: int = 5): ...
    def get_skill_asset(self, skill_name: str, relative_path: str) -> str: ...
    def get_skill_script_path(self, skill_name: str, script_name: str) -> str: ...
    def list_skill_assets(self, skill_name: str): ...


class ToolContext:
    """
    单次工具执行的上下文。
    - workspace_root: 该 Agent 允许操作的工作目录，相对路径在此下解析。
    - agent_id / session_id: 用于权限与审计。
    - skills_provider: 可选，技能类工具使用；未提供时技能类工具可返回提示或跳过。
    """

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        agent_id: str = "",
        session_id: str = "",
        skills_provider: Optional[SkillsProvider] = None,
    ):
        self.workspace_root = Path(workspace_root or DOCUMENT_ROOT).resolve()
        self.agent_id = agent_id
        self.session_id = session_id
        self.skills_provider = skills_provider

    def resolve_path(self, path_str: str) -> Path:
        """
        将传入路径解析为绝对路径：相对路径相对于 workspace_root，且禁止逃逸出工作区。
        """
        p = Path(path_str)
        if not p.is_absolute():
            p = self.workspace_root / path_str
        resolved = p.resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(f"路径不得超出工作区: {path_str}")
        return resolved
