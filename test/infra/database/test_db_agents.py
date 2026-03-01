import pytest
from unittest.mock import patch
from backend.infra.database import db

def test_agents_table_exists_and_can_insert():
    db.upsert_agent("TestAgent", role_settings_yaml="description: test\n", system_prompt_text="You are test.")
    row = db.get_agent("TestAgent")
    assert row is not None
    assert row["agent_name"] == "TestAgent"
    assert "description: test" in (row["role_settings_yaml"] or "")
    assert row["system_prompt_text"] == "You are test."


def test_create_session_for_agent_and_get_agent_name():
    db.upsert_agent("A1", role_settings_yaml="", system_prompt_text="")
    db.create_session_for_agent("sess_1", "A1")
    name = db.get_session_agent_name("sess_1")
    assert name == "A1"


def test_create_session_appends_system_message():
    db.upsert_agent("A2", role_settings_yaml="", system_prompt_text="You are A2.")
    db.create_session_for_agent("sess_2", "A2")
    msgs = db.load_messages("sess_2")
    assert len(msgs) >= 1 and msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "You are A2."


def test_agent_run_does_not_double_append_system_when_session_exists():
    """Run with agent_name+session_id on an existing session must not add a second system message."""
    pytest.importorskip("openai")
    from backend.core.agent import basic_agent
    from backend.infra.predefined.llm_settings_property import LLMSettingsProperty

    db.upsert_agent("A2", role_settings_yaml="", system_prompt_text="You are A2.")
    db.clear_session("sess_run_2")  # ensure clean state (no leftover from previous runs)
    db.create_session_for_agent("sess_run_2", "A2")
    system_count_before = sum(1 for m in db.load_messages("sess_run_2") if m["role"] == "system")
    assert system_count_before == 1

    agent = basic_agent(
        name="A2",
        description="",
        skills=[],
        rules=[],
        soul="",
        tools=[],
        llm_settings=LLMSettingsProperty(model="test", api_key="sk-test"),
    )
    with patch("backend.core.agent.request_display_action_and_save", return_value=True):
        agent.run({"agent_name": "A2", "session_id": "sess_run_2", "text": "hi"})

    msgs = db.load_messages("sess_run_2")
    system_count_after = sum(1 for m in msgs if m["role"] == "system")
    assert system_count_after == 1, "run() must not append system when session already has one"


def test_basic_agent_from_agent_name():
    pytest.importorskip("openai")
    from backend.core.agent import basic_agent
    from backend.infra.database import db
    db.upsert_agent("FromDB", role_settings_yaml="souls: x\nrules: []\ntools: []", system_prompt_text="You are FromDB.")
    agent = basic_agent.from_agent_name("FromDB")
    assert agent.name == "FromDB"
    assert "You are FromDB" in agent.prompt_builder()["content"]  # or check system_prompt is used


def test_delete_agent_cascades_sessions_and_messages():
    db.upsert_agent("DelAgent", role_settings_yaml="", system_prompt_text="")
    db.create_session_for_agent("del_sess", "DelAgent")
    db.append_message("del_sess", {"role": "user", "content": "x"})
    db.delete_agent("DelAgent")
    assert db.get_agent("DelAgent") is None
    assert db.get_session_agent_name("del_sess") is None
    assert len(db.load_messages("del_sess")) == 0
