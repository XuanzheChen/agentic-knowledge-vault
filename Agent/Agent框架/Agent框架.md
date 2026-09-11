# Agent 框架

[[Agent|返回上级：Agent]] · [[main|返回知识主干]] · [[Agent/Context/context|Context 工程]]

围绕 Agent 开发框架的抽象层级、协作范式、工程取舍与选型整理。经典多 Agent 框架与 LangGraph 的横向比较、LangChain / LangGraph / Deep Agents 的层级关系统一放在这里；具体的 Agent 执行范式与运行时约束见 [[Agent]]。

## 问题目录

- [[Agent框架#AutoGen、AgentScope、CAMEL 与 LangGraph 的核心差异是什么？|AutoGen、AgentScope、CAMEL 与 LangGraph 的核心差异是什么？]]
- [[Agent框架#LangChain 在 Agent 开发中解决什么问题？|LangChain 在 Agent 开发中解决什么问题？]]
- [[Agent框架#Deep Agents 是什么，它为什么比普通 Agent Harness 更“重”？|Deep Agents 是什么，它为什么比普通 Agent Harness 更“重”？]]
- [[Agent框架#如何从 Agent 层级理解 LangChain、LangGraph 与 Deep Agents？|如何从 Agent 层级理解 LangChain、LangGraph 与 Deep Agents？]]

---

## AutoGen、AgentScope、CAMEL 与 LangGraph 的核心差异是什么？

这四个框架并不是简单的“同类产品四选一”，而是在解决 Agent 系统的不同核心矛盾。按照 [Hello-Agents 第六章](https://hello-agents.datawhale.cc/#/./chapter6/%E7%AC%AC%E5%85%AD%E7%AB%A0%20%E6%A1%86%E6%9E%B6%E5%BC%80%E5%8F%91%E5%AE%9E%E8%B7%B5) 的划分，可以先抓住两个坐标轴：**AutoGen / CAMEL 更偏涌现式协作，LangGraph 更偏显式控制；AgentScope 则额外强调从原型走向生产时的工程化能力。**

### AutoGen

AutoGen 的核心抽象是“**通过对话完成协作**”：把 Product Manager、Coder、Reviewer 等不同角色建模成可对话 Agent，再规定轮询、接管或终止等基本交互规则，让任务在多轮群聊中逐渐完成。

它的优点是贴近人类团队协作，角色扩展直观；在需求开放、路径不确定的多专家讨论和协作任务中，不需要预先把每条控制路径都写成代码。代价也来自同一设计：控制流有一部分交给 LLM 和对话本身，Agent 可能跑题、越权、重复讨论或形成非预期循环，出现问题时还需要从较长的对话轨迹中定位原因。

因此 AutoGen 更偏向：**定义谁参与、各自负责什么，让协作从对话中涌现。**

### CAMEL

CAMEL 最具代表性的思想是 Role-Playing 与 Inception Prompting：给两个互补角色设定身份、共同目标和协作规则，例如“懂业务但不懂代码的交易员”与“懂代码的 Python 程序员”，然后让它们通过多轮对话自主推进任务。

它的优点是轻量，能够用较少的流程代码换来较深的专家协作，尤其适合创意、研究、写作和跨领域讨论；缺点是效果高度依赖角色和 Prompt，当协作失败时，不容易判断究竟是角色定义、任务描述、交互协议还是模型能力出了问题。双 Agent 范式扩展到大规模多 Agent 后，还会自然遇到消息路由、状态同步和冲突仲裁问题。

因此 CAMEL 可以理解为：**用精心设计的角色关系换取协作涌现。**

### AgentScope：重点是把多 Agent 从“能聊”推进到“能稳定运行”

AgentScope 的主要价值不只是提供另一种 Agent 对话 API，而是把多 Agent 系统当成需要并发、通信、部署、恢复和观测的软件系统来设计。Hello-Agents 因此把它概括为“工程化优先”的多智能体平台。

它采用消息驱动思路：Agent 之间的交互被抽象成 `Message` 的发送与接收，`MsgHub` 负责消息路由，`Pipeline` 负责编排顺序或并发流程；更上层再由 Runtime、Studio 等能力负责运行和开发支持。

几个重要的后端概念可以拆开理解：

- **消息驱动 / 异步解耦**：传统同步函数调用类似 `A()` 调 `B()` 后必须等 B 返回；消息模式更像 A 把任务投递出去，由 B 在能够处理时消费。“谁发消息”和“谁处理消息”在时间上可以解耦，更容易并行。这与后端里的[事件驱动架构（Event-Driven Architecture）](https://learn.microsoft.com/zh-cn/azure/architecture/guide/architecture-styles/event-driven)接近，但 AgentScope 的消息机制是框架内部多 Agent 通信抽象，而事件驱动架构是更广义的软件架构模式。
- **位置透明与分布式部署**：Agent A 不必关心 Agent B 是否与自己在同一进程或同一台机器。RPC（Remote Procedure Call）可以理解为“像调用本地函数一样调用另一台机器上的服务”；可参考 [gRPC 的介绍](https://grpc.io/docs/what-is-grpc/introduction/)。
- **水平扩展（Horizontal Scaling）**：负载增加时，通过启动更多相同服务实例共同处理请求，而不是只给一台机器增加资源。Kubernetes 的 [Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) 是这一思想的典型工程实现。
- **可观测性（Observability）**：需要知道一次请求经过了哪些 Agent、哪一步慢、哪一步报错、吞吐和失败率怎样。后端通常用 Logs、Metrics、Traces 观察系统；可参考 [OpenTelemetry Signals](https://opentelemetry.io/docs/concepts/signals/)。消息天然成为较好的追踪边界。
- **容错与恢复**：消息可以被记录、持久化并在失败时重试；同时必须处理消息顺序、重复消费、幂等和最终一致性等分布式系统问题。

这些能力适合需要长期运行、Agent 数量较多、服务需要横向扩展的生产系统；代价是工程复杂度显著上升。对于“一个 Researcher 调一个 Writer”这样的简单 Agent，完整的分布式运行时可能属于过度工程化。

> **AgentScope 更关心“怎样让复杂 Agent 系统稳定地服务”，而不只是“怎样让 Agent 更聪明地对话”。**

### LangGraph：把 Agent 应用变成显式状态图

LangGraph 最值得理解的地方，是它不把 Agent 主要看成一个“会说话的角色”，而是把整个 Agent 应用建模为一个随 State 演化的、可循环和可恢复的状态图。因此它尤其适合需要明确控制流、重试、审批、审计和长时间运行的 Agent。

1. **State、Node、Edge 是核心抽象。** [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) 中，`State` 表示当前应用状态的共享快照；`Node` 是读取状态并执行计算的函数，可以是 LLM、Tool、普通 Python 逻辑、数据库操作甚至另一个 Agent；`Edge` 决定下一个节点。Conditional Edge 可以根据当前 State 动态路由。

   ```text
   START → Planner → Executor → Reviewer
                         ↑          │
                         └── fail ──┘
                                    │ pass
                                    ↓
                                   END
   ```

2. **循环是它对 Agent 特别重要的能力。** ReAct 的 Tool Loop、Reflection 的“生成—评审—修改”、代码 Agent 的“实现—测试—修复”，本质上都是包含条件回边的 Graph。条件边把“什么时候重试、什么时候结束、失败后回哪里”从自然语言协商提升为显式程序逻辑。
3. **State 连接持久化与 Human-in-the-loop。** [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) 可以保存 Checkpoint；[Interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts) 可以在关键动作前暂停，等待人工批准、编辑或拒绝，再从同一状态继续。
4. **Subgraph 让多 Agent 仍能建立在图模型上。** Research Agent、Coding Agent 或 Reviewer 可以分别作为子图，由上层 Supervisor Graph 负责路由；[Subgraph persistence](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) 还可以单独控制子 Agent 是否跨调用保留内部状态。

它的主要优势是控制流清楚、循环与回退自然、状态可追踪；主要代价是需要提前设计 State Schema、节点职责、边和终止条件，简单任务会显得代码更多，涌现式自由协作也不如 AutoGen / CAMEL。

> **LangGraph 的价值不是替 LLM 增加新的推理能力，而是为 Agent 外部执行过程提供可编程控制平面。**

综合来看，可以把四种框架记成四句话：**AutoGen 关心“多个角色怎样通过对话协作”；CAMEL 关心“怎样通过角色设定促成自主协作”；AgentScope 关心“多 Agent 怎样作为分布式软件系统稳定运行”；LangGraph 关心“整个 Agent 执行过程怎样被状态与控制流精确编排”。**

---

## LangChain 在 Agent 开发中解决什么问题？

### 核心定位

当前 LangChain 官方把自己定位为一个 **Agent Framework**：它提供 `create_agent` 这样的最小、可高度配置的 Agent Harness，把模型、工具、Prompt 和 Middleware 组合成一个标准 Agent Loop。官方对 Agent 的简化定义是：模型不断调用工具，直到任务完成；而 Harness 是包在这个循环外面、决定模型“什么时候看到什么上下文、能调用什么工具、受到什么约束”的那一层系统。

参考：[LangChain Overview](https://docs.langchain.com/oss/python/langchain/overview) · [Agents](https://docs.langchain.com/oss/python/langchain/agents)

最简单的 LangChain Agent 可以理解成：

```text
Model + Tools + System Prompt
            ↓
      create_agent()
            ↓
Model → Tool → Model → Tool → ... → Finish
```

因此，LangChain 现在最重要的价值已经不只是早期“Chain”概念，而是两类统一抽象：

1. **模型与工具的统一接口**：不同模型提供商、Python 函数、LangChain Tool 等可以用较统一的方式接入 Agent，降低模型和工具替换成本。
2. **Agent Harness 与 Middleware**：`create_agent` 给出标准 Tool Loop；Middleware 则在模型调用、工具调用和状态更新等位置插入能力，例如动态 Prompt、重试、限流、PII 检查、Human-in-the-loop、Summarization、Memory、Skills、Subagent 等。

可以把 Middleware 类比成 Web 后端的中间件：核心请求流程不变，但每个 Middleware 在流程的特定位置增加一个横切能力，例如认证、日志、重试或限流。对 Agent 而言，它所拦截和增强的对象从 HTTP 请求变成了 **Model Call、Tool Call 和 Agent State**。

更具体的 Context 生命周期控制见 [[Agent/Context/context#LangChain 如何设计 Context Engineering？|LangChain 如何设计 Context Engineering？]]。

### 优点

- **上手快**：不需要自己实现 Model ↔ Tool 的循环，只需给 `create_agent` 配置模型和工具即可形成一个可运行 Agent。
- **标准化程度高**：模型、工具、消息、结构化输出、状态等都有相对统一的抽象，适合快速替换供应商或组合生态组件。
- **可渐进扩展**：简单应用只用 `model + tools`；复杂后再逐步添加 Middleware，而不是一开始就设计完整状态图。
- **和 LangGraph 同源**：LangChain Agent 本身运行在 LangGraph 之上，因此可以继承持久化、Streaming、Human-in-the-loop 等 Runtime 能力，但开发者并不需要先理解 LangGraph 才能使用 LangChain。

### 局限

LangChain 的便利来自它已经替开发者预设了一个标准 Agent Loop。当任务主要就是“模型决定是否调用工具，然后继续循环”时非常合适；但如果真正的问题是：**A 节点失败后必须回到 B、C 和 D 要并行、人工审批后才能进入 E、某些步骤完全不允许由模型决定**，那么继续堆 Middleware 会逐渐变得别扭，此时通常应该下探到 LangGraph 直接描述控制流。

另外，LangChain 虽然可以通过 Middleware 逐项加入文件系统、上下文压缩、Subagent、Memory 等能力，但这些能力默认并没有被组装成一个完整的长期任务 Harness。对于 Coding Agent、Deep Research Agent 这类长时间、多步骤任务，开发者如果全部自己组合，很容易重新做一遍“上下文治理 + 工作空间 + Delegation + 权限 + 恢复”的工程；这正是 Deep Agents 想进一步封装的部分。

> **LangChain 的核心价值：给你一个标准、可组合的 Agent Loop 和组件接口，让你用较少代码搭出“自己的 Harness”。**

---

## Deep Agents 是什么，它为什么比普通 Agent Harness 更“重”？

### 核心定位

Deep Agents 是 LangChain 团队提供的 **opinionated、batteries-included Agent Harness**。它不是一种新的模型，也不是一种新的 Runtime；`create_deep_agent()` 最终仍然建立在 LangChain 的 `create_agent()` 以及 LangGraph Runtime 之上。它做的事情是：把复杂、长时程 Agent 经常需要的能力预先组装好，并给出一套默认工作方式。

参考：[Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview) · [Deep Agents GitHub](https://github.com/langchain-ai/deepagents)

这里的“Deep”更适合理解为 **long-horizon / complex multi-step agent**，而不是“LLM 本身进行了更深的推理”。它主要补齐四个方面：

1. **执行环境（Execution Environment）**：除了自定义 Tools，还提供虚拟文件系统、可插拔 Backend、文件权限，以及可选的 Sandbox / Shell / Interpreter。Agent 因而不只是“调用几个 API”，而是拥有一个可持续操作的工作空间。
2. **上下文治理（Context Management）**：通过 Summarization、Context Offloading、Prompt Caching 等机制处理长任务中不断膨胀的消息和 Tool Result；Memory 和 Skills 则让长期信息与领域能力按合适方式进入上下文。
3. **Delegation**：主 Agent 可以把子任务交给 Subagent。Subagent 使用独立 Context Window，完成后只把结果返回主 Agent，因此既可以并行处理任务，也可以避免某个重型子任务把主 Agent 上下文污染得过大。任务规划能力也可以按需加入。
4. **Steering / Safety Boundary**：关键 Tool Call 可以暂停等待人工批准；文件访问可以声明权限。它也支持 MCP 等工具协议，从外部系统接入能力。

可以把一个 Deep Agent 粗略看成：

```text
                     ┌─ Skills / Memory
                     ├─ Summarization / Context Offloading
Model + Agent Loop ──┼─ Filesystem / Sandbox / Shell
                     ├─ Subagents / Delegation
                     └─ HITL / Permissions
```

### 为什么需要文件系统？

文件系统不只是为了“让 Coding Agent 编辑代码”。它还承担一种 **外部工作记忆（external working memory）** 的作用：大段搜索结果、报告草稿、中间数据和子任务产物不必全部长期塞在 LLM Context Window 里，可以落到文件中，需要时再检索和读取。于是 Agent 的工作空间从“只有聊天历史”变成了“Context Window + Persistent Workspace”。

这种思想和 Coding Harness 很接近：LLM 不需要一次记住整个仓库，它可以通过 `grep`、`read_file`、`edit_file`、测试命令等不断读取环境并修改环境。

### 为什么需要 Subagent？

Subagent 不只是“多一个模型”。它还有一个重要的 **Context Isolation** 作用。例如主 Agent 需要调查三个互不相关的技术方案，如果都在主上下文里进行搜索，每个方案的网页内容、工具结果和推理轨迹都会互相挤占 Token；如果分别委派给三个 Subagent，它们可以在独立 Context Window 中工作，主 Agent 最终只接收三个相对紧凑的结论。

因此 Delegation 同时解决两类问题：

- **并行计算**：多个独立任务可以同时推进。
- **上下文隔离**：局部任务的过程信息不必全部进入主 Agent Context。

Deep Agents 更完整的 Context Offloading、Summarization、Isolation 与 Long-term Memory 设计见 [[Agent/Context/context#Deep Agents 如何管理长时程 Context？|Deep Agents 如何管理长时程 Context？]]。

### 优点

- 对长时程、多步骤任务开箱即用，不必从零设计文件工具、Context Compression、Memory、Subagent 等基础设施。
- 通过 Filesystem + Context Offloading + Subagent Isolation，使 Agent 能处理远超单次 Context Window 的工作量。
- 保留较强可扩展性：模型、工具、Backend、Middleware、Subagent 都可以替换或扩展，而不是一个完全封闭的 Agent 产品。
- 底层仍使用 LangGraph，因此可以利用 Persistence、Checkpoint、Streaming 与 Interrupt 等运行时能力。

### 局限

- **更有主见，也意味着更多默认行为。** 对一个只需要调用两三个工具的简单 Agent，这套 Harness 可能带来不必要的工具描述、状态和工程复杂度。
- **它优化的是一种通用长时程 Agent 形态，而不是任意控制流。** 如果业务流程需要非常特殊、强确定性的状态迁移，直接写 LangGraph 往往更清楚。
- **能力越强，安全边界越重要。** 文件写入、Shell、外部 MCP Tool 都可能产生真实副作用，不能只依赖 Prompt 要求模型“不要做危险操作”；权限、Sandbox、Tool Policy 和 Human Approval 应放在 Harness / Runtime 层执行。
- **Subagent 和长期上下文不是免费的。** 并行委派、总结和额外模型调用会增加 Token、延迟和调试维度，因此需要根据任务复杂度决定是否值得。

> **Deep Agents 的核心价值：不是重新定义 Agent Loop，而是把一个能够长期工作的 Agent 所需要的“工作空间、上下文治理、委派与安全控制”预装到 Harness 中。**

---

## 如何从 Agent 层级理解 LangChain、LangGraph 与 Deep Agents？

### 先纠正一个容易混淆的层级关系

如果按软件依赖和抽象层级来看，三者不是：

```text
LangChain → LangGraph → Deep Agents
```

而更接近：

```text
              应用 / 具体 Agent
                     │
              Deep Agents
          opinionated full harness
                     │
               LangChain
       agent framework / create_agent
                     │
               LangGraph
       orchestration runtime / graph
                     │
     Model · Tools · Storage · External Systems
```

也就是：**Deep Agents 构建在 LangChain Agent abstraction 之上，而 LangChain Agent 又运行在 LangGraph Runtime 之上。** 官方目前也分别把三者称为 Harness、Framework 和 Runtime。

参考：[Runtimes, frameworks, and harnesses](https://docs.langchain.com/oss/python/concepts/products)

### 第一层：LangGraph 管“这个过程怎样运行”

**LangGraph 是 Runtime / Orchestration 层。** 它关心 State 怎样保存，Node 怎样执行，Edge 怎样迁移，什么时候暂停、恢复、重试或 Streaming。它最核心的问题不是“Agent 应该有哪些工具”，而是：

> **一次有状态的执行应该怎样可靠地向前推进？**

因此它给开发者最大的能力是 **控制权**。你可以把 deterministic workflow 和 agentic decision 混在同一个 Graph 里：有些 Edge 由程序硬编码，有些 Edge 由 LLM 决定；有些节点是模型，有些节点只是普通函数或人工审批。

它的优点是控制细、状态显式、适合复杂工作流与长期可靠运行；缺点是开发者要自己设计 State Schema、Node、Edge 和异常路径，开发成本最高。

### 第二层：LangChain 管“一个标准 Agent 由哪些东西组成”

**LangChain 是 Agent Framework 层。** 它把底层 Graph 中最常见的一种形态——`Model → Tool → Model → ... → Finish`——包装成 `create_agent`，再通过 Model、Tools、Prompt 和 Middleware 暴露常用扩展点。

它回答的问题更像：

> **怎样快速组合出一个符合业务需求的 Agent？**

因此你通常不关心底层 Node 和 Edge，只关心选哪个模型、给哪些工具、用哪些 Middleware。它牺牲一部分控制粒度，换来开发效率和标准化。

### 第三层：Deep Agents 管“一个长期自主工作的 Agent 还缺什么”

**Deep Agents 是 Full Harness 层。** 它假定仅有 Tool Loop 还不足以完成 Coding、Research 等长任务，于是在 LangChain Agent 外围预装工作空间、Context Engineering、Memory、Skills、Subagent Delegation、权限与人工介入等能力。

它回答的问题进一步变成：

> **怎样让这个 Agent 不只是会调用工具，而是真正能够持续完成一个复杂任务？**

因此 Deep Agents 的抽象更接近 Claude Code、Codex 一类 Agent Harness，而不是单纯的 LLM 调用库。

### 三者的取舍

| 层级 | 核心抽象 | 主要解决的问题 | 优点 | 主要代价 |
| --- | --- | --- | --- | --- |
| **LangGraph** | State / Node / Edge / Runtime | 执行过程怎样可靠、可控地运行 | 控制粒度最高；适合循环、分支、恢复、HITL、复杂编排 | 要自己设计状态图，代码与认知成本最高 |
| **LangChain** | Model / Tool / Agent Loop / Middleware | 怎样快速组合一个可定制 Agent | 上手快、标准化、生态丰富、可以渐进扩展 | 默认围绕标准 Tool Loop；特殊控制流会逐渐别扭 |
| **Deep Agents** | Workspace / Context / Subagent / Full Harness | 怎样让 Agent 长时间自主完成复杂任务 | 长任务常用能力开箱即用；上下文治理和委派完善 | 更重、更有默认假设；简单任务可能过度工程化 |

可以用一个非常简化的尺度来记：

```text
更底层、更多控制                               更高层、更多默认能力

LangGraph  ───────────── LangChain ───────────── Deep Agents
Runtime                 Framework                 Harness
怎么运行                 怎么搭 Agent              怎么让 Agent 长期工作
```

这里并不是“越右越高级、越好”。相反，**越往右，框架替你决定得越多，开发越快；越往左，你自己决定得越多，控制越精细。**

### 一个具体例子：开发 Research Agent

如果只需要“模型可以搜索网页，然后综合回答”，LangChain 的 `create_agent(model, tools=[search])` 就可能足够。

如果要求流程严格是：

```text
提出搜索计划
   ↓
并行执行 3 组搜索
   ↓
证据完整性检查
   ↓ 不完整
回到指定搜索节点
   ↓ 完整
人工确认
   ↓
生成报告
```

那么核心难点已经是控制流，应优先考虑 LangGraph。

如果要求 Agent 自己处理一个数小时的研究任务：不断搜索、把资料落盘、压缩旧上下文、派多个研究 Subagent、维护长期笔记、最终生成多个文件，那么这些需求恰好接近 Deep Agents 预装的 Harness 能力。

### 学习路径怎么理解？

虽然软件依赖是：

> **Deep Agents → LangChain → LangGraph**

但学习路径完全可以采用：

> **LangChain → LangGraph → Deep Agents**

先用 LangChain 理解一个标准 Agent Loop 需要 Model、Tool、Prompt、State 和 Middleware；再下探 LangGraph，看这个 Loop 在 Runtime 层如何被表示为 State、Node、Edge、Checkpoint 和 Interrupt；最后再回到 Deep Agents，看一个成熟 Harness 如何把 Filesystem、Context Engineering、Memory、Skills 和 Subagent 等能力装配在这个 Loop 外面。

这样学的好处是：你不会把 Deep Agents 的各种能力当成“魔法”。你能够逐层还原它：**最底下仍然是一个有状态的执行 Runtime，中间是标准 Agent Loop，最上面才是长期任务所需的一整套 Harness Engineering。**

> **最终总结：LangGraph 提供 Agent 的“执行骨架”，LangChain 提供 Agent 的“标准组装接口”，Deep Agents 则给这副骨架和接口装上适合长期工作的“完整装备”。**

---

相关主题：[[Agent]] · [[Agent/Context/context|Context]] · [[对比问题]] · [[评估]] · [[部署]]
