# 🧩 核心技能：认知上下文调度 (Cognitive Context Dispatcher)

**描述：** 模仿人类大脑的“阿特金森-谢夫林触发模型”，通过动态权重计算，使 AI 能够根据对话的**频率**和**近因**自动唤起相关记忆，同时保留“主动回想”（工具搜索）的能力，以解决长文本窗口下的注意力稀释问题。



### 💡 运作逻辑 (Heuristics)
1.  **自动唤起（隐式）：** 每一轮对话前，系统自动扫描存储。高频提及（Frequency）或近期发生（Recency）的片段，其激活值（Activation Score）若超过阈值，直接进入 `System Prompt` 的“潜意识区”。
2.  **主动回想（显式）：** 当现有上下文不足以回答时，AI 意识到信息缺失，主动调用 `search_memory` 工具进行全量检索。
3.  **动态衰减：** 记忆遵循遗忘曲线。未被再次激活的记忆权重随时间对数下降，确保上下文空间始终被“最有价值”的信息占据。

### 🧠 激活权重公式 (Activation Formula)
$$A_i = \ln \left( \sum_{j=1}^{n} t_j^{-d} \right) + \text{Similarity}(q, m_i)$$
其中 $A_i$ 是记忆 $i$ 的激活度，$t_j$ 是自第 $j$ 次记忆触发以来经过的时间，$d$ 是衰减因子。

---

```yaml
# ===============================
# Issue Metadata
# ===============================

issue:
  id: TASK-MEM-001
  module: message_io
  type: implementation
  version: 1.0
  title: "实现基于人类记忆规律的上下文动态加载机制"

# ===============================
# Execution Context (World Model)
# ===============================

context:
  repository:
    root: backend/
    target_files:
      - backend/memory/engine.py
      - backend/message_io.py

  dependencies:
    functions:
      - name: fetch_high_activation_memories
        signature: fetch_high_activation_memories(user_id: str, top_n: int) -> List[Dict]
      - name: update_memory_heat
        signature: update_memory_heat(memory_ids: List[str]) -> None

  semantics:
    fetch_high_activation_memories:
      behavior: selective_read
      logic: "Select memories where activation_score > threshold ORDER BY activation_score DESC"
    update_memory_heat:
      behavior: atomic_increment
      consistency: synchronous

# ===============================
# Interface Contract
# ===============================

interfaces:
  public_methods:
    - name: compose_final_payload
      inputs:
        user_query: str
        session_id: str
      outputs:
        payload: Dict  # 格式: [激活记忆] + [System(Skills+Tools)] + [历史消息]

    - name: memory_search_tool
      inputs:
        query: str
      outputs:
        search_results: List[str]

  invariants:
    - total_token_count_under_threshold
    - system_prompt_must_contain_search_tool_definition
    - memory_activation_score_must_decay_over_time

# ===============================
# Workflow / Control Flow
# ===============================

workflow:
  model: state_machine
  states:
    - IDLE
    - FETCHING_AUTO_MEMORY   # 隐式加载：提取“潜意识”
    - CONSTRUCTING_PROMPT    # 组装：拼接 System 与激活记忆
    - INFERENCE              # 推理：AI 决定是否进行“显式搜索”

  transitions:
    - name: on_receive_query
      from: IDLE
      to: FETCHING_AUTO_MEMORY

    - name: on_memory_ready
      from: FETCHING_AUTO_MEMORY
      to: CONSTRUCTING_PROMPT

# ===============================
# Requirements & Constraints
# ===============================

requirements:
  must:
    - "支持按激活次数（Hits）和时间戳（Timestamp）计算综合权重"
    - "在 System Prompt 顶部为自动激活的记忆预留专门的 Context 区块"
    - "显式暴露 search_memory 工具，允许 AI 在自动记忆不足时主动检索"

  must_not:
    - "禁止全量加载原始历史记录，必须通过激活权重或工具过滤"
    - "计算激活分数的过程不得阻塞 IO 主进程"

# ===============================
# Definition of Done (Machine-checkable)
# ===============================

acceptance:
  tests:
    - memory_engine_test.py::test_activation_decay
    - memory_engine_test.py::test_payload_structure

  invariants:
    - invariant(no_memory_leak_between_sessions)
    - invariant(search_tool_invocable_when_context_missing)