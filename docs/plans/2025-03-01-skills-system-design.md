# Skills 系统设计（符合 Agent Skills 规范）

> 设计日期：2025-03-01  
> 规范参考：[Agent Skills Specification](https://agentskills.io/specification)  
> 目标：在 openseed 中引入可配置的 skills 系统，提供 SkillsManager、load_skill、search_skills，供 Agent 按需查找并加载 SOP。

## 1. 规范要点（agentskills.io）

- **技能即目录**：每个技能是一个目录，**至少包含** `SKILL.md` 文件。
- **目录结构示例**：
  ```
  skill-name/
  └── SKILL.md          # 必需
  ```
  可选子目录：`scripts/`、`references/`、`assets/`。本期要求**至少支持加载 references 与 scripts**：如技能内置比对脚本、格式校验脚本，或 references 中的文档规范/模板，供 Agent 按需加载或获取脚本路径并配合 `run_shell_command` 执行。
- **SKILL.md 格式**：必须是 **YAML frontmatter + Markdown 正文**。
  - **必填 frontmatter**：`name`、`description`。
  - **name**：1–64 字符，仅小写字母、数字、连字符；不得以连字符开头/结尾；不得含连续连字符；**必须与父目录名一致**。
  - **description**：1–1024 字符，非空；描述技能做什么、何时使用，建议含关键词便于检索。
  - 可选字段：`license`、`compatibility`、`metadata`、`allowed-tools`（本期可不解析，后续可扩展）。
- **渐进式披露**：启动时仅加载元数据（name + description）；激活技能时加载完整 SKILL.md 正文。本系统通过 `search_skills` 暴露元数据、`load_skill` 加载全文，与之一致。

## 2. 配置与目录

- **技能根目录**：`Path(DOCUMENT_ROOT) / "skills"`，`DOCUMENT_ROOT` 来自 `backend.infra.config`（与 chat_history 同根）。
- **技能识别规则**：在 `skills_root` 下，每个**子目录**若包含 `SKILL.md`，则视为一个技能。技能**名称**以 frontmatter 的 `name` 为准；规范要求 `name` 与目录名一致，故实现上可用「目录名」作为 name 的权威来源（解析 frontmatter 时校验一致或直接采用目录名）。
- **load_skill 匹配**：按名称**完全匹配、忽略大小写**（规范中 name 为小写，输入时允许用户写 Data-Analysis 匹配目录 data-analysis）。

## 3. 组件

### 3.1 SkillsManager（core/skills/skills_manager.py）

- **依赖**：`from backend.infra.config import DOCUMENT_ROOT`，`skills_root = Path(DOCUMENT_ROOT) / "skills"`。
- **职责**：
  - **list_skills()**：若 `skills_root` 不存在则返回 `[]`；否则遍历子目录，仅保留「目录内存在 `SKILL.md`」的目录，返回这些目录的名称列表（即技能 name 列表，与规范一致）。
  - **get_skill_content(name)**：在 `skills_root` 下查找名称与 `name` 匹配的子目录（忽略大小写），且该目录内存在 `SKILL.md`；若找到则读取并返回 `SKILL.md` 的**完整内容**（frontmatter + 正文）；无匹配时返回明确错误信息（如「未找到技能: xxx」）。
  - **search_skills(query, n=5)**：对每个有效技能目录读取其 `SKILL.md` 的 **frontmatter**，提取 `name` 与 `description`（必填）；基于「name + description」与 query 做关键词/相似度匹配，排序后取前 n 条，返回 `[{"name": "...", "description": "..."}]`。若某技能 frontmatter 无效（缺 name 或 description），可跳过或使用目录名与空 description，并在文档中建议用户按规范书写。
  - **get_skill_asset(skill_name, relative_path)**：在指定技能目录下，按相对路径加载文件**内容**（文本）。`relative_path` 相对于技能根目录，且**仅允许**落在 `references/`、`assets/` 或 `scripts/` 下的路径（如 `references/REFERENCE.md`、`references/FORMS.md`、`assets/template.md`）；禁止 `..` 及越界路径。用于加载规范文档、模板等，供输出符合某规范时参考。
  - **get_skill_script_path(skill_name, script_name)**：返回该技能目录下 `scripts/{script_name}` 的**绝对路径**（如 `compare.py` → `.../skills/file-diff/scripts/compare.py`）。Agent 可将该路径传给 `run_shell_command` 执行（如两文件 1:1 比对、格式校验等）。若文件不存在或路径不合法，返回明确错误信息。
  - **list_skill_assets(skill_name)**（可选）：列出该技能下 `references/`、`scripts/`、`assets/` 中的相对路径列表，便于 Agent 发现可加载的模板或可执行的脚本名。

### 3.2 SKILL.md 解析

- **Frontmatter**：以 `---` 开始和结束的 YAML 块；解析出 `name`、`description`（必填）。可选：`license`、`compatibility`、`metadata`、`allowed-tools` 可在后续扩展为元数据返回。
- **正文**：frontmatter 之后的 Markdown 内容，作为「技能指南/SOP」在 `load_skill` 时整份返回，不做格式限制（符合规范）。

### 3.3 工具（Tools）

- **load_skill(skill_name: str)**：调用 `SkillsManager().get_skill_content(skill_name)`，返回 SKILL.md 全文或错误信息。
- **search_skills(query: str, n: int = 5)**：调用 `SkillsManager().search_skills(query, n)`，返回前 n 条 `{name, description}` 列表。
- **load_skill_asset(skill_name: str, relative_path: str)**：调用 `SkillsManager().get_skill_asset(skill_name, relative_path)`，返回该技能下某文件（references/assets/scripts 内）的**文本内容**，用于加载规范、模板等。路径需在技能目录内且仅允许 `references/`、`assets/`、`scripts/` 下。
- **get_skill_script_path(skill_name: str, script_name: str)**：调用 `SkillsManager().get_skill_script_path(skill_name, script_name)`，返回 `scripts/{script_name}` 的**绝对路径**，供 Agent 配合 `run_shell_command` 执行（如比对、格式校验脚本）。
- **list_skill_assets(skill_name: str)**（可选）：调用 `SkillsManager().list_skill_assets(skill_name)`，返回该技能下 references/、scripts/、assets/ 中的相对路径列表，便于 Agent 发现可用模板与脚本。

注册方式与现有 `register_tool.py` 一致，使用 `@tool_manager.register`，并将上述工具名加入 `tools_list`。

## 4. Agent 逻辑（预期）

- 用户提出要求时，Agent 先调用 `search_skills` 获取候选技能元数据，再对选中的 name 调用 `load_skill` 得到完整 SOP；若无合适技能则自行规划。得到 SOP 后按 SOP 执行。
- 当需要**符合某文档规范**时，可调用 `load_skill_asset(skill_name, "references/SPEC.md")` 等加载模板或规范正文。
- 当需要**执行技能内置脚本**（如两文件 1:1 比对、格式校验）时，可先调用 `list_skill_assets(skill_name)` 查看有哪些脚本，再调用 `get_skill_script_path(skill_name, "compare.py")` 取得绝对路径，最后通过 `run_shell_command` 执行（如 `python <path> file1 file2`）。决策由模型根据 system prompt 与工具描述完成。

## 5. 错误与边界

- 技能根目录不存在：`list_skills` / `search_skills` 返回空列表；`get_skill_content` 返回「未找到技能」类提示。
- 某子目录无 `SKILL.md` 或 frontmatter 缺少 name/description：该目录不参与 list/search；若仅用于 load_skill 且按目录名匹配到，可尝试读取 SKILL.md，若解析失败则返回错误信息。
- **路径安全**：`get_skill_asset` / `get_skill_script_path` 必须将请求路径限制在技能目录内，禁止 `..` 及绝对路径；仅允许 `references/`、`assets/`、`scripts/` 下的相对路径。解析后若真实路径不在技能根下，返回错误。
- 可选：首次使用或启动时创建 `skills_root` 并写入 README，说明此处按 [Agent Skills](https://agentskills.io/specification) 规范放置技能目录及 SKILL.md。

## 6. 测试与文档

- 单元测试：SkillsManager 的 list_skills、get_skill_content、search_skills；**get_skill_asset**（合法路径、越界/非法路径）、**get_skill_script_path**（存在/不存在）、**list_skill_assets**；工具层可测 load_skill、search_skills、load_skill_asset、get_skill_script_path、list_skill_assets 的入参出参。
- 文档：说明技能根目录位置、目录结构（SKILL.md + references/、scripts/、assets/）、两个新工具的用途（加载模板/规范、获取脚本路径并配合 run_shell_command），并引用 [Agent Skills 规范](https://agentskills.io/specification)。

---

设计确认后，实现计划将按「目录 + SKILL.md + 必填 frontmatter」重写并执行。
