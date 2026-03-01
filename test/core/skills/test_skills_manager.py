import os
import sys
import pytest
from pathlib import Path

# 先导入包以加载子模块，否则 sys.modules 中尚无 skills_manager 模块
import backend.core.skills  # noqa: F401
# 包内还导出了 skills_manager 实例，patch 须作用在定义 _get_document_root 的模块上
_skills_module = sys.modules["backend.core.skills.skillsmanager"]
from backend.core.skills.skillsmanager import SkillsManager


def test_skills_root_uses_document_root():
    mgr = SkillsManager()
    from backend.infra.config import DOCUMENT_ROOT
    expected = Path(DOCUMENT_ROOT) / "skills"
    assert mgr.skills_root == expected


def test_list_skills_empty_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    mgr = SkillsManager()
    assert mgr.list_skills() == []


def test_list_skills_returns_dir_names_with_skill_md(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "data-analysis").mkdir()
    (tmp_path / "skills" / "data-analysis" / "SKILL.md").write_text("---\nname: data-analysis\ndescription: 数据分析\n---\n# Body")
    (tmp_path / "skills" / "code-review").mkdir()
    (tmp_path / "skills" / "code-review" / "SKILL.md").write_text("---\nname: code-review\ndescription: 代码审查\n---\n# Body")
    (tmp_path / "skills" / "empty-dir").mkdir()
    mgr = SkillsManager()
    assert set(mgr.list_skills()) == {"data-analysis", "code-review"}


def test_get_skill_content_exact_match(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "hello").mkdir()
    (tmp_path / "skills" / "hello" / "SKILL.md").write_text("---\nname: hello\ndescription: Hi\n---\ncontent here")
    mgr = SkillsManager()
    assert "content here" in mgr.get_skill_content("hello")
    assert "name: hello" in mgr.get_skill_content("hello")


def test_get_skill_content_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "pdf-processing").mkdir()
    (tmp_path / "skills" / "pdf-processing" / "SKILL.md").write_text("---\nname: pdf-processing\ndescription: PDF\n---\ncontent")
    mgr = SkillsManager()
    assert "content" in mgr.get_skill_content("PDF-Processing")


def test_get_skill_content_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    mgr = SkillsManager()
    out = mgr.get_skill_content("nonexistent")
    assert "未找到" in out or "not found" in out.lower()


def test_search_skills_returns_name_and_description(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "data-analysis").mkdir()
    content = "---\nname: data-analysis\ndescription: Data analysis and visualization.\n---\n# Data"
    (tmp_path / "skills" / "data-analysis" / "SKILL.md").write_text(content, encoding="utf-8")
    mgr = SkillsManager()
    results = mgr.search_skills("analysis", n=5)
    assert len(results) >= 1
    assert results[0]["name"] == "data-analysis"
    assert "analysis" in results[0]["description"]


def test_search_skills_respects_n(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills").mkdir()
    for i in range(5):
        (tmp_path / "skills" / f"skill-{i}").mkdir()
        (tmp_path / "skills" / f"skill-{i}" / "SKILL.md").write_text(
            f"---\nname: skill-{i}\ndescription: Skill number {i}\n---\n# S{i}"
        )
    mgr = SkillsManager()
    results = mgr.search_skills("skill", n=2)
    assert len(results) == 2


def test_get_skill_asset_returns_content(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "doc-spec").mkdir(parents=True)
    (tmp_path / "skills" / "doc-spec" / "SKILL.md").write_text("---\nname: doc-spec\ndescription: doc spec\n---\n# Spec")
    (tmp_path / "skills" / "doc-spec" / "references").mkdir()
    (tmp_path / "skills" / "doc-spec" / "references" / "SPEC.md").write_text("# Output must follow this spec")
    mgr = SkillsManager()
    assert "follow this spec" in mgr.get_skill_asset("doc-spec", "references/SPEC.md")


def test_get_skill_asset_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "x").mkdir(parents=True)
    (tmp_path / "skills" / "x" / "SKILL.md").write_text("---\nname: x\ndescription: x\n---\n")
    mgr = SkillsManager()
    out = mgr.get_skill_asset("x", "../x/references/SPEC.md")
    assert "not found" in out.lower() or "invalid" in out.lower() or "未找到" in out or "不允许" in out


def test_get_skill_script_path_returns_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "file-diff").mkdir(parents=True)
    (tmp_path / "skills" / "file-diff" / "SKILL.md").write_text("---\nname: file-diff\ndescription: 文件比对\n---\n")
    (tmp_path / "skills" / "file-diff" / "scripts").mkdir()
    (tmp_path / "skills" / "file-diff" / "scripts" / "compare.py").write_text("# compare")
    mgr = SkillsManager()
    path = mgr.get_skill_script_path("file-diff", "compare.py")
    assert path.endswith("scripts" + os.sep + "compare.py") or "compare.py" in path
    assert Path(path).exists()


def test_get_skill_script_path_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "x").mkdir(parents=True)
    (tmp_path / "skills" / "x" / "SKILL.md").write_text("---\nname: x\ndescription: x\n---\n")
    mgr = SkillsManager()
    out = mgr.get_skill_script_path("x", "nonexistent.py")
    assert "not found" in out.lower() or "未找到" in out


def test_list_skill_assets_returns_relative_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(_skills_module, "_get_document_root", lambda: tmp_path)
    (tmp_path / "skills" / "full").mkdir(parents=True)
    (tmp_path / "skills" / "full" / "SKILL.md").write_text("---\nname: full\ndescription: full\n---\n")
    (tmp_path / "skills" / "full" / "references").mkdir(parents=True)
    (tmp_path / "skills" / "full" / "references" / "R.md").write_text("")
    (tmp_path / "skills" / "full" / "scripts").mkdir(parents=True)
    (tmp_path / "skills" / "full" / "scripts" / "run.py").write_text("")
    mgr = SkillsManager()
    paths = mgr.list_skill_assets("full")
    assert "references/R.md" in paths or any("R.md" in p for p in paths)
    assert "scripts/run.py" in paths or any("run.py" in p for p in paths)
