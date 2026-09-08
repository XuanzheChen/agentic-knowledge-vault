# Memory

[[index|返回知识索引]] · [[Agent|Agent 基础]] · [[RAG]]

围绕工程化 Agent Memory 的框架、写入策略、一致性维护、聚合与遗忘机制整理。这里的 Memory 重点是 **Agent 如何从长期交互和执行经验中形成可复用状态**，而不是简单保存 Chat History；检索算法与 RAG 高度重叠的部分只保留必要说明。

> 版本说明：以下框架行为按 2026 年 9 月的官方文档与开源仓库整理。Memory 框架仍在快速演化，依赖具体版本的实现细节应以实际部署版本为准。

## 问题目录

- [[Memory#工程化 Agent Memory 的核心问题是什么？|工程化 Agent Memory 的核心问题是什么？]]
- [[Memory#Mem0 如何实现记忆的添加、搜索、遗忘与聚合？|Mem0 如何实现记忆的添加、搜索、遗忘与聚合？]]
- [[Memory#Letta 如何把 Memory 做进 Agent Runtime？|Letta 如何把 Memory 做进 Agent Runtime？]]
- [[Memory#Graphiti 如何用时序知识图谱实现长期记忆？|Graphiti 如何用时序知识图谱实现长期记忆？]]
- [[Memory#Mem0、Letta 与 Graphiti 分别适合什么场景？|Mem0、Letta 与 Graphiti 分别适合什么场景？]]
- [[Memory#主流工程化 Memory Pipeline 总体是什么思路？|主流工程化 Memory Pipeline 总体是什么思路？]]
- [[Memory#Memory Pipeline 各阶段有哪些主流实现与取舍？|Memory Pipeline 各阶段有哪些主流实现与取舍？]]

---

## 工程化 Agent Memory 的核心问题是什么？

教学实现常从 Working / Episodic / Semantic / Perceptual 等认知分类出发；工程系统更关心的是 **Memory Lifecycle**：

> **什么值得写 → 写成什么结构 → 与旧记忆是什么关系 → 存在哪里 → 什么时候召回 → 如何聚合 → 如何失效或删除。**

因此，Memory 不应被理解成“把每轮对话做 Embedding 后塞进 Vector DB”。原始消息、Tool Result、文件和环境事件只是 **Experience**，它们首先要经过写入判断和 Memory Formation，才可能成为真正的长期记忆。

比较成熟的系统通常同时解决三类问题：

1. **内容问题**：事实、用户画像、经历、规则、技能分别怎样表示？
2. **生命周期问题**：什么时候写、怎样更新、怎样去重、怎样处理冲突和过期？
3. **上下文问题**：哪些记忆应该始终在 Context 中，哪些只在需要时检索？

这也是工程 Memory 与单纯 Chat History 的主要区别。Agent 中“长期记忆应该少写、可更新、按需读”的基础原则见 [[Agent#长期记忆应写入什么，如何避免信息污染？|长期记忆应写入什么，如何避免信息污染？]]。

---

## Mem0 如何实现记忆的添加、搜索、遗忘与聚合？

### 核心定位

Mem0 更像一个可以插到现有 Agent 旁边的 **独立 Memory Layer / Memory Service**。Agent 不必采用特定 Runtime：交互结束后调用 `add`，下一次模型调用前调用 `search`，把相关 Memory 注入 Prompt 即可。

普通 Memory 主要通过 `user_id`、`agent_id`、`run_id` 等 scope 隔离，而不是强制把每条信息分成 Episodic / Semantic 等不同 Store。当前 Python OSS 中只有 `procedural_memory` 是真正接入实现的显式 `memory_type`；`semantic_memory` 和 `episodic_memory` 虽然存在枚举，但官方文档说明尚未接入对应 Pipeline。

参考：[Mem0 Memory Types](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-types.mdx) · [How Mem0 Works](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/how-it-works.mdx)

### 添加：从消息中形成可检索事实

`add()` 接收对话消息，并可附带 scope、metadata 和 `expiration_date`。默认 `infer=True` 时，Mem0 不要求把完整 Transcript 原样保存，而会借助 LLM 提取更适合长期复用的偏好、决策、计划和事实；`infer=False` 才是直接保存原始内容。

可以把基础写入路径理解为：

```text
Conversation / Fact
        ↓
     add()
        ↓
Context / Related Memory Lookup
        ↓
Durable Fact Extraction
        ↓
Deduplication + Entity Extraction
        ↓
Embedding + Persistence
```

其中 scope 决定“属于谁 / 哪个 Agent / 哪个任务”，metadata 负责业务过滤，`expiration_date` 则为具有自然失效时间的 Memory 提供生命周期边界。

**需要特别注意当前官方文档的版本不一致：**

- [Add Memory](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-operations/add.mdx) 与 [How Mem0 Works](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/how-it-works.mdx) 当前都把默认写入描述为 **additive pipeline**：自动抽取和去重，但不会静默覆盖或删除已有 Memory，需要应用显式调用 `update` / `delete` 做纠错。
- [Memory Types](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-types.mdx) 同时又描述了 `infer=True` 会检索相关旧 Memory，再由 LLM 对事实决定 `ADD / UPDATE / DELETE / no-op`。

因此工程实现不应把“自动冲突消解的具体语义”当成稳定接口契约。**更可靠的做法是把显式 `update` / `delete` 视为权威的一致性操作，并针对实际使用的 Mem0 版本测试 `infer=True` 的行为。**

### 搜索：先按 scope 隔离，再做相关性召回

最基本的使用方式是：

```text
Current Query
     ↓
search(filters = user / agent / run scope)
     ↓
Relevant Memories
     ↓
Context Assembly
     ↓
LLM
```

Mem0 OSS 以配置的 Vector Store 为主要检索基础，可配可选 Reranker，并利用实体重合辅助排序；具体能力依赖选择的 Store。Mem0 Platform 当前会融合 Semantic、Keyword、Entity 和 Temporal 等信号，并把内置 Graph Memory 的实体连接用于 Ranking。

这里最重要的工程原则不是某一种排序公式，而是：**先通过 scope / metadata 防止不同用户、Agent、任务之间的 Memory 串库，再从正确范围里做相关性检索。**

参考：[How Mem0 Works](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/how-it-works.mdx) · [Graph Memory](https://github.com/mem0ai/mem0/blob/main/docs/platform/features/graph-memory.mdx)

### 遗忘：显式删除、更新与过期

Mem0 的遗忘更偏工程一致性，而不是“记忆随时间自然衰减”。主要手段包括：

- **`delete` / `delete_all`**：明确移除不应再存在的 Memory。
- **`update`**：当事实发生变化时直接改写旧 Memory；它本质上属于一致性维护，而非真正遗忘。
- **`expiration_date`**：到期 Memory 默认不再出现在 `search` 和 `get_all` 中，但仍可以按 ID 获取，因此更接近“失效”而不是物理删除。
- **scope 级清理**：当一个用户、Agent 或 Run 生命周期结束时，可以按相应边界清理。

这种路线的优点是可预测，缺点是如果应用没有主动处理事实变化，旧事实可能继续存在。

### 聚合与一致性维护：重点不是摘要，而是事实级去重和纠错

Mem0 的普通 Memory 更接近 **Atomic Fact Collection**。因此它的“聚合”首先不是把 100 条 Episode 总结成一条知识，而是保证 Collection 不被重复、过时和互相矛盾的事实污染：

```text
New Candidate
      ↓
Find Related Memories
      ↓
Duplicate / Same Fact / Changed Fact / Conflict
      ↓
Keep / Merge / Update / Delete
```

默认写入已经包含相关 Memory 查询和 Deduplication；对明确的事实变更，应用还需要配合 `update`、`delete` 或自己的 reconciliation policy。若业务真正需要“多个事件 → 抽象成更高层知识或规则”，则通常需要在 Mem0 之上再加 Background Reflection / Consolidation，而不能只依赖普通 `add()`。

### 特点与优缺点

**特点**：独立于 Agent Runtime、Fact-oriented、scope 清晰、可替换 LLM / Embedding / Vector Store，适合作为现有 Agent 的长期事实层。

**优点**：

- 接入成本低，不需要为了 Memory 重构 Agent 控制流。
- 对用户偏好、项目决策、长期事实等 Atomic Memory 很自然。
- scope、metadata、expiration 和显式 CRUD 让工程边界较清楚。
- OSS 可以自选底层 Store；Platform 进一步提供多信号检索和 Graph Memory。

**局限**：

- OSS 并没有完整实现认知式 Semantic / Episodic 分类；普通 Memory 主要仍是事实集合。
- 多条经历如何抽象成稳定知识、技能或行为规则，需要额外设计。
- Collection 长期运行后仍要面对冲突、碎片化、低质量抽取和数据治理问题。
- 当前官方文档对自动更新 / 删除语义存在不一致，版本升级时需要回归测试 Memory 写入行为。

---

## Letta 如何把 Memory 做进 Agent Runtime？

### 核心定位

Letta（MemGPT 的后续体系）走的是 **Agent-managed Memory** 路线：Memory 不是旁挂的事实数据库，而是 Agent 自身 Context Architecture 的组成部分。当前 Letta Code 使用 Git-backed 的 MemFS，把长期 Context 投影为可以由 Agent 读写和重构的文件系统。

参考：[Letta Docs](https://docs.letta.com/) · [Letta Code](https://github.com/letta-ai/letta-code) · [MemFS Prompt / Architecture](https://github.com/letta-ai/letta-code/blob/main/src/agent/prompts/letta_local_memfs.md)

### Memory 的主要层级

- **Recall / Experience**：过去的完整消息经历自动保存；当前 Context 主要保留近期消息和较老内容的摘要，需要过去细节时再搜索。
- **Memory Blocks**：始终进入 System Prompt 的核心记忆，如 persona、用户稳定信息、关键行为规则。它们是最昂贵的 Context 位置，因此需要保持精炼。
- **External Memory**：Markdown、图片、项目资料等长期信息，不一直占 Context，需要时通过文件树、搜索和读取调入。
- **Skills**：可复用程序性知识（Procedural Memory），保存“以后遇到这类任务应该怎么做”。

因此 Letta 的 Memory 分类更接近 **上下文可见性与用途**，而不是四个独立数据库。

### 写入与搜索

写入权很大程度交给 Agent：当 Agent 判断某条信息应该影响未来行为时，可以修改 Memory Block、External Memory 或 Skill；用户也可以显式要求记忆。MemFS 的修改通过 Git 记录版本，便于查看 diff、回退和审计。

搜索同样偏 Agentic：目录结构本身就是索引，Agent 可以先看文件树，再 `grep` / read 对应内容；过去对话则通过 Recall / message search 访问。这和传统“所有东西都先向量化再 Top-K”不同。

### 遗忘与聚合

Letta 特别值得学习的一点是：**遗忘不等于删除。**

- 一条信息很重要时，可以进入始终在 Context 的 Memory Block。
- 不再值得每轮占 Token 时，可以从 Core / System Memory **降级（demote）**到 External Memory，需要时再找回来。
- 错误或过时内容可以 rewrite / delete；Git history 仍能保留变更轨迹。
- Background Reflection / Dreaming 与 Memory defragmentation 可以在后台整理近期经验、删除重复、拆分杂乱文件并改进 Memory 结构。

所以 Letta 的核心问题其实是 **Context Budget Management + Continual Learning**：什么应该始终看见，什么应该按需查找，什么应该从经验进一步变成规则或 Skill。

### 特点与优缺点

**优点**：Memory 真正进入 Stateful Agent 的 Runtime；Git-backed Memory 可审计、可回退；文件与 Skill 适合长期 Coding Agent、AI coworker 等持续工作场景；Promotion / Demotion 比简单 TTL 更符合 Context Engineering。

**局限**：体系比独立 Memory Service 更重；Memory 质量依赖 Agent 自主管理能力，可能出现错误写入、目录膨胀和重复；始终在 Context 的 Memory Block 会直接消耗每轮 Token，因此需要持续治理。对于只想记几个用户偏好的简单应用，Letta 往往属于过度工程化。

---

## Graphiti 如何用时序知识图谱实现长期记忆？

### 核心定位

Graphiti 把长期记忆建模为 **Temporal Knowledge Graph**。它特别适合“事实和关系会随时间变化”的场景，不只回答“有什么事实”，还试图回答“这个事实什么时候成立、什么时候失效、来自哪一次 Episode”。

参考：[Graphiti GitHub](https://github.com/getzep/graphiti) · [Quickstart](https://github.com/getzep/graphiti/blob/main/examples/quickstart/quickstart_neo4j.py)

### Memory 表示

- **Episode**：原始消息或事件，是事实的 provenance。
- **Entity Node**：人物、组织、项目、地点、概念等实体。
- **Entity Edge / Fact**：实体之间的关系和事实。
- **`valid_at` / `invalid_at`**：事实有效区间。

例如“某人从 A 公司转到 B 公司”不必简单覆盖成唯一当前值，而可以保留旧关系的有效期，再建立新的关系。

### 写入与一致性维护

典型写入路径为：

```text
New Episode
    ↓
Extract Entities / Relations
    ↓
Entity Resolution
    ↓
Find Existing Related Nodes / Edges
    ↓
Deduplicate + Contradiction Resolution
    ↓
Create New Facts / Invalidate Old Facts
    ↓
Persist Temporal Graph
```

Graphiti 的 edge resolution 代码会处理重复事实与冲突候选，并为被新事实取代的关系设置 `invalid_at` / `expired_at`。这种策略比直接 DELETE 更适合保留历史世界状态。

参考：[Graphiti edge operations](https://github.com/getzep/graphiti/blob/main/graphiti_core/utils/maintenance/edge_operations.py)

### 搜索、遗忘与聚合

Graphiti 的搜索可以组合 Semantic 与 BM25，并进一步使用 RRF、MMR 或 Cross-Encoder 等 Reranker；这里不展开算法细节，重点在于它可以利用图结构与时间状态搜索事实。

它的“遗忘”更接近 **Invalidate, don't delete**：旧事实仍然作为历史存在，但不再表示当前状态。聚合则主要发生在 Entity Resolution、Node / Edge Deduplication、关系冲突消解和实体摘要更新中。

### 特点与优缺点

**优点**：时间是一等信息；事实具有来源；适合关系密集、多跳查询和动态世界状态；历史事实不会因为一次更新而直接丢失。

**局限**：LLM 抽取、Entity Resolution、Graph DB 和时间冲突处理带来明显的成本与复杂度；错误实体合并会把污染传播到很多关系；对于简单用户偏好，图结构往往得不偿失。换言之，Graph Memory 并不是 Vector / Collection Memory 的“高级替代品”，而是适合不同问题的数据模型。

---

## Mem0、Letta 与 Graphiti 分别适合什么场景？

三者并不是在实现同一种“Memory 数据库”，而是在不同位置做工程化。

| 维度 | Mem0 | Letta | Graphiti |
| --- | --- | --- | --- |
| 核心定位 | 独立 Memory Layer | Stateful Agent / Context Runtime | Temporal Knowledge Graph |
| 典型记忆单元 | Atomic Fact | Memory Block / File / Skill / Experience | Episode / Entity / Fact |
| 主要写入者 | Extraction Pipeline + 应用显式 CRUD | Agent 自主管理 | Extraction + Resolution Pipeline |
| 主要聚合 | 去重、事实一致性维护 | Background Reflection、重构、总结 | Entity / Edge Resolution |
| 主要遗忘 | Delete / Update / Expire | Demote / Rewrite / Delete | Invalidate / Expire Fact |
| 历史保留 | 依实现与 History | Git history + Recall | Temporal validity + provenance |
| 最突出能力 | 易接入、长期事实 | Context Engineering、持续学习 | 动态关系、时间一致性 |
| 典型适用 | 用户偏好、个性化、项目事实 | 长期 Coding Agent、个人助手、AI coworker | 组织关系、客户状态、动态实体网络 |

可以把三者的核心启发压缩成：

> **Mem0 教“如何维护事实集合”；Letta 教“如何管理 Agent 的长期 Context”；Graphiti 教“如何维护随时间变化的世界模型”。**

实际系统完全可以组合这些思想，而不必只选择一种 Memory 数据模型。

---

## 主流工程化 Memory Pipeline 总体是什么思路？

综合 Mem0、Letta、Graphiti，以及 LangMem 对 Semantic / Episodic / Procedural Memory 与 Hot-path / Background 写入的抽象，一个比较通用的工程 Pipeline 可以写成：

```text
Experience
message / tool / file / feedback / environment
                     ↓
               ① Write Gate
              “值得记吗？”
                     ↓
             ② Memory Formation
       fact / profile / episode / rule
                     ↓
              ③ Reconciliation
      new / duplicate / update / conflict
                     ↓
               ④ Persistence
      prompt / SQL / vector / file / graph
                     ↓
                  ⑤ Recall
                     ↓
              Context Assembly
                     ↓
                   Agent
                     ↓
              New Experience

Background Loop:
Memory → Reflection → Consolidation → Promote / Demote / Invalidate / Delete
```

这条 Pipeline 的核心不是某个具体 Vector DB，而是两个闭环：

1. **在线闭环**：Experience → Memory → Recall → Agent → New Experience。
2. **后台闭环**：低质量、重复和具体经验不断被整理、压缩、抽象和失效。

LangMem 的抽象与这一思路很接近：Memory 操作通常同时接收新 Conversation 与当前 Memory State，再由模型决定如何扩展或 Consolidate；写入既可以发生在 Hot Path，也可以通过 ReflectionExecutor 等机制延迟到 Background。

参考：[LangMem Core Concepts](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/) · [Background Memory](https://langchain-ai.github.io/langmem/background_quickstart/)

---

## Memory Pipeline 各阶段有哪些主流实现与取舍？

### 1. Write Gate：Experience 不等于 Memory

原始数据包括 Conversation、Tool Result、文件、环境事件和用户反馈，但长期 Memory 应优先保存 **future utility 高**的信息，例如稳定偏好、重要决策、可复用经验和规则。

常见写入时机有三种：

| 策略 | 思路 | 优点 | 缺点 |
| --- | --- | --- | --- |
| Hot Path / Agent-managed | Agent 当场调用 Memory Tool 保存 | 意图明确、信息新鲜 | 增加延迟，Agent 可能过度记录 |
| Synchronous Extractor | 每轮或阶段结束后自动抽取 | 自动、容易接入 | 每轮有模型成本，局部上下文可能不足 |
| Background Reflection | 会话稳定后批量抽取和整理 | 不阻塞前台，可看到更完整经历 | Memory 更新有延迟 |

生产系统经常混合使用：明确用户偏好可即时保存，普通 Conversation 放到后台总结，关键业务状态则走确定性数据库写入。

### 2. Memory Formation：形成什么数据结构？

#### Core / Working Context

保存当前必须始终让模型知道的信息，例如角色、关键用户偏好和任务约束。实现可以是 System Prompt、Memory Block、Agent State 或滚动 Summary。

优点是不需要检索；缺点是每一 Token 都会反复进入模型，因此 **Context Budget 本身就是 Memory 容量上限**。

#### Semantic Memory

主流有三种表示：

- **Profile**：一个结构化 User / Agent Profile，不断原地更新。读取简单、一致性好，但 Schema 固定且对象会膨胀。
- **Collection**：把事实拆成多个 Atomic Records。扩展性强、易搜索，但必须处理重复、矛盾和碎片化。Mem0 更接近这一方向。
- **Graph**：实体、关系和属性组成知识图谱。适合关系与多跳问题，但构图和 Entity Resolution 昂贵。Graphiti 属于这一方向。

LangMem 也把 Profile 与 Collection 作为 Semantic Memory 的两种典型表示。

参考：[LangMem Core Concepts](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/) · [Manage User Profiles](https://langchain-ai.github.io/langmem/guides/manage_user_profile/)

#### Episodic Memory

简单实现是保存 Session / Event Summary；更有价值的实现是 **Experience Replay**：

```text
Situation / Observation
        ↓
Strategy / Action
        ↓
Result
        ↓
Lesson
```

这样 Agent 下次遇到相似问题，不只是知道“发生过”，还可以复用过去成功或失败的处理经验。

参考：[LangMem Episodic Memory](https://langchain-ai.github.io/langmem/guides/extract_episodic_memories/)

#### Procedural Memory

保存“以后应该怎么做”：System Prompt Rules、SOP、Skills、Workflow 或由过去轨迹总结出的行为策略。Letta 的 Skills 和 LangMem 的 Prompt Optimization 都体现了这种路线。

多模态输入通常不必单独建立一个 `PerceptualMemory` 数据库：更常见的是把图片、音频、PDF 等原始 Artifact 放在 Object / File Store，再把 OCR、Caption、Embedding、事件引用等写入 Semantic / Episodic Memory。

### 3. Reconciliation：新信息不能直接 INSERT

成熟 Memory Collection 应先比较新 Candidate 和旧状态：

```text
Candidate
   ↓
Retrieve Related Existing Memories
   ↓
New / Duplicate / Update / Contradiction / Obsolete
   ↓
Insert / Merge / Update / Invalidate / Delete
```

这一步是工程 Memory 的核心之一。过度写入会降低 Search Precision；写得太少又会降低 Recall。Collection、Profile 和 Graph 的区别，很大程度就在于它们采用了不同的一致性策略。

### 4. Persistence：不同 Memory 放到不同 Store

| Memory / 数据 | 常见存储 |
| --- | --- |
| Core / Working | Prompt / Agent State / Checkpoint |
| Profile | SQL / JSON / Document |
| Semantic Collection | SQL + Vector Index |
| Episodic History | Event Log / SQL + Search Index |
| Procedural | Prompt / Git / Skills / Workflow Config |
| Temporal / Relational | Graph DB |
| Raw Artifact | Object Storage / Filesystem |

因此“选哪个 Vector DB”只是 Persistence 的一个局部问题，而不是 Memory Architecture 本身。

### 5. Consolidation：记忆的价值来自抽象，而不只是累积

常见聚合方式至少有四种：

1. **Fact Consolidation**：把同义、重复事实合并成更干净的 Atomic Memory。
2. **Summary Consolidation**：把大量消息 / Episode 压缩成 Summary，解决 Context 膨胀。
3. **Entity Consolidation**：把 `NYC / New York / New York City` 等解析为同一实体，并合并关系。
4. **Experience → Knowledge / Procedure**：从多次 Episode 中总结稳定事实、故障模式或可复用 Skill。

最后一种最接近“Agent 从经验中学习”：

```text
多个 Episode
     ↓
Reflection
     ↓
Semantic Knowledge
     ↓
Procedural Rule / Skill
```

### 6. Forgetting：工程系统至少有四种“忘”

- **Hard Delete**：真正删除，适合隐私删除、错误数据或明确撤回。
- **Expiration**：TTL / expiration 到期后不再参与正常 Recall。
- **Invalidation**：保留历史，但标记“已经不再成立”；Graphiti 的时序 Fact 是典型例子。
- **Demotion**：从 Always-in-context Memory 移到按需检索的 External Memory；Letta 的 Context Management 更强调这一点。

此外，**Consolidation 本身也是一种信息压缩式遗忘**：细节被更高层的 Summary、Fact 或 Rule 取代，从而降低长期 Context 和 Retrieval 噪声。

### 总结

工程上更值得追求的不是“记住更多”，而是：

> **只形成未来真正有价值的 Memory；让新旧信息可一致地演化；把重要信息放在合适的 Context 层级；再通过后台聚合与失效机制，让 Memory 随时间变得更干净、更抽象，而不是越来越像一个无边界日志库。**
