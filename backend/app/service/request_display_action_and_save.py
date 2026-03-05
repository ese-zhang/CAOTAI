import json
from pathlib import Path
from typing import Callable, Optional

from backend.config import DOCUMENT_ROOT
from backend.infra.function_calling.context import ToolContext
from backend.infra.streambuffer import stream_buffer


def _tool_result_to_plain_text(value) -> str:
    """将 function calling 的返回值或错误统一转为纯文本，供模型观察。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def request_display_action_and_save(
    client,  # 模型客户端
    session_id,  # 对话历史文件路径
    model_settings,  # 模型设置
    token: Callable[[str], None],
    agent_context: Optional[dict] = None,  # workspace_root, allowed_tools, agent_id, skills_provider 等
    **kwargs
):
    """
        这个代码是模型一轮思考的基石
        在模型层面，会执行：思考、工具请求、观察结果；
        在代码层面，会进行：消息请求、工具请求执行、观察返回、结果持久化
        大致的逻辑是
        1. 从文件中读取对话历史
        2. 根据对话历史,请求模型进行思考和工具请求,并路由至UI进行展示
        3. 根据工具请求, 执行工具, 并在指定UI中进行展示
        4. 根据工具执行结果, 构建观察结果, 写入上下文
        5. 根据本轮数据，存储至对话历史文件中
        他不构成一个完整的对话, 而是一个完整的思考、执行、观察、保存的流程
        ::param client: 模型客户端
        ::param session_id: 对话历史文件路径
        ::param model_settings: 模型设置
        ::param kwargs: 其他参数, 必须符合client的参数要求
    """
    # 0. 初始化
    assistant_message = stream_buffer.start_stream(session_id)
    messages = stream_buffer.recall(session_id)
    # 1. 请求模型进行思考和工具请求 Request
    stream = client.chat.completions.create(
        model=model_settings["model"],
        messages=messages,
        tools=model_settings["tools"],
        stream=True,
        **kwargs
    )
    # 2. 收集思考、工具请求、内容，并展示 Display
    tool_calls_collector = {}
    reasoning_content = ""
    content = ""
    think_flag = 0
    for chunk in stream:
        delta = chunk.choices[0].delta
        if not delta:
            continue
        # 接收思考内容
        if delta.reasoning_content:
            reasoning_content += delta.reasoning_content
            stream_buffer.append_reasoning(
                session_id,
                delta.reasoning_content
                )
            if think_flag==0:
                token("<think>"+delta.reasoning_content)
                think_flag=1
            elif think_flag==1:
                token(delta.reasoning_content)

        # 接收工具请求
        if delta.tool_calls:
            if think_flag==1:
                token("</think>\n")
                think_flag=-1
            for tc_delta in delta.tool_calls:
                index = tc_delta.index
                if index not in tool_calls_collector:
                    tool_calls_collector[index] = {
                        "id": tc_delta.id,
                        "type": "function",
                        "function": {"name": tc_delta.function.name or "", "arguments": ""}
                    }
                if tc_delta.function.arguments:
                    tool_calls_collector[index]["function"]["arguments"] += tc_delta.function.arguments
        # 接收正文内容
        if delta.content:
            if think_flag == 1:
                token("</think>\n")
                think_flag = -1
            content += delta.content
            stream_buffer.append_content(
                session_id,
                delta.content
                )
            token(delta.content)
    # 将思考、工具请求、内容，写入对话历史
    final_tool_calls = [
        tool_calls_collector[i]
        for i in sorted(tool_calls_collector.keys())
        ]

    stream_buffer.end_stream(
        session_id,
        tool_calls=final_tool_calls if final_tool_calls else None
        )

    # 构造要存入 json 的 message
    if len(final_tool_calls) > 0:
        is_final_answer = False
        # 3. 执行工具 Action and Observe（带上下文与权限）
        tool_registry = model_settings.get("tool_registry", {})
        allowed_tools = None
        if agent_context:
            allowed_tools = agent_context.get("allowed_tools")
            if allowed_tools is not None:
                allowed_tools = set(allowed_tools)
        if allowed_tools is None:
            allowed_tools = set(tool_registry.keys())

        workspace_root = None
        if agent_context and agent_context.get("workspace_root") is not None:
            workspace_root = Path(agent_context["workspace_root"])
        if workspace_root is None:
            workspace_root = Path(DOCUMENT_ROOT)

        ctx = ToolContext(
            workspace_root=workspace_root,
            agent_id=agent_context.get("agent_id", "") if agent_context else "",
            session_id=session_id,
            skills_provider=agent_context.get("skills_provider") if agent_context else None,
        )

        for tool_call in tool_calls_collector.values():
            tool_name = tool_call["function"]["name"]
            raw_args = tool_call["function"]["arguments"]

            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError as e:
                tool_result = f"[tool args parse error] {str(e)}"
            else:
                if tool_name not in allowed_tools:
                    tool_result = f"[Permission denied: tool '{tool_name}' is not allowed for this agent.]"
                else:
                    tool_fn = tool_registry.get(tool_name)
                    if tool_fn is None:
                        tool_result = f"[unknown tool] {tool_name}"
                    else:
                        try:
                            tool_result = tool_fn(ctx, **args)
                        except PermissionError as e:
                            tool_result = f"[Permission denied] {e}"
                        except Exception as e:
                            tool_result = f"[tool execution error] {str(e)}"
            tool_result = _tool_result_to_plain_text(tool_result)
            new_message = {
                "role": "tool",
                "content": tool_result,
                "tool_call_id": tool_call["id"],
            }
            token(tool_result)
            stream_buffer.append_message(
                session_id,new_message
                )
            #print(db.load_messages(session_id)[-1])
    else:
        is_final_answer=True
    token("\n")
    return is_final_answer