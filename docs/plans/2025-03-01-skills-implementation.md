# Skills 系统实现计划（符合 Agent Skills 规范）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.  
> **规范参考:** [Agent Skills Specification](https://agentskills.io/specification) — 每个技能为**目录**，内含必需文件 `SKILL.md`，且 SKILL.md 含必填 frontmatter：`name`、`description`。

**Goal:** 在 core 下实现符合 Agent Skills 规范的可配置 skills 系统：SkillsManager（目录+SKILL.md + references/scripts/assets 加载）、load_skill、search_skills、**load_skill_asset**、**get_skill_script_path**、**list_skill_assets**，技能根目录为 `DOCUMENT_ROOT/skills`。

**Architecture:** `backend/core/skills/` 下实现 SkillsManager（子目录含 SKILL.md 即为一技能；解析 frontmatter；按名加载 SKILL.md 全文；**get_skill_asset / get_skill_script_path / list_skill_assets** 支持 references/、scripts/、assets/）；在 `register_tool.py` 注册上述工具；通过 `backend.infra.config.DOCUMENT_ROOT` 获取根目录。

**Tech Stack:** Python 3, pathlib, YAML frontmatter（正则或 PyYAML）, difflib 排序，现有 ToolManager 注册方式。

---

## Task 1: 创建 core/skills 包与 SkillsManager 骨架

**Files:**
- Create: `backend/core/skills/__init__.py`
- Create: `backend/core/skills/skills_manager.py`
- Test: `test/core/skills/test_skills_manager.py`

**Step 1: 写失败测试**

在 `test/core/skills/test_skills_manager.py` 中：

```python
import pytest
from pathlib import Path
from backend.core.skills.skills_manager import SkillsManager

def test_skills_root_uses_document_root():
    mgr = SkillsManager()
    from backend.infra.config import DOCUMENT_ROOT
    expected = Path(DOCUMENT_ROOT) / "skills"
    assert mgr.skills_root == expected
```

**Step 2: 运行测试确认失败**

```bash
pytest test/core/skills/test_skills_manager.py::test_skills_root_uses_document_root -v
```
Expected: FAIL (SkillsManager 或 skills_root 不存在)

**Step 3: 最小实现**

- `backend/core/skills/__init__.py`:

```python
from .skills_manager import SkillsManager
__all__ = ["SkillsManager"]
```

- `backend/core/skills/skills_manager.py`:

```python
from pathlib import Path

def _get_document_root():
    from backend.infra.config import DOCUMENT_ROOT
    return Path(DOCUMENT_ROOT)

class SkillsManager:
    def __init__(self):
        self.skills_root = _get_document_root() / "skills"
```

**Step 4: 运行测试确认通过**

```bash
pytest test/core/skills/test_skills_manager.py::test_skills_root_uses_document_root -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/core/skills/__init__.py backend/core/skills/skills_manager.py test/core/skills/test_skills_manager.py
git commit -m "feat(skills): add SkillsManager skeleton and skills_root"
```

---

## Task 2: SkillsManager.list_skills 与 get_skill_content（目录+SKILL.md，按名加载，忽略大小写）

**约定（Agent Skills 规范）：** 每个技能是 `skills_root` 下的一个**子目录**，且该目录内存在 **SKILL.md**。技能名称以**目录名**为准（规范要求 frontmatter 的 name 与目录名一致）。

**Files:**
- Modify: `backend/core/skills/skills_manager.py`
- Test: `test/core/skills/test_skills_manager.py`

**Step 1: 写失败测试**

在测试文件中增加（使用目录结构，非单文件）：

```python
def test_list_skills_empty_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    assert mgr.list_skills() == []

def test_list_skills_returns_dir_names_with_skill_md(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "data-analysis").mkdir()
    (tmp_path / "skills" / "data-analysis" / "SKILL.md").write_text("---\nname: data-analysis\ndescription: 数据分析\n---\n# Body")
    (tmp_path / "skills" / "code-review").mkdir()
    (tmp_path / "skills" / "code-review" / "SKILL.md").write_text("---\nname: code-review\ndescription: 代码审查\n---\n# Body")
    (tmp_path / "skills" / "empty-dir").mkdir()  # 无 SKILL.md，不应出现在列表中
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    assert set(mgr.list_skills()) == {"data-analysis", "code-review"}

def test_get_skill_content_exact_match(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "hello").mkdir()
    (tmp_path / "skills" / "hello" / "SKILL.md").write_text("---\nname: hello\ndescription: Hi\n---\ncontent here")
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    assert "content here" in mgr.get_skill_content("hello")
    assert "name: hello" in mgr.get_skill_content("hello")

def test_get_skill_content_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "pdf-processing").mkdir()
    (tmp_path / "skills" / "pdf-processing" / "SKILL.md").write_text("---\nname: pdf-processing\ndescription: PDF\n---\ncontent")
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    assert "content" in mgr.get_skill_content("PDF-Processing")

def test_get_skill_content_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    out = mgr.get_skill_content("nonexistent")
    assert "未找到" in out or "not found" in out.lower()
```

**Step 2: 运行测试确认失败**

```bash
pytest test/core/skills/test_skills_manager.py -v
```
Expected: 新测试 FAIL（方法未实现或结构不符）

**Step 3: 实现 list_skills 与 get_skill_content**

- `list_skills()`: 若 `self.skills_root` 不存在则返回 `[]`；否则遍历 `self.skills_root` 下的**子目录**，仅保留「目录内存在 `SKILL.md` 文件」的目录，返回这些目录的名称列表（即技能 name 列表）。
- `get_skill_content(name)`: 在 `list_skills()` 得到的名称中做**忽略大小写**的匹配（如 `name.lower() == candidate.lower()`）；若匹配到唯一目录，则读取该目录下的 `SKILL.md`（`(self.skills_root / matched_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")`）并返回全文；否则返回 `"未找到技能: {name}"` 之类字符串。

**Step 4: 运行测试确认通过**

```bash
pytest test/core/skills/test_skills_manager.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add backend/core/skills/skills_manager.py test/core/skills/test_skills_manager.py
git commit -m "feat(skills): add list_skills and get_skill_content (dir+SKILL.md, case-insensitive)"
```

---

## Task 3: 解析 SKILL.md frontmatter 与 search_skills

**约定：** 按 [Agent Skills 规范](https://agentskills.io/specification)，SKILL.md 必须包含 YAML frontmatter，其中 **name**、**description** 为必填。search_skills 仅需读取 frontmatter 的 name 与 description 做匹配，无需加载正文。

**Files:**
- Modify: `backend/core/skills/skills_manager.py`（增加 frontmatter 解析与 search_skills）
- Test: `test/core/skills/test_skills_manager.py`

**Step 1: 写失败测试**

```python
def test_search_skills_returns_name_and_description(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "data-analysis").mkdir()
    (tmp_path / "skills" / "data-analysis" / "SKILL.md").write_text(
        "---\nname: data-analysis\ndescription: 数据分析与可视化，在需要做图表或统计时使用。\n---\n# Data"
    )
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    results = mgr.search_skills("数据分析", n=5)
    assert len(results) >= 1
    assert results[0]["name"] == "data-analysis"
    assert "数据分析" in results[0]["description"]

def test_search_skills_respects_n(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    for i in range(5):
        (tmp_path / "skills" / f"skill-{i}").mkdir()
        (tmp_path / "skills" / f"skill-{i}" / "SKILL.md").write_text(
            f"---\nname: skill-{i}\ndescription: Skill number {i}\n---\n# S{i}"
        )
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    results = mgr.search_skills("skill", n=2)
    assert len(results) == 2
```

**Step 2: 运行测试确认失败**

**Step 3: 实现 frontmatter 解析与 search_skills**

- **Frontmatter 解析**：实现一个内部方法（如 `_parse_frontmatter(content: str) -> dict`），识别 SKILL.md 内容中第一个 `---` 到第二个 `---` 之间的 YAML，解析出 `name`、`description`（必填）。若某技能 SKILL.md 无有效 frontmatter 或缺少 name/description，该技能在 search_skills 中可跳过或使用目录名 + 空 description。
- **search_skills(query, n=5)**：对每个在 `list_skills()` 中的技能，读取其 `SKILL.md`（或仅读前若干字节以解析 frontmatter，减少 I/O），得到 (name, description)；将 query 与 name + description 做匹配（关键词包含或 difflib 相似度），排序后取前 n 条，返回 `[{"name": ..., "description": ...}]`。

**Step 4: 运行测试确认通过**

**Step 5: Commit**

```bash
git add backend/core/skills/skills_manager.py test/core/skills/test_skills_manager.py
git commit -m "feat(skills): add SKILL.md frontmatter parsing and search_skills"
```

---

## Task 4: 注册 load_skill 与 search_skills 工具

**Files:**
- Modify: `backend/core/tools/register_tool.py`（以及 tools_list）
- Test: 可选，工具层或沿用 SkillsManager 单元测试

**Step 1: 写失败测试（必须）**

例如在测试中调用 `tool_manager._registry["load_skill"]("data-analysis")` 等，确认工具存在且返回字符串。

**Step 2: 实现工具并注册**

在 `register_tool.py` 中：

- `from backend.core.skills import SkillsManager`
- 定义 `load_skill(skill_name: str)`：`return SkillsManager().get_skill_content(skill_name)`
- 定义 `search_skills(query: str, n: int = 5)`：`return SkillsManager().search_skills(query, n)`
- 使用 `@tool_manager.register(name="load_skill", description="...", parameters={...})` 与 `@tool_manager.register(name="search_skills", ...)` 注册，参数 schema 与现有工具一致。
- 将 `"load_skill"` 和 `"search_skills"` 加入 `tools_list`。

**Step 3: 运行测试**

```bash
pytest test/core/skills/ test/core/tools/ -v
```

**Step 4: Commit**

```bash
git add backend/core/tools/register_tool.py
git commit -m "feat(tools): register load_skill and search_skills"
```

---

## Task 5: SkillsManager 支持 references/scripts/assets（get_skill_asset、get_skill_script_path、list_skill_assets）

**约定：** 每个技能目录下可含 `references/`、`scripts/`、`assets/`。需支持：(1) 按相对路径加载某文件**内容**（用于规范/模板）；(2) 返回某脚本的**绝对路径**供 run_shell_command 执行；(3) 列出该技能下可用的资源路径供 Agent 发现。

**Files:**
- Modify: `backend/core/skills/skills_manager.py`
- Test: `test/core/skills/test_skills_manager.py`

**Step 1: 写失败测试**

```python
def test_get_skill_asset_returns_content(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "doc-spec").mkdir(parents=True)
    (tmp_path / "skills" / "doc-spec" / "SKILL.md").write_text("---\nname: doc-spec\ndescription: 文档规范\n---\n# Spec")
    (tmp_path / "skills" / "doc-spec" / "references").mkdir()
    (tmp_path / "skills" / "doc-spec" / "references" / "SPEC.md").write_text("# 输出必须符合本规范")
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    assert "输出必须符合本规范" in mgr.get_skill_asset("doc-spec", "references/SPEC.md")

def test_get_skill_asset_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "x").mkdir(parents=True)
    (tmp_path / "skills" / "x" / "SKILL.md").write_text("---\nname: x\ndescription: x\n---\n")
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    out = mgr.get_skill_asset("x", "../x/references/SPEC.md")
    assert "未找到" in out or "不允许" in out or "invalid" in out.lower()

def test_get_skill_script_path_returns_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "file-diff").mkdir(parents=True)
    (tmp_path / "skills" / "file-diff" / "SKILL.md").write_text("---\nname: file-diff\ndescription: 文件比对\n---\n")
    (tmp_path / "skills" / "file-diff" / "scripts").mkdir()
    (tmp_path / "skills" / "file-diff" / "scripts" / "compare.py").write_text("# compare")
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    path = mgr.get_skill_script_path("file-diff", "compare.py")
    assert path.endswith("scripts" + os.sep + "compare.py") or "compare.py" in path
    assert Path(path).exists()

def test_get_skill_script_path_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "x").mkdir(parents=True)
    (tmp_path / "skills" / "x" / "SKILL.md").write_text("---\nname: x\ndescription: x\n---\n")
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    out = mgr.get_skill_script_path("x", "nonexistent.py")
    assert "未找到" in out or "not found" in out.lower()

def test_list_skill_assets_returns_relative_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.skills.skills_manager._get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "full").mkdir(parents=True)
    (tmp_path / "skills" / "full" / "SKILL.md").write_text("---\nname: full\ndescription: full\n---\n")
    (tmp_path / "skills" / "full" / "references").mkdir(parents=True)
    (tmp_path / "skills" / "full" / "references" / "R.md").write_text("")
    (tmp_path / "skills" / "full" / "scripts").mkdir(parents=True)
    (tmp_path / "skills" / "full" / "scripts" / "run.py").write_text("")
    from backend.core.skills.skills_manager import SkillsManager
    mgr = SkillsManager()
    paths = mgr.list_skill_assets("full")
    assert "references/R.md" in paths or any("R.md" in p for p in paths)
    assert "scripts/run.py" in paths or any("run.py" in p for p in paths)
```

（测试中如需 `os` 或 `Path`，在文件头 import。）

**Step 2: 运行测试确认失败**

```bash
pytest test/core/skills/test_skills_manager.py -v -k "get_skill_asset or get_skill_script_path or list_skill_assets"
```

**Step 3: 实现**

- **允许的子目录**：仅允许相对路径以 `references/`、`assets/`、`scripts/` 之一开头；解析时用 `Path(relative_path)` 并 `resolve()`，再检查解析后的路径是否仍在 `skill_root` 内（且不以 `..` 逃逸）。
- **get_skill_asset(skill_name, relative_path)**：先按名称解析出技能目录；校验 relative_path 落在 references/assets/scripts 下且在技能目录内；若为文本文件（按扩展名或尝试 UTF-8 解码）则返回内容，否则可返回错误或路径（实现可先仅支持文本）。
- **get_skill_script_path(skill_name, script_name)**：解析出 `skills_root / matched_skill / "scripts" / script_name`，若存在且为文件则返回其 `resolve().as_posix()` 或 `str(resolve())`；否则返回「未找到脚本」类字符串。
- **list_skill_assets(skill_name)**：遍历该技能目录下的 `references/`、`scripts/`、`assets/`（若存在），收集相对路径（如 `references/REFERENCE.md`、`scripts/compare.py`），去重后返回列表。

**Step 4: 运行测试确认通过**

**Step 5: Commit**

```bash
git add backend/core/skills/skills_manager.py test/core/skills/test_skills_manager.py
git commit -m "feat(skills): add get_skill_asset, get_skill_script_path, list_skill_assets"
```

---

## Task 6: 注册 load_skill_asset、get_skill_script_path、list_skill_assets 工具

**Files:**
- Modify: `backend/core/tools/register_tool.py` 及 `tools_list`

**Step 1:** 在 `register_tool.py` 中增加：
- `load_skill_asset(skill_name: str, relative_path: str)`：调用 `SkillsManager().get_skill_asset(skill_name, relative_path)`，description 注明用于加载技能内的规范/模板文件（references 或 assets 下的相对路径）。
- `get_skill_script_path(skill_name: str, script_name: str)`：调用 `SkillsManager().get_skill_script_path(skill_name, script_name)`，description 注明返回脚本绝对路径，供 run_shell_command 执行（如文件比对、格式校验）。
- `list_skill_assets(skill_name: str)`：调用 `SkillsManager().list_skill_assets(skill_name)`，description 注明列出该技能下 references/、scripts/、assets/ 中的相对路径。
- 将 `"load_skill_asset"`、`"get_skill_script_path"`、`"list_skill_assets"` 加入 `tools_list`。

**Step 2: 运行测试**

```bash
pytest test/core/skills/ test/core/tools/ -v
```

**Step 3: Commit**

```bash
git add backend/core/tools/register_tool.py
git commit -m "feat(tools): register load_skill_asset, get_skill_script_path, list_skill_assets"
```

---

## Task 7: 文档与可选“首次创建目录”

**Files:**
- Create or Modify: `doc/skills.md` 或 README 中一节
- 可选: 首次使用或启动时创建 `skills_root` 并写入 README，说明按 [Agent Skills 规范](https://agentskills.io/specification) 放置技能

**Step 1–2:** 在文档中说明：

- 技能根目录：`DOCUMENT_ROOT/skills`（与 chat_history 同根，配置见 `backend.infra.config`）。
- 每个技能是一个**子目录**，目录内**必须**包含 `SKILL.md`；可选 `references/`、`scripts/`、`assets/`（规范：https://agentskills.io/specification）。
- Agent 可使用 `search_skills` → `load_skill(name)` 获取 SOP；使用 **load_skill_asset(skill_name, relative_path)** 加载规范/模板（如 `references/SPEC.md`）；使用 **list_skill_assets(skill_name)** 查看可用资源，再使用 **get_skill_script_path(skill_name, script_name)** 取得脚本绝对路径，配合 `run_shell_command` 执行（如两文件 1:1 比对、格式校验）。

**Step 4: Commit**

```bash
git add doc/skills.md
git commit -m "docs: add skills directory, references/scripts usage and Agent Skills spec"
```

---

## 执行方式

计划已保存到 `docs/plans/2025-03-01-skills-implementation.md`。

**两种执行方式：**

1. **本会话子 agent 驱动**：按任务分派子 agent，每步完成后审查再进入下一步。
2. **并行会话**：在新会话中打开该计划，使用 executing-plans 按检查点批量执行。
