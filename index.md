# AI 知识 Q&A

从底层概念出发，记录原理、工程取舍与个人思考。按主题进入笔记，再通过问题目录跳转到具体 Q&A。

## 一级概念

| 主题 | 内容 |
| --- | --- |
| [LLM](LLM.md) | RNN 长期依赖、Token Embedding、Transformer 架构与 KV Cache 等模型基础机制 |
| [预训练](预训练.md) | 大规模通用数据上的基础能力与知识学习 |
| [中训练](中训练.md) | 通过更定向的继续训练强化领域、推理、代码、长上下文等基础能力 |
| [后训练](后训练.md) | SFT、偏好学习、强化学习、自训练与蒸馏等后训练范式及训练数据 |
| [残差连接](残差连接.md) | 传统 Residual、Hyper-Connections、mHC、Gated Residual 与 AttnRes 的深度信息流 |
| [注意力机制](注意力机制.md) | 现代 Attention / Linear Attention 机制，目前包括 KDA 及相关架构演进 |
| [Agent](Agent.md) | Agent State、持续对话、意图冲突、执行范式与运行时约束 |
| [Agent框架](Agent框架.md) | LangChain、LangGraph、Deep Agents 等框架的抽象层级、设计取舍与选型 |
| [通信协议](通信协议.md) | MCP、A2A、ANP 的协议定位，以及 MCP 与 Function Calling、Code Mode 的关系 |
| [Context](context.md) | Agentic Context 的来源、动态治理、压缩、外部化、隔离与框架实现 |
| [Memory](Memory.md) | 工程化 Agent Memory 的框架、写入策略、一致性维护、聚合与遗忘 |
| [RAG](RAG.md) | 数据与索引组织、Embedding、Chunk、RAG 框架、Pipeline 与主流检索架构 |
| [评估](评估.md) | Agent 的任务结果、执行过程、可靠性与效率 |
| [部署](部署.md) | 显存、并发、吞吐、延迟、稳定性与成本 |
| [对比问题](对比问题.md) | CoT / ToT / Agent Thought、KV Cache / Prompt Cache、微调 / RAG / 规则、Memory / RAG |

## 待继续思考的问题

- [[RAG#RAG 解决什么问题，与幻觉有什么关系？|RAG 解决什么问题，与幻觉有什么关系？]]（待补充）
- [[对比问题#Memory 与 RAG 的作用和增强策略有什么区别？|Memory 与 RAG 的作用和增强策略有什么区别？]]（待补充）
