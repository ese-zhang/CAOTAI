import difflib
import re
from pathlib import Path

import yaml


def _get_document_root():
    from backend.infra.config import DOCUMENT_ROOT
    return Path(DOCUMENT_ROOT)


class SkillsManager:
    def __init__(self):
        self.skills_root = _get_document_root() / "skills"

    def list_skills(self):
        if not self.skills_root.exists() or not self.skills_root.is_dir():
            return []
        result = []
        for child in self.skills_root.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                result.append(child.name)
        return result

    def get_skill_content(self, name: str) -> str:
        names = self.list_skills()
        name_lower = name.strip().lower()
        matched = None
        for n in names:
            if n.lower() == name_lower:
                matched = n
                break
        if matched is None:
            return f"未找到技能: {name}"
        path = self.skills_root / matched / "SKILL.md"
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {}
        try:
            data = yaml.safe_load(match.group(1))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def search_skills(self, query: str, n: int = 5) -> list:
        skills = self.list_skills()
        candidates = []
        for skill_name in skills:
            path = self.skills_root / skill_name / "SKILL.md"
            raw = path.read_text(encoding="utf-8", errors="replace")
            meta = self._parse_frontmatter(raw)
            name = meta.get("name") or skill_name
            desc = meta.get("description") or ""
            if not desc and not meta:
                continue
            text = f"{name} {desc}"
            score = 0.0
            if query.lower() in text.lower():
                score = 1.0
            else:
                for part in query.split():
                    if part.lower() in text.lower():
                        score += 0.5
            if score == 0 and query:
                ratio = difflib.SequenceMatcher(None, query.lower(), text.lower()).ratio()
                score = ratio * 0.5
            candidates.append((score, {"name": name, "description": desc}))
        candidates.sort(key=lambda x: -x[0])
        return [c[1] for c in candidates[:n]]

    def _resolve_skill_dir(self, name: str):
        """Return skill directory name (from list_skills) if name matches (case-insensitive), else None."""
        names = self.list_skills()
        name_lower = name.strip().lower()
        for n in names:
            if n.lower() == name_lower:
                return n
        return None

    ALLOWED_PREFIXES = ("references/", "assets/", "scripts/")

    def get_skill_asset(self, skill_name: str, relative_path: str) -> str:
        matched = self._resolve_skill_dir(skill_name)
        if matched is None:
            return f"未找到技能: {skill_name}"
        rel = relative_path.strip().replace("\\", "/")
        if not rel or ".." in rel or rel.startswith("/"):
            return "Invalid path: only references/, assets/, scripts/ under skill are allowed."
        allowed = any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in self.ALLOWED_PREFIXES)
        if not allowed:
            return "Invalid path: only references/, assets/, scripts/ under skill are allowed."
        skill_root = self.skills_root / matched
        full = (skill_root / rel).resolve()
        try:
            full.relative_to(skill_root.resolve())
        except ValueError:
            return "Invalid path: path escapes skill directory."
        if not full.exists() or not full.is_file():
            return f"未找到文件: {relative_path}"
        try:
            return full.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Cannot read as text: {e}"

    def get_skill_script_path(self, skill_name: str, script_name: str) -> str:
        matched = self._resolve_skill_dir(skill_name)
        if matched is None:
            return f"未找到技能: {skill_name}"
        script_name = script_name.strip().replace("\\", "/")
        if ".." in script_name or "/" in script_name:
            return "Invalid script name: use filename only, e.g. compare.py"
        path = self.skills_root / matched / "scripts" / script_name
        if not path.exists() or not path.is_file():
            return f"未找到脚本: {script_name}"
        return str(path.resolve())

    def list_skill_assets(self, skill_name: str) -> list:
        matched = self._resolve_skill_dir(skill_name)
        if matched is None:
            return []
        skill_root = self.skills_root / matched
        result = []
        for sub in ("references", "scripts", "assets"):
            d = skill_root / sub
            if not d.is_dir():
                continue
            for f in d.rglob("*"):
                if f.is_file():
                    result.append(str(f.relative_to(skill_root).as_posix()))
        return sorted(result)
