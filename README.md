# 草台班子（CAOTAI）

> 承认 AI 不可靠，并据此设计的软件工程体系  
> A software engineering framework built on the assumption that AI is *not* reliable

---

## 中文版

### 草台班子是什么？

**草台班子（CAOTAI）不是一个“让 AI 自动写代码”的项目。**  
它的核心理念恰恰相反：

> **AI 是不可靠的执行者，人类才是设计者。**

CAOTAI 试图解决的问题不是“AI 能不能写代码”，  
而是：

> **在 AI 不可靠的前提下，如何把它安全、可复现、可审计地纳入软件工程流程。**

---

### 名字的含义

**CAOTAI** 的英文全称是：

> **Collaborative Agent Orchestration Task Automation Integration**

这个名字背后隐含着一个并不浪漫、但更接近现实的判断：

> **世界本身就是由“草台班子”构成的。**  
> 执行者不完美、信息不完整、判断常常出错。

CAOTAI 并不试图否认这一点，而是正面接受它。

正如俗语所说：

> **三个臭皮匠，顶个诸葛亮。**

CAOTAI 认为，这并不是因为个体突然变聪明了，而是因为：

> **在合适的管理、约束和裁决机制下，  
> 多个不可靠的执行者，可以产生可靠的结果。**

---

### 核心理念

CAOTAI 的设计遵循几条朴素、但常被忽略的工程事实：

1. **设计不可外包**  
   架构、接口、不变量、世界模型，必须由人类冻结。

2. **执行可以外包**  
   当设计被严格约束后，AI 非常适合做“填空题式”的实现。

3. **判断不能交给 AI**  
   完成与否必须由机器可判定的测试与规则决定，而不是“看起来差不多”。

4. **失败是系统的一部分**  
   系统必须假设失败会发生，并能回滚、重试、升级。

---

### 协作，而不是智能

CAOTAI 不依赖单个“最聪明”的 Agent。

它假设：

- 每个 Agent 都有盲区
- 每个 Agent 都可能犯错
- 有些 Agent 必须是对抗性的（测试、审查、反驳）

**正确性并非来自智能，而是来自结构化的不一致。**

---

### 编排，而不是放任

没有编排的协作只会产生噪声。

在 CAOTAI 中：

- 每个 Agent 都有明确角色
- 输入、输出、接口被冻结
- 执行顺序由 DAG / 状态机决定
- 判断权始终在系统之外

**编排，是把混乱变成产出的关键。**

---

### CAOTAI 在做什么？

CAOTAI 构建的是一条 **受控的 AI 软件生产流水线**：

- 使用 YAML 作为中间表示（IR），冻结设计与接口
- 通过 Schema、Invariant、Workflow 明确边界
- 让 AI 只在“无设计自由度”的前提下写代码
- 用测试与规则裁决对错
- 在必要时，将问题升级给人类

在 CAOTAI 中：

- `issue.yaml` 不是需求描述，而是 **可执行契约**
- Agent 不是智能体，而是 **不可信劳动力**
- 人类不是 reviewer，而是 **系统设计者**

---

### 适合谁？

CAOTAI 并不适合：

- 想“一句话生成整个项目”的人
- 把 AI 当作高级程序员的人

它适合：

- 把软件工程当工程的人
- 希望 AI **可控、可复现、可维护**地参与开发的人
- 愿意用结构和约束换取长期稳定性的人

---

## English Version

### What is CAOTAI?

**CAOTAI is not about letting AI write code autonomously.**  
Its core belief is the opposite:

> **AI is an unreliable executor; humans are the designers.**

CAOTAI is not asking whether AI *can* write code,  
but instead:

> **How can AI be integrated into software engineering safely, reproducibly, and audibly—given that it is unreliable?**

---

### About the Name

**CAOTAI** stands for:

> **Collaborative Agent Orchestration Task Automation Integration**

The name encodes a deliberately unromantic view of reality:

> **The world itself is a “grass-stage troupe”:  
> messy, inconsistent, and built from unreliable actors.**

Agents are not sages.  
They are partial, biased, and frequently wrong.

And yet:

> **With proper management, multiple flawed executors  
> can outperform a single “smart” one.**

This is not optimism.  
It is orchestration.

---

### Core Principles

CAOTAI is built on a few simple but often ignored truths:

1. **Design cannot be outsourced**  
   Architecture, interfaces, invariants, and world models must be frozen by humans.

2. **Execution can be outsourced**  
   Once constraints are strict enough, AI excels at implementation as a fill-in-the-blanks executor.

3. **Judgment must not belong to AI**  
   Completion is defined by machine-checkable tests and rules, not subjective assessment.

4. **Failure is part of the system**  
   The pipeline must assume failure, support rollback, and allow escalation.

---

### Collaboration over Intelligence

CAOTAI does not depend on a single all-knowing agent.

It assumes:
- Every agent has blind spots
- Every agent will make mistakes
- Some agents must be adversarial (tester, critic, reviewer)

Correctness emerges not from intelligence,  
but from **structured disagreement under constraints**.

---

### Orchestration over Autonomy

Without orchestration, collaboration degenerates into noise.

CAOTAI treats agents as engineering components:
- Clear roles
- Explicit inputs and outputs
- Frozen interfaces
- Ordered execution (DAGs, state machines)

Orchestration is what turns chaos into throughput.

---

### What Does CAOTAI Do?

CAOTAI builds a **controlled AI software production pipeline**:

- YAML-based intermediate representations (IR) to freeze design
- Explicit schemas, invariants, and workflows
- AI operates only where design freedom is eliminated
- Tests and rules act as final arbiters
- Human intervention is reserved for irreducible ambiguity

In CAOTAI:

- `issue.yaml` is not a task description, but an **executable contract**
- Agents are not “intelligent beings”, but **untrusted labor**
- Humans are not reviewers, but **system architects**

---

### Who Is This For?

CAOTAI is **not** for people who:
- Want one-prompt full-project generation
- Treat AI as a senior engineer

CAOTAI *is* for people who:
- Treat software engineering as engineering
- Want AI to be **controllable, reproducible, and maintainable**
- Prefer structure and constraints over fragile automation

---

## Status

CAOTAI is an ongoing experiment.  
It is opinionated, strict, and intentionally conservative.

If you believe AI should be powerful,  
CAOTAI believes **power must come after control**.