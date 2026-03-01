# Skills 系统使用说明

## 技能根目录

技能根目录为 **`DOCUMENT_ROOT/skills`**，与 chat_history 同根。`DOCUMENT_ROOT` 由 `backend.infra.config` 提供（通常来自 `config/settings.yaml` 的 `document_root`）。

## 技能目录结构（Agent Skills 规范）

每个技能是一个**子目录**，目录内**必须**包含 `SKILL.md`。可选子目录：

- **references/**：规范、参考文档（如 `REFERENCE.md`、`FORMS.md`）
- **scripts/**：可执行脚本（如 Python 比对脚本、格式校验脚本）
- **assets/**：模板、静态资源

规范参考：[Agent Skills Specification](https://agentskills.io/specification)

示例：

```
skills/
  data-analysis/
    SKILL.md          # 必需，含 YAML frontmatter（name、description）
    references/
      SPEC.md
    scripts/
      validate.py
  file-diff/
    SKILL.md
    scripts/
      compare.py
```

## SKILL.md 格式

- 必须包含 **YAML frontmatter**，且 **name**、**description** 为必填。
- `name` 须与目录名一致（小写、数字、连字符）。
- 正文为 Markdown，描述技能步骤与用法。

## Agent 可用工具

| 工具 | 用途 |
|------|------|
| **search_skills(query, n)** | 按关键词搜索技能，返回前 n 条 name 与 description。 |
| **load_skill(skill_name)** | 按名称加载技能全文（SKILL.md 内容），获取 SOP。 |
| **load_skill_asset(skill_name, relative_path)** | 加载技能内某文件的文本内容，如 `references/SPEC.md`，用于规范或模板。 |
| **list_skill_assets(skill_name)** | 列出该技能下 references/、scripts/、assets/ 中的相对路径。 |
| **get_skill_script_path(skill_name, script_name)** | 返回 `scripts/{script_name}` 的绝对路径，供 `run_shell_command` 执行（如文件 1:1 比对、格式校验）。 |

## 典型流程

1. 用户提出需求 → 调用 **search_skills** 得到候选技能。
2. 对选中技能调用 **load_skill** 获取完整 SOP，按 SOP 执行。
3. 需要符合某文档规范时 → **load_skill_asset(skill_name, "references/SPEC.md")** 加载规范内容。
4. 需要执行技能内置脚本时 → **list_skill_assets(skill_name)** 查看脚本名，再 **get_skill_script_path(skill_name, "compare.py")** 取得路径，最后 **run_shell_command** 执行（如 `python <path> file1 file2`）。
