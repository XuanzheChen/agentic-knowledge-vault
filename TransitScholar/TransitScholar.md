# TransitScholar

[[main|返回知识主干]]

本 Tree 用于记录 [TransitScholar](https://github.com/XuanzheChen/transit-scholar) 科研 Agent 项目的实际架构、设计动机、代码机制与工程限制。相关通用原理可延伸阅读 [[Agent/Agent|Agent]]、[[Agent/Context/context|Context]]、[[Agent/Context/RAG/RAG|RAG]]、[[Agent/Context/Memory/Memory|Memory]] 和 [[backend/backend|后端开发]]。项目相关事实以**具体提交、实际代码和测试**为依据，避免将设计意图与已验证效果混同。

## 总体架构图

![[transitscholar-overview.svg]]

> 图示用于总体结构导航，描述论文知识层、服务层、Agent Core、上下文与记忆、运行时持久化及证据链之间的关系。它是概要示意，并不表示所有可选组件都已接入默认生产路径。后续写 Q&A 时，需逐项核实该界限。

## 子树

| 子树 | 内容 |
| --- | --- |
| [[TransitScholar/系统架构与服务层/系统架构与服务层|系统架构与服务层]] | 前端、FastAPI、Product Service、后台执行管理和数据持久化的调用边界 |
| [[TransitScholar/文献处理与知识构建/文献处理与知识构建|文献处理与知识构建]] | 论文身份、PDF 解析、Canonical Blocks、Chunking、Schema 与 Base Wiki 构建 |
| [[TransitScholar/知识检索与证据链/知识检索与证据链|知识检索与证据链]] | Schema、Wiki、RAG 混合检索以及 Query、Evidence、Claim 和来源约束 |
| [[TransitScholar/研究规划与会话编排/研究规划与会话编排|研究规划与会话编排]] | RunCoordinator、ResearchPlan、PlanItem、ResearchSession 和研究结果汇总 |
| [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行|Agent Loop 与角色执行]] | 多角色单 Agent、RoleRuntime、结构化 Prompt、角色切换、Action 校验与工具调用 |
| [[TransitScholar/上下文与记忆/上下文与记忆|上下文与记忆]] | Context Snapshot、RoleContext Projection、Working Memory、Episodic Memory、Agentic Wiki |
| [[TransitScholar/运行时状态与可靠性/运行时状态与可靠性|运行时状态与可靠性]] | Research State、Trace、Checkpoint、执行预算、暂停恢复、重试和测试 |

## 问题目录

- [[TransitScholar/TransitScholar#TransitScholar 要解决什么科研工作流问题，和普通论文问答 RAG 有什么不同？|TransitScholar 要解决什么科研工作流问题，和普通论文问答 RAG 有什么不同？]]（待补充）
- [[TransitScholar/TransitScholar#TransitScholar 从用户研究问题到最终回答的完整执行链路是什么？|TransitScholar 从用户研究问题到最终回答的完整执行链路是什么？]]（待补充）
- [[TransitScholar/TransitScholar#论文知识构建与 Agent Runtime 为什么采用两条相互独立又协作的主线？|论文知识构建与 Agent Runtime 为什么采用两条相互独立又协作的主线？]]（待补充）
- [[TransitScholar/TransitScholar#TransitScholar 的主要工程取舍、已实现边界与尚待验证的问题是什么？|TransitScholar 的主要工程取舍、已实现边界与尚待验证的问题是什么？]]（待补充）

---

## TransitScholar 要解决什么科研工作流问题，和普通论文问答 RAG 有什么不同？

> 待补充：本轮仅建立问题框架，后续依据 TransitScholar 仓库源码与真实执行链路撰写。

## TransitScholar 从用户研究问题到最终回答的完整执行链路是什么？

> 待补充：本轮仅建立问题框架，后续依据 TransitScholar 仓库源码与真实执行链路撰写。

## 论文知识构建与 Agent Runtime 为什么采用两条相互独立又协作的主线？

> 待补充：本轮仅建立问题框架，后续依据 TransitScholar 仓库源码与真实执行链路撰写。

## TransitScholar 的主要工程取舍、已实现边界与尚待验证的问题是什么？

> 待补充：本轮仅建立问题框架，后续依据 TransitScholar 仓库源码与真实执行链路撰写。
