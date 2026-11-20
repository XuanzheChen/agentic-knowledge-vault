# Agent Loop 与角色执行

[[TransitScholar/TransitScholar|返回上级：TransitScholar]] · [[main|返回知识主干]]

多角色单 Agent、RoleRuntime、结构化 Prompt、角色切换、Action 校验与工具调用。本子树按实际实现、设计动机与工程边界组织 Q&A；以下问题均是待核对与待撰写的知识叶子，**尚不构成已验证的答案**。

## 问题目录

- [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行#TransitScholar 为什么采用多角色单 Agent，而不是多个独立 Agent？|TransitScholar 为什么采用多角色单 Agent，而不是多个独立 Agent？]]（待补充）
- [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行#五个内置 Role 的职责、输入和输出契约分别是什么？|五个内置 Role 的职责、输入和输出契约分别是什么？]]（待补充）
- [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行#ResearchCoordinator 如何决定下一轮 Role，MainResearchRuntime 如何推进循环？|ResearchCoordinator 如何决定下一轮 Role，MainResearchRuntime 如何推进循环？]]（待补充）
- [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行#StructuredLLMRolePolicy 如何构造 Prompt 并处理模型结构化输出？|StructuredLLMRolePolicy 如何构造 Prompt 并处理模型结构化输出？]]（待补充）
- [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行#BuiltinRoleActionPlanner 如何将 LLM 决策转成可执行 Action？|BuiltinRoleActionPlanner 如何将 LLM 决策转成可执行 Action？]]（待补充）
- [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行#ActionValidator 与 ActionExecutor 如何验证角色权限和资源归属？|ActionValidator 与 ActionExecutor 如何验证角色权限和资源归属？]]（待补充）
- [[TransitScholar/Agent Loop 与角色执行/Agent Loop 与角色执行#LLM 输出异常、工具异常与预算耗尽分别怎样终止或重试？|LLM 输出异常、工具异常与预算耗尽分别怎样终止或重试？]]（待补充）

---

## TransitScholar 为什么采用多角色单 Agent，而不是多个独立 Agent？

> 待补充：依据 TransitScholar 实际代码、默认运行链路和必要测试核实后撰写；区分已实现功能、未接入能力及后续设计。

## 五个内置 Role 的职责、输入和输出契约分别是什么？

> 待补充：依据 TransitScholar 实际代码、默认运行链路和必要测试核实后撰写；区分已实现功能、未接入能力及后续设计。

## ResearchCoordinator 如何决定下一轮 Role，MainResearchRuntime 如何推进循环？

> 待补充：依据 TransitScholar 实际代码、默认运行链路和必要测试核实后撰写；区分已实现功能、未接入能力及后续设计。

## StructuredLLMRolePolicy 如何构造 Prompt 并处理模型结构化输出？

> 待补充：依据 TransitScholar 实际代码、默认运行链路和必要测试核实后撰写；区分已实现功能、未接入能力及后续设计。

## BuiltinRoleActionPlanner 如何将 LLM 决策转成可执行 Action？

> 待补充：依据 TransitScholar 实际代码、默认运行链路和必要测试核实后撰写；区分已实现功能、未接入能力及后续设计。

## ActionValidator 与 ActionExecutor 如何验证角色权限和资源归属？

> 待补充：依据 TransitScholar 实际代码、默认运行链路和必要测试核实后撰写；区分已实现功能、未接入能力及后续设计。

## LLM 输出异常、工具异常与预算耗尽分别怎样终止或重试？

> 待补充：依据 TransitScholar 实际代码、默认运行链路和必要测试核实后撰写；区分已实现功能、未接入能力及后续设计。

**源码核查入口：**[main_runtime.py](https://github.com/XuanzheChen/transit-scholar/blob/master/src/transit_scholar/layer3/runtime/main_runtime.py) · [role_runtime.py](https://github.com/XuanzheChen/transit-scholar/blob/master/src/transit_scholar/layer3/runtime/role_runtime.py) · [executor.py](https://github.com/XuanzheChen/transit-scholar/blob/master/src/transit_scholar/layer3/actions/executor.py) · [builtin.py](https://github.com/XuanzheChen/transit-scholar/blob/master/src/transit_scholar/layer3/roles/builtin.py)。
