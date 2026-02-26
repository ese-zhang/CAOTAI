import json
from backend.infra.fileio import save_messages
from .memory import agent_memory


def request_display_action_and_save(
    client, # 模型客户端
    session_path, # 对话历史文件路径
    model_settings, # 模型设置
    **kwargs # 其他参数
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
        ::param session_path: 对话历史文件路径
        ::param model_settings: 模型设置
        ::param kwargs: 其他参数, 必须符合client的参数要求
    """
    # 0. 初始化
    assistant_message = agent_memory.start_stream(session_path)
    messages = agent_memory.read_messages(session_path)
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
    for chunk in stream:
        delta = chunk.choices[0].delta
        if not delta:
            continue
        # 接收思考内容
        if delta.reasoning_content:
            reasoning_content += delta.reasoning_content
            agent_memory.append_reasoning(
                session_path,
                delta.reasoning_content
                )

        # 接收工具请求
        if delta.tool_calls:
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
            content += delta.content
            agent_memory.append_content(
                session_path,
                delta.content
                )
    # 将思考、工具请求、内容，写入对话历史
    final_tool_calls = [
        tool_calls_collector[i]
        for i in sorted(tool_calls_collector.keys())
        ]

    agent_memory.end_stream(
        session_path,
        tool_calls=final_tool_calls if final_tool_calls else None
        )

    # 构造要存入 json 的 message
    if len(final_tool_calls)>0:
        is_final_answer=False
        # 3. 执行工具 Action and Observe
        tool_registry = model_settings.get("tool_registry", {})

        for tool_call in tool_calls_collector.values():
            tool_name = tool_call["function"]["name"]
            raw_args = tool_call["function"]["arguments"]

            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError as e:
                tool_result = f"[tool args parse error] {e}"
            else:
                tool_fn = tool_registry.get(tool_name)
                if tool_fn is None:
                    tool_result = f"[unknown tool] {tool_name}"
                else:
                    try:
                        tool_result = tool_fn(**args)
                    except Exception as e:
                        tool_result = f"[tool execution error] {e}"

            new_message=dict({"role": "tool",
                              "content": tool_result,
                              "tool_call_id": tool_call["id"]})
            agent_memory.append_message(
                session_path,new_message
                )
    else:
        is_final_answer=True

    # 4. 保存对话历史 Save
    save_messages(
        agent_memory.read_messages(session_path),
        session_path
        )
    return is_final_answer