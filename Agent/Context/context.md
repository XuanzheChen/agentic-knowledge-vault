# Context

[[Agent|返回上级：Agent]] · [[main|返回知识主干]] · [[Agent框架|Agent 框架]]

围绕现代 Agentic Context 的来源、生命周期、治理策略与框架实现整理。这里的 Context 不等同于 Chat History，也不等同于 Memory 或 RAG；更准确地说，它是**某一次模型调用真正可见的工作集（working set）**，由 Runtime 从更大的 Agent State、Memory、知识库、工具、文件系统和运行环境中动态构造。

## 子树

| 子树 | 内容 |
| --- | --- |
| [[Memory]] | 长期记忆的形成、检索、更新、聚合与遗忘 |
| [[RAG]] | 外部知识的组织、索引、检索、重排与增强生成 |

## 问题目录

- [[context#现代 Agentic Context 应如何理解？|现代 Agentic Context 应如何理解？]]
- [[context#Agent 的 Context 有哪些来源？|Agent 的 Context 有哪些来源？]]
- [[context#现代 Agent 应如何治理 Context？|现代 Agent 应如何治理 Context？]]
- [[context#LangChain 如何设计 Context Engineering？|LangChain 如何设计 Context Engineering？]]
- [[context#Deep Agents 如何管理长时程 Context？|Deep Agents 如何管理长时程 Context？]]

---

## 现代 Agentic Context 应如何理解？

### Context 是一次模型调用的“工作集”，不是系统拥有的全部信息

Anthropic 将上下文工程定义为：在推理阶段，从不断变化的候选信息中策划和维护最合适的一组 tokens，使模型更可能产生期望行为。核心目标不是尽量填满 Context Window，而是找到**尽可能小、但信号密度足够高的 token 集合**。随着 Agent 在循环中不断产生工具结果、中间状态和历史消息，这个集合需要在每次模型调用前持续更新，而不是一次性构造后永久不变。

参考：[Anthropic - Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

可以先区分四个容易混淆的概念：

| 概念 | 更准确的含义 | 是否一定进入当前 LLM Context |
| --- | --- | --- |
| **Context** | 某一次模型调用真正可见的 instructions、messages、tools、evidence 等工作集 | 是 |
| **State** | 当前任务运行过程中持续演化的结构化状态，如消息、计划、工具结果、flags | 否，只在需要时投影进 Context |
| **Memory / Store** | 跨轮次或跨会话保存的用户偏好、事实、经验和历史 | 否，是候选 Context 来源 |
| **RAG / Retrieval** | 从外部知识空间寻找与当前任务相关信息的机制 | 否，检索结果经过筛选后才进入 Context |

因此，一个现代 Agent 更合理的结构不是：

```text
Context = Chat History + Memory + RAG
```

而是：

```text
              更大的 Context Universe

 Instructions / Policies        Conversation / Task State
 Memory / User Profile          RAG / External Knowledge
 Files / Artifacts              Tools / Tool Results
 Skills / Examples              Runtime Metadata
             \                     /
              \                   /
               ── Context Runtime ──
                        ↓
               当前 LLM Working Set
                        ↓
                    Model Call
                        ↓
             Action / New Observation
                        ↓
           更新 State / Files / Memory
                        ↓
                 下一轮重新构造
```

这也是上下文工程和传统 Prompt Engineering 的主要区别：Prompt Engineering 主要研究“指令怎么写”；Context Engineering 研究的是**Agent Loop 每一轮中，哪些信息应该存在、何时进入、以什么形式进入、何时被移出以及如何在窗口之外继续保存。**

### Context Window 是容量上限，不是建议使用量

大 Context Window 并不意味着应该把所有信息都放进去。Anthropic 将 Context 视为有限的 attention budget：随着 token 数量增加，相关信息会受到重复、陈旧和无关内容的干扰，模型的长程检索和推理精度可能逐渐下降，即所谓 Context Rot。因此治理目标更接近：

> **最大化 Context Utility / Signal Density，而不是最大化 Context Utilization。**

这意味着即使模型仍剩下大量可用 token，也没有必要主动填满。

---

## Agent 的 Context 有哪些来源？

从工程上看，可以把候选 Context 来源分成七类。它们的共同点是：**只有经过当前任务需要的筛选与装配后，才真正成为 Model Context。**

### 1. Instructions 与 Policies

包括 System Prompt、Developer Instructions、角色定义、业务规则、安全边界、输出要求等。这部分通常具有最高优先级，但也需要控制规模：过度把程序逻辑硬编码进 Prompt 会产生脆弱、难维护的长提示；过于抽象则无法给模型足够明确的行为信号。

工具描述和参数 schema 也属于这一类 Context，因为它们通常随每次模型调用一起暴露给模型。工具数量过多、功能重叠或描述模糊，会同时浪费 token 和增加 Tool Selection 的认知负担。Anthropic 因此强调最小、边界清晰、token-efficient 的工具集合。

参考：[Anthropic - Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)

### 2. User Input 与 Conversation History

包括当前用户请求、近期对话和必要的历史上下文。长对话中不应默认把全部 Message History 原样保留；较老消息可以被摘要、结构化提炼或转移到外部存储，只保留近期局部上下文和必要历史。

### 3. Task State / Agent State

包括当前目标、Plan、已完成步骤、待办、约束、权限状态、错误计数、当前 artifact 等。State 是 Runtime 的“真实状态”，而 Prompt 中的 Context 只是 State 的一个视图。例如 `retry_count` 可以由 Runtime 使用，但未必需要让模型看到；而当前 Plan 和未解决 Blocker 则可能需要注入 Model Context。

### 4. Memory / Store

包括用户偏好、长期事实、经验、跨会话历史等。Memory 的写入、冲突、遗忘等问题见 [[Memory]]。Context Engineering 主要关心的是**哪一条 Memory 在当前任务中值得被读取，并以多大粒度进入当前窗口**，而不是如何永久存储所有 Memory。

### 5. Retrieval / External Knowledge

包括 RAG、搜索引擎、数据库查询、API、企业知识库等。相关检索机制见 [[RAG]]。检索结果也不是越多越好：需要经过 filtering、reranking、deduplication、context compression 等步骤，最终只把高价值 Evidence 注入模型。

### 6. Workspace / Files / Artifacts

代码仓库、报告草稿、日志、中间数据、Note、搜索结果文件等可以作为 Context Window 之外的**外部工作记忆（external working memory）**。Agent 不需要一直“记住”文件内容，只需要知道文件路径、目录结构或轻量摘要，并在需要时通过 `grep`、`read_file`、数据库查询等方式重新加载。

### 7. Runtime Context 与 Environment

包括 user ID、权限、API key、数据库连接、部署环境、feature flags 等 Runtime dependency。这里要特别注意术语：**Runtime Context 不等于 LLM Context。** 例如 LangChain 中的 `runtime.context` 可以被 Tool 和 Middleware 读取，但不会自动暴露给模型；只有当代码根据它生成 Prompt、选择 Tool 或读取数据时，它才间接影响 Model Context。

LangChain 官方把 Context 按可变性和生命周期进一步区分为 static runtime context、dynamic runtime state 与 cross-conversation store，这个区分很适合避免把“模型看到的信息”和“Agent Runtime 拥有的信息”混为一谈。

参考：[LangChain - Context overview](https://docs.langchain.com/oss/python/concepts/context)

---

## 现代 Agent 应如何治理 Context？

相比把 JIT、压缩、Subagent 等技巧简单并列，更完整的工程模型是把 Context 看成一个循环生命周期：

```text
Context Sources
      ↓
1. Acquisition / Retrieval
      ↓
2. Selection / Prioritization / Budgeting
      ↓
3. Structuring / Assembly
      ↓
4. Compression / Offloading
      ↓
5. Isolation / Scoping
      ↓
        Model Call
      ↓
    Tool / Action
      ↓
6. Persistence / Update / Eviction
      ↓
7. Observability / Evaluation
      └────────────→ 下一轮 Context
```

### 1. Acquisition：Preload、JIT 与 Progressive Disclosure

第一步不是决定怎么压缩，而是决定**信息何时进入候选工作集**。

- **Preload**：始终把小量、稳定且高价值的信息提前放入上下文，例如项目级规范、关键用户要求和当前 Task。
- **Just-in-Time Retrieval（JIT）**：只保留文件路径、URL、查询、索引等轻量引用，Agent 在真正需要时再通过 Tool 读取具体内容。
- **Progressive Disclosure**：不是一次把资源全部展开，而是从目录、摘要、metadata 等粗粒度信息开始，逐层读取更细内容；每一次 Observation 再决定下一次获取什么。
- **Hybrid Strategy**：现实中通常不是 Preload 和 JIT 二选一，而是“少量高价值信息预加载 + 其余按需探索”。

Anthropic 将 JIT Context 与 Progressive Disclosure 视为 Agentic Search 的重要方向。例如 Coding Agent 可以始终加载项目规范，但只在需要时 `grep` 和读取具体文件。

### 2. Selection / Prioritization / Budgeting：从候选信息中选什么

Context Window 是预算，因此选择策略需要同时考虑“价值”和“成本”。比单纯 `relevance + recency` 更成熟的候选特征通常包括：

- **Priority / Mandatory**：安全规则、用户当前任务和硬约束是否必须存在；
- **Relevance**：是否直接帮助当前决策；
- **Recency / Freshness**：是否仍然有效；
- **Authority / Reliability**：来源可信度与事实等级；
- **Task dependency**：当前步骤是否依赖它；
- **Novelty / Redundancy**：是否只是重复已有信息；
- **Token utility**：单位 token 带来的信息价值；
- **Diversity / Coverage**：Evidence 是否覆盖多个必要角度。

因此 Context Selection 可以看成一个 budgeted optimization 问题，而不是“检索 Top-K 后全部塞入 Prompt”。工具 schema、Few-shot 和固定 Prompt 同样消耗这个预算。

### 3. Structuring / Assembly：把不同角色的信息组织清楚

被选中的信息不能无差别拼接。更好的做法是明确其语义角色，例如：

```text
[Role / Policies]
[Current Task]
[Task State / Plan]
[Evidence / Sources]
[Relevant Memory]
[Available Tools]
[Recent Interaction]
[Output Contract]
```

结构化的目的不是追求某种固定 Markdown/XML 模板，而是减少语义歧义：模型应该能区分“规则”“用户事实”“外部证据”“旧历史”和“当前任务”。同时应保留必要 provenance，避免不同来源的事实在 Context 中失去出处后被模型当成同等可信的信息。

工程上还应考虑 stable prefix / prompt caching：稳定的系统说明和工具定义尽量保持稳定，而动态 Evidence 放在适合变化的位置，从而兼顾缓存与运行时适配。

### 4. Compression / Offloading：缩小 active working set

长时程 Agent 必须把大量历史移出 Model Context。常见方式不是单一“摘要”，而是几类不同操作：

- **Truncation**：删除明确低价值或可重取的数据，最便宜但最容易丢信息；
- **Summarization / Compaction**：把老历史压缩成目标、关键决策、已完成事项、未解决问题和下一步等结构化摘要；
- **Extraction**：不是总结全文，而是提取 Plan、Decision、Entity、Constraint、Citation 等结构化状态；
- **Offloading**：把大型 Tool Result、文件内容或日志写入 Filesystem / Object Store，只在 Context 中保留 path、preview、hash 或摘要；
- **Reversible compression**：优先保留能够重新访问原始信息的引用，而不是只留下不可逆摘要。

Anthropic 对长时程任务特别强调 Compaction 与 Structured Note-taking。核心原则是：**压缩可以有损，但关键事实必须能够保留或重新取回。**

### 5. Isolation / Scoping / Delegation：不是所有信息都应该让主 Agent 看

Context Isolation 的目的不是简单增加 Agent 数量，而是防止局部、高噪声任务污染主 Context：

```text
Main Agent
   ↓ delegate
Subagent：独立 fresh context
   ↓ 多轮搜索 / 工具调用 / 大量中间结果
Concise Result / Artifact
   ↓
Main Agent
```

Subagent 因此同时承担**任务分工**和**Context Quarantine**。还可以进一步缩小每个 Agent 的 Tool Set、Skill、Memory namespace 和文件访问范围，使不同角色只拥有完成局部任务所需的信息与能力。

但隔离也会损失信息：主 Agent 只看到 Subagent 输出时，局部推理过程和 Evidence 可能被过度压缩。因此高价值结果应通过 citation、artifact 或文件引用保留可追溯性，而不是只返回一句结论。

### 6. Persistence / Update / Eviction：决定哪些信息离开 Context 后仍值得存在

一次 Model Call 之后会产生新的 Observation、Tool Result、Decision 和 Artifact。它们不应该全部永久追加到消息历史，而应根据类型写回不同层：

```text
短期任务状态      → State / Checkpoint
大段工作产物      → Files / Artifacts
项目进度与决策    → Structured Notes
用户长期偏好      → Memory / Store
外部事实           → RAG source / cache（必要时）
临时 Tool Noise    → discard
```

这一步把 Context Engineering 与 [[Memory]] 的 Write Policy 联系起来：上下文治理不仅有“读什么”，也有“执行后把什么留下”。同时需要 deduplication、conflict resolution、freshness、TTL / eviction 等机制，避免未来检索持续召回过时或冲突信息。

### 7. Observability / Evaluation：必须能够检查“模型当时到底看到了什么”

Agent 调试不能只看最终答案。Context Engineering 至少需要记录：

- 最终 Model Context 的组成和 token 分布；
- 每段 Context 的来源与选择原因；
- 哪些候选被裁剪、摘要或 offload；
- Retrieval / Rerank 结果；
- Tool schema 和 Tool Result 的 token 成本；
- Compaction 前后关键信息是否仍可恢复；
- Subagent 返回内容是否保留关键 Evidence。

典型评估指标可以包括 retrieval recall、context precision、compression recall、tool-selection accuracy、context token cost，以及任务成功率对 Context Policy 的敏感性。也就是说，Context Policy 应通过 eval 驱动迭代，而不是只凭 Prompt 直觉调参。

### 与 HelloAgents GSSC 的关系

HelloAgents 第 9 章的 `Gather → Select → Structure → Compress` 是很好的教学骨架，它主要覆盖上面生命周期中的**候选汇聚、选择、装配和压缩**。现代长时程 Agent 还需要显式补上 JIT Acquisition、Filesystem / Note Offloading、Subagent Isolation、State / Memory Write-back 以及 Observability，因此 Context Engineering 更适合理解成一个 Runtime lifecycle，而不只是一个 Prompt Builder。

---

## LangChain 如何设计 Context Engineering？

> 框架定位与 LangGraph / Deep Agents 的层级关系见 [[Agent框架#LangChain 在 Agent 开发中解决什么问题？|LangChain 在 Agent 开发中解决什么问题？]]。

LangChain 的 Context Engineering 思想可以概括为：**不是提供一个固定 ContextBuilder，而是通过 Agent Lifecycle 的 Middleware，让开发者控制每一次 Model Call、Tool Call 以及两者之间的 Context 变化。**

参考：[LangChain - Context engineering in agents](https://docs.langchain.com/oss/python/langchain/context-engineering)

### 1. 三类 Context 控制面

LangChain 官方把 Agent Loop 中可以治理的 Context 分成三类：

| Context 类型 | 控制什么 | 典型内容 |
| --- | --- | --- |
| **Model Context** | 某一次 LLM Call 真正看到什么 | System Prompt、Messages、Tools、Model、Response Format |
| **Tool Context** | Tool 能读取和写入什么 | State、Store、Runtime Context、Tool Result |
| **Life-cycle Context** | Model / Tool 调用之间发生什么 | Summarization、Guardrail、Logging、Context update |

其中 Model Context 是 transient 的：可以临时改变这一次调用看到的消息和工具，而不一定修改持久化 State；Tool write 和 Lifecycle hook 则可以修改持久状态，影响之后所有轮次。

### 2. 三种主要数据来源：Runtime Context、State、Store

LangChain / LangGraph 又从数据生命周期区分：

- **Runtime Context**：单次 run 内静态配置，例如 user ID、权限、API client、数据库连接；本质类似 dependency injection，不自动进入模型 Prompt。
- **State**：单个 thread / run 内动态变化的短期状态，如 Messages、上传文件、Tool Result、任务字段；可以被模型、Tool 和 Middleware 读写。
- **Store**：跨 conversation 的持久数据，如用户偏好、长期 Memory、历史洞察。

这三个来源可以共同决定动态 Prompt、当前可用 Tools 和注入 Messages。例如根据 Runtime Context 的用户权限隐藏写操作 Tool，根据 State 里的上传文件只注入当前相关文件摘要，根据 Store 中的用户偏好动态修改 System Prompt。

### 3. Middleware 是核心 Context Governance 机制

Middleware 可以在 Agent 生命周期各节点插入逻辑，例如：

```text
before_agent
    ↓
Model Call ── wrap_model_call / dynamic_prompt
    ↓
Tool Call  ── wrap_tool_call
    ↓
after_model / after_agent
```

因此开发者可以实现：

- 动态 System Prompt；
- 根据状态注入 / 删除 Messages；
- 动态选择 Tool Set；
- 根据任务选择不同 Model 或 Response Schema；
- Summarization / Message trimming；
- Guardrail、权限与 PII 处理；
- 从 Store 读取 Memory，或把结果写回 State / Store。

### 特点与优缺点

**优点**是控制面细、可组合，而且 Context Governance 与标准 Agent Loop 紧密结合。开发者可以只改变“这一轮模型看到什么”，也可以通过 State/Store 做持久更新；复杂度可以逐步增加，而不必一开始设计完整 Context Runtime。

**缺点**是 LangChain 更多提供 primitives 和 lifecycle hooks，而不是替你决定 Context Policy。什么时候 summarization、哪些 Memory 应注入、如何给 Evidence 分预算、怎样做冲突消解与 Context Eval，仍然需要业务侧自己设计。Middleware 过多时还可能形成新的隐式控制流：上下文究竟在哪里被修改，需要良好的 tracing 和约定才能调试。

> **LangChain 的 Context Engineering 更像“可编程的上下文生命周期”，而不是一套固定上下文算法。**

---

## Deep Agents 如何管理长时程 Context？

> Deep Agents 的 Harness 定位见 [[Agent框架#Deep Agents 是什么，它为什么比普通 Agent Harness 更“重”？|Deep Agents 是什么，它为什么比普通 Agent Harness 更“重”？]]。

Deep Agents 建立在 LangChain / LangGraph 之上，但比 LangChain 更 opinionated：它已经替长时程 Agent 预装了一套较完整的 Context Policy。官方目前把 Context Management 分成 **Input Context、Runtime Context、Context Compression、Context Isolation 与 Long-term Memory**。

参考：[Deep Agents - Context engineering](https://docs.langchain.com/oss/python/deepagents/context-engineering)

### 1. Input Context：少量常驻 + 能力渐进披露

启动时的 Context 主要包括：

- 自定义 System Prompt 与内置 Harness 指引；
- Memory，例如配置后的 `AGENTS.md`；
- Skills：只在相关时按需加载，属于 Progressive Disclosure；
- Tool Prompts / Tool Schemas；
- Filesystem、Subagent、HITL 等 Harness 自带说明。

这意味着 Deep Agents 并不试图把所有知识常驻 Prompt：Memory 用于真正“每次都相关”的长期约定，而更具体的能力通过 Skills 按需披露。

### 2. Runtime Context 与 State：运行依赖和可变状态分开

Runtime Context 保存 user metadata、API keys、connections、feature flags 等每次 run 的静态依赖，不自动进入 Model Prompt，但会传播给 Subagent；需要跨 Model / Tool Call 持续变化的数据则使用 Agent State，并由 LangGraph checkpoint 维护。

这种区分很重要：**模型不需要知道 API key，但 Tool 需要；模型可能需要知道当前用户角色，但可以由 Middleware 基于 role 生成适当指令，而不是暴露底层 credential。**

### 3. Filesystem + Offloading：把 Context Window 之外的空间当作工作记忆

Deep Agents 对大型 Tool Input / Result 会自动 offload 到配置的 filesystem/backend，并在消息中只留下文件路径和少量 preview。Agent 需要细节时再通过文件 Tool 搜索和读取。

因此它不是简单删除大输出，而是：

```text
Large Tool Result
      ↓
Persistent / Thread-local Filesystem
      ↓
Context 仅保存 Reference + Preview
      ↓
需要时 read_file / grep
```

这是一种**可恢复的 Context Compression**：active context 变小，但原始数据仍然存在。

当前官方实现还会在接近 Context Window 上限时自动 summarization，把旧 Message History 压缩成包含 session intent、artifacts 和 next steps 等信息的结构化摘要，同时把原始历史保存在 filesystem 中。具体阈值属于版本实现细节，不应当作 Context Engineering 的固定原则；真正重要的是“摘要留在工作集，原始记录留在外部存储”。

### 4. Context Isolation：Subagent 是隔离机制，不只是并行机制

主 Agent 将重型搜索、文件分析或数据库任务交给 Subagent 后，Subagent 使用自己的 fresh context 完成多轮工作，主 Agent 最终只接收一份 Final Report。于是几十次局部 Tool Call 不会全部污染主 Agent Context。

```text
Main Agent
   ↓ task
Subagent fresh context
   ↓
search / read / reason / tool ...
   ↓
summary + artifact references
   ↓
Main Agent
```

官方也建议让 Subagent 输出精炼结论，并把大型结果写入 Filesystem，让主 Agent 只读取必要片段。

### 5. Long-term Memory：Filesystem abstraction 连接跨 Thread Store

Deep Agents 的默认工作文件可以只存在单个 thread 的 State 中；需要跨会话持久化时，可以通过 `CompositeBackend` 把特定路径（例如 `/memories/`）路由到 LangGraph Store。这样文件系统同时承担了：

- thread-local 工作空间；
- cross-thread long-term memory；
- context offloading 的外部存储接口。

这让 Agent 可以用统一的文件 Tool 操作不同生命周期的数据，而 Runtime 在 Backend 层决定数据究竟存在哪、活多久。

### 特点与优缺点

**优点**是长时程 Agent 常见的治理机制——Progressive Disclosure、Filesystem Offloading、Summarization、Subagent Isolation、Long-term Memory——已经被整合为一套 Harness Policy，因此 Coding、Deep Research 等任务不必从零实现 Context Runtime。

**缺点**是更强的默认策略也意味着更强的框架假设。简单 Agent 可能不需要 Filesystem、Subagent 与自动压缩；而非常特殊的 Context Policy，例如自定义 Evidence Budget、复杂冲突仲裁或严格的信息流安全边界，仍可能需要自定义 Middleware 或直接下探 LangGraph。自动 Summarization 和 Subagent handoff 也存在有损压缩风险，因此仍需要 tracing、artifact provenance 和 eval。

> **Deep Agents 的 Context Engineering 核心不是“更大的 Context Window”，而是让 Agent 拥有一个 Context Window 之外的 Workspace，并通过按需读取、自动卸载、压缩和隔离，使 active working set 始终保持可控。**

---

## 当前认识

现代 Agentic Context 更适合被理解为一个 Runtime-managed working set，而不是静态 Prompt。一个成熟 Context Runtime 至少需要回答：

1. **Source**：信息可以从哪里来？
2. **Acquire**：什么时候加载，预加载还是 JIT？
3. **Select**：有限 token 预算下选哪些？
4. **Structure**：不同来源和权限的信息怎样明确组织？
5. **Compress / Offload**：什么可以摘要、外移或用引用代替？
6. **Isolate**：什么应该放进 Subagent 或局部 Context，而不是主 Context？
7. **Persist / Evict**：一轮结束后什么写入 State、Memory、Note 或 Filesystem，什么丢弃？
8. **Observe / Evaluate**：如何知道模型当时看到了什么，以及 Context Policy 是否真的提高任务成功率？

因此，[[Memory]] 解决的是“哪些信息值得跨时间保存”，[[RAG]] 解决的是“怎样从外部知识空间找回相关信息”，而 **Context Engineering 负责在 Agent Runtime 中把这些来源连成一个动态的信息供给与治理系统。**

---

相关主题：[[Agent]] · [[Agent框架]] · [[Memory]] · [[RAG]] · [[评估]] · [[部署]]
