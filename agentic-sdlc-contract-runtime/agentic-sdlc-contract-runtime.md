# agentic-sdlc-contract-runtime（PSC）

[[main|返回知识主干]]

本 Tree 记录 [Agentic SDLC Contract-Driven Runtime（PSC）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime) 的实际工程架构、设计动机与机制取舍。关于项目的结论以当前代码和明确的历史案例为依据；设计初衷与已验证的工程效果分别表述。

## 问题目录

- [[agentic-sdlc-contract-runtime#为什么已有 Codex、Claude Code，还需要开发 PSC？|为什么已有 Codex、Claude Code，还需要开发 PSC？]]
- [[agentic-sdlc-contract-runtime#PSC 的 Supervisor 如何验收 Executor 的真实完成情况？|PSC 的 Supervisor 如何验收 Executor 的真实完成情况？]]
- [[agentic-sdlc-contract-runtime#Executor 中途失败后，PSC 如何恢复部分完成的任务并避免重复修改？|Executor 中途失败后，PSC 如何恢复部分完成的任务并避免重复修改？]]
- [[agentic-sdlc-contract-runtime#MCP 断连后，PSC 如何避免重复启动 Executor 和并发写入？|MCP 断连后，PSC 如何避免重复启动 Executor 和并发写入？]]
- [[agentic-sdlc-contract-runtime#远程 Executor 状态未知时，如何兼顾安全与任务恢复？|远程 Executor 状态未知时，如何兼顾安全与任务恢复？]]

## 实际实现流程架构

![[psc-actual-architecture.svg]]

这张图依据 PSC 仓库 `main` 分支提交 [`c21dff887222`](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/commit/c21dff887222c00786f4e9de35af6a312de24b8b) 的代码与运行时约定绘制，覆盖 Contract 导入、MCP 调度、Preflight、Executor 执行、Supervisor 验收、重试与持久化恢复。

**阅读边界：** Executor 返回 `completed` 仅代表执行进程结果；任务是否通过由 Supervisor 依据 Contract 验收条件和独立验证证据决定。Runtime 负责调度、隔离、范围约束、证据保存及状态提交，不能用执行器自述代替验收。

---

## 为什么已有 Codex、Claude Code，还需要开发 PSC？

### 原始设计初衷：把高成本规划与重复开发执行分开

开发 PSC 并不是因为 Codex、Claude Code 缺乏编码能力。最初的目标是：**让高智能模型负责需求理解和任务规划，让成本相对较低的模型承担持续监督与具体开发，减少人反复拆任务、追进度和逐轮交互的负担。**

为此，我把研发过程划分为三个职责：

- **Planner** 与人对齐需求，将较大的开发目标拆成具有范围、依赖关系和验收标准的版本化 **Contract**。
- **Supervisor** 依据 Contract 管理任务顺序，派发 Executor，检查实际交付并决定通过、返工或升级处理。
- **Executor** 专注于当前任务的代码实现和测试，不承担对自己最终验收的权力。

这样，人主要参与目标与关键约束的确定，以及必要的异常决策；日常开发迭代则由工作流推进。**节省高智能模型 Token 是设计动机，不等于已经证明 PSC 的总调用成本一定更低**：Preflight、独立复核和失败恢复本身也有开销。

### 工程设计的深化：让长任务可控、可恢复、可验证

随着实际使用，我发现 Coding Agent **能够生成代码，不等于能够可靠地交付一整个长周期软件开发任务**。PSC 因而从角色分工，逐步演化为带有明确执行约束和持久化状态的 Runtime，重点处理三个问题：

1. **需求偏移与自我验收。** Agent 可能修改了代码并宣称完成，却遗漏验收条件或触及不相关文件。PSC 用不可变 Contract 明确需求、任务边界和验收标准；Runtime 记录代码变更并检查作用域，Supervisor 再结合代码差异、必要测试和实际结果独立判断是否 PASS，而不是直接采信 Executor 的 `completed`。
2. **中断后的执行连续性。** 超时、会话中断或重新派发后，新执行器可能不清楚前一次做到了哪里。PSC 把任务状态、执行记录、失败尝试、交接信息和文件指纹持久化；后续尝试读取与当前任务兼容的历史证据，核查源码是否漂移，避免单纯依赖聊天历史续做。
3. **异常分类与重试决策。** 曾遇到 Windows 命令行过长触发 `WinError 206`：Executor 实际未启动，旧流程却消耗了任务重试额度。这暴露出“启动失败、执行异常、实现质量不合格”不能混为一谈。现在 PSC 区分前置阻断、异常重试与质量返工，维护独立预算；如果进程异常但产物已被独立验证合格，也可以直接 PASS，而不机械重试。

**因此，PSC 不打算替代 Coding Agent 的代码生成能力，而是把它们当作可替换的执行单元，补齐跨任务的契约约束、状态管理、独立验收和异常恢复。** 最初关注的是降低使用高智能模型和人工反复交互的成本；最终形成的工程价值，则是让复杂开发过程具备更清晰的控制边界和可追溯证据。

相关实现：[Contract 与工作流](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)、[MCP 调度与重试](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)、[Supervisor 状态提交](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/supervisor_runtime.py)。

---

## PSC 的 Supervisor 如何验收 Executor 的真实完成情况？

**核心原则：Executor 的完成声明只是线索，不是验收结论。** PSC 把实际执行、证据采集与最终验收分离，让 Supervisor 基于 Contract 和可检查的代码事实作出判断，而非仅让两个模型互相评价。

![[psc-supervisor-acceptance-flow.svg]]

整个验收过程可概括为三步：

1. **Runtime 采集客观证据。** Executor 返回结构化 Completion，解析后保存为 `plan.md`、`coding.md`；同时 Runtime 保留真实执行日志，在执行前后调用 `_git_snapshot()`，计算 `changed_paths`，再由 `_scope_violations()` 对照 Contract 的 Allowed / Forbidden Scope 检查越界修改。Executor 自称修改了哪些文件，不能覆盖实际快照结果。参考：[执行器及证据采集实现](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/invoke_executor.py)。
2. **Supervisor 独立核验。** 重新读取 Contract 的验收条件（AC），结合 Git Diff、代码实现与必要的实际测试判断完成质量。例如 FastAPI 接口不仅检查路由是否存在，还要核对请求与响应、非法参数及异常处理；关键 AC 应能对应到具体代码或验证证据。**这些测试与语义判断由 Supervisor 负责，不是 Runtime 自动运行全部测试。**
3. **作出并提交验收决策。** 满足 AC、证据充分且无阻断时，提交 `pass`，生成 `review.md`、`result.md` 并推进工作流；若存在真实功能缺陷，提交 `quality_rework`，向 Executor 反馈具体问题；无法继续或需要变更契约时，使用 `blocked` / `waiting_planner`。正式接口 `psc_commit_supervisor_transition()` 校验任务、Contract 版本、可选状态 SHA 及部分安全阻断，并持久化决策。参考：[Supervisor 状态提交](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/supervisor_runtime.py)。

**异常但可验收的情况：** Executor 进程或输出格式异常，不代表产品一定失败。如果 Supervisor 已独立验证交付满足 AC，且没有越界或硬阻断，可以保留真实异常记录并直接 PASS，避免无意义的重复开发。反之，异常且尚未完成或无法验证时，再按 `abnormal_retry` 重新派发；它是下一次派发的重试类型，**不是** Supervisor 状态提交的 decision。

**当前技术边界：** Runtime 的确定性检查降低了误判风险，但尚无能够自动证明所有 AC 均满足的通用验证器；复杂功能仍需要 Supervisor 判断，因此不能宣称“模型审核绝对可靠”。后续可逐步将可执行的验收条款结构化，增加自动测试与证据校验。参考：[MCP 运行时接口](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)。

---

## Executor 中途失败后，PSC 如何恢复部分完成的任务并避免重复修改？

**核心思路：保留代码现场，将失败尝试转化为可验证的恢复上下文，而不是重新从零开发。** 例如任务要求修改五个文件，Executor 完成其中三个后因 API 超时退出，PSC 不会把这次进程失败直接等同于全部代码失败。

1. **归档本轮执行现场。** 对于已启动、并已返回执行结果及日志的尝试，Runtime 即使收到失败结果，也会在 `developing/artifacts/T-###/execution-memory/attempts/` 写入不可变回执：执行状态与失败原因、实际 `changed_paths` 中可记录文件的 SHA-256、已有的实现摘要、决策、失败路径和后续步骤。没有有效 Completion 时仍保存能取得的失败事实，但不虚构实现进度。参考：[Task Execution Memory](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/task_execution_memory.py)、[Executor 调用及归档](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/invoke_executor.py)。
2. **Supervisor 决定是否重派。** 先以 Contract 和实际代码、测试判断任务是否已完成：若成果已被独立验证且无硬阻断，即使进程异常也可 PASS；若实现不完整或尚未验证，才使用 `abnormal_retry` 重派。这个重试类别与有明确质量缺陷时的 `quality_rework` 分开管理。参考：[运行时协议](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/references/runtime-protocol.md)。
3. **新 Executor 从现有代码继续。** 重新派发时注入当前 Task、Contract、上一轮 Supervisor Review 和兼容的历史 Execution Memory。历史记录必须匹配任务 ID、Contract 版本、任务正文与执行包；读取时会重新比较所记录文件的 SHA-256，标示文件是否已变化。 `abnormal_retry` 的执行指令要求先检查当前 Git Diff、任务产物和失败证据，保留有效修改，优先补完剩余部分。参考：[恢复上下文拼装](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/invoke_executor.py)。

**边界与改进方向：** 历史 Execution Memory 是有界的、未经 Supervisor 验收的执行记录，不是可信的“已完成文件清单”；SHA-256 只能检测相关文件内容是否与归档时一致，不能证明功能正确，更不能百分之百避免重复编辑。当前主要依靠重派提示、代码核验和 Supervisor 复核降低破坏风险；若进一步增强，可考虑为已验收的子目标建立显式进度标记、恢复前基线检查以及细粒度的幂等修改与回滚机制。

---

## MCP 断连后，PSC 如何避免重复启动 Executor 和并发写入？

**核心原则：MCP 连接断开不等于 Executor 进程已经终止。** 如果 Supervisor 只根据通信异常重试，就可能让两个执行器同时修改同一仓库。因此，同一工作流的执行互斥必须由 Runtime 的确定性机制保证，不能只依赖 Supervisor 的 Prompt。

### 已实现：工作流级文件锁与进度记录

正常调度通过  MCP 工具调用 Executor ，调用前会获取工作流的一个内置操作系统管理文件锁，锁持有范围覆盖 Preflight、Executor 运行与调用结果处理。锁属于操作系统级跨进程互斥，而不是 Python 内存标志。如果另一调用占锁，最多等待约 10 秒，仍无法获取就抛出 `TimeoutError`。因此，只要原 MCP Server 仍正常运行并持锁，后续同工作流派发不能并发进入执行段。参考：[MCP 调度](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)、[文件锁实现](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/workflow_registry.py)。

此外，skill已经实现了持久化 `run_id`、任务、运行状态、最近活动及心跳时间，便于连接异常后的诊断。参考：[执行进度采集](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/executor_progress.py)。

### 尚未完整解决：服务崩溃后的孤儿执行器

| 故障场景 | 当前保障与边界 |
| --- | --- |
| Supervisor 客户端断连，MCP Server 仍在执行 | 文件锁持续由 Server 持有；同工作流的新派发受阻 |
| MCP Server 崩溃，Executor 子进程继续运行 | 文件锁可能随 Server 退出而释放，尚不能可靠识别和阻止孤儿进程继续写入 |
| Executor 主进程退出，但派生进程仍在写入 | 尚无完整的进程树级生命周期约束；现有超时处理主要终止所启动的直接进程 |
| 两个 PSC 工作流同时使用同一代码仓库 | 工作流级锁不等于仓库级互斥 |

### 后续设计：先确认旧执行者失效，再允许新执行者写入

可为每次派发建立持久化执行身份与租约，记录 Task / Run ID、PID、工作区和运行状态；重连后结合操作系统进程信息等核验旧执行器是否仍存活。**无法确认旧执行器已经停止时应阻断重试（fail closed）**，而不是仅靠 PID 或心跳超时推断其死亡。

或者使用git worktree隔离不同派发的工作区，避免新旧执行者同时写入。

---

## 远程 Executor 状态未知时，如何兼顾安全与任务恢复？

**判断：远程服务器不可达，不等于 Executor 已退出；但调度器也不能无限等待。** 应把“旧执行是否仍在运行”与“是否继续安排新工作”分开处理，优先保证共享代码仓库不会被两个身份不明的执行器同时修改。

![[psc-remote-executor-unreachable-flow.svg]]

1. **有限时间内恢复连接。** MCP 断连后，在明确的重试次数和时间窗口内尝试重连、查询旧 Executor 状态；若可确认，则依据实际运行情况继续监控或进入独立验收。
2. **无法确认时停止自动重派。** 若持续不可达，将执行结果标记为概念上的 `UNKNOWN`（未知，而非 `FAILED`），把任务调度暂停为阻断状态，保存 Task / Run ID、最后心跳与已知代码状态。有限探测结束后释放调度资源，等待外部条件恢复或人工决策。
3. **紧急恢复只能隔离重算。** 若业务确实不能等待，可在另一台服务器上基于最后可信 Git Commit 创建**独立 Git Worktree 或容器工作区**，启动新的 Executor。旧、新执行器只在各自工作区写入，结果不能直接进入主分支；必须经 Contract 验收、执行身份与版本检查及**唯一受控提交门**，防止两个结果同时被接受。
4. **旧服务器恢复后对账。** 重新读取旧进程状态、代码差异和日志，决定终止、保留或审查旧结果。即使旧 Executor 最后完成，也不能跳过验收或覆盖已被接受的结果。

**核心工程取舍：** 当旧执行器状态未知时，对**同一共享工作区**必须阻断重派；但如果采用隔离执行，可以允许重新计算，把“任务执行可用性”和“最终结果一致性”交给不同机制保障。PID 或心跳超时不足以证明旧进程死亡，最终还需要进程生命周期管理及防止过期执行身份写入的 fencing 约束。

**现状与边界：** PSC 目前已实现本地 MCP 调度、工作流级文件锁和进度持久化，**尚未实现完整的远程执行租约、跨服务器 Worktree 隔离与受控合并**。图中的 `UNKNOWN` 是建议引入的执行状态语义，并非当前 PSC Runtime 已有的状态枚举；整套远程故障恢复流程属于后续设计。可对照：[MCP 调度实现](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)、[进度记录](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/executor_progress.py)及[运行时协议](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/references/runtime-protocol.md)。
