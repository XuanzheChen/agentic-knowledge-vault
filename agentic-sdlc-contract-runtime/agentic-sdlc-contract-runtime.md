# agentic-sdlc-contract-runtime（PSC）

[[main|返回知识主干]]

本 Tree 记录 [Agentic SDLC Contract-Driven Runtime（PSC）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime) 的实际工程架构、设计动机与机制取舍。关于项目的结论以当前代码和明确的历史案例为依据；设计初衷与已验证的工程效果分别表述。

## 问题目录

- [[agentic-sdlc-contract-runtime#为什么已有 Codex、Claude Code，还需要开发 PSC？|为什么已有 Codex、Claude Code，还需要开发 PSC？]]
- [[agentic-sdlc-contract-runtime#PSC 的 Supervisor 如何验收 Executor 的真实完成情况？|PSC 的 Supervisor 如何验收 Executor 的真实完成情况？]]
- [[agentic-sdlc-contract-runtime#Executor 中途失败后，PSC 如何恢复部分完成的任务并避免重复修改？|Executor 中途失败后，PSC 如何恢复部分完成的任务并避免重复修改？]]
- [[agentic-sdlc-contract-runtime#MCP 断连后，PSC 如何避免重复启动 Executor 和并发写入？|MCP 断连后，PSC 如何避免重复启动 Executor 和并发写入？]]
- [[agentic-sdlc-contract-runtime#executor-dispatch.lock 会限制哪些调用，锁的真实粒度和异常边界是什么？|executor-dispatch.lock 会限制哪些调用，锁的真实粒度和异常边界是什么？]]
- [[agentic-sdlc-contract-runtime#远程 Executor 状态未知时，如何兼顾安全与任务恢复？|远程 Executor 状态未知时，如何兼顾安全与任务恢复？]]
- [[agentic-sdlc-contract-runtime#文件锁失效后，如何防止旧 Executor 继续写入与提交？|文件锁失效后，如何防止旧 Executor 继续写入与提交？]]
- [[agentic-sdlc-contract-runtime#PSC 为什么需要版本化 Contract，如何将需求转化为可执行任务？|PSC 为什么需要版本化 Contract，如何将需求转化为可执行任务？]]
- [[agentic-sdlc-contract-runtime#Contract 升级时，PSC 如何选择迁移策略并防止跨版本误验收？|Contract 升级时，PSC 如何选择迁移策略并防止跨版本误验收？]]
- [[agentic-sdlc-contract-runtime#Supervisor 基于过期 Contract 提交 PASS 时，Runtime 如何处理？|Supervisor 基于过期 Contract 提交 PASS 时，Runtime 如何处理？]]
- [[agentic-sdlc-contract-runtime#如何将 Contract V2 激活扩展为逐 Task 的可恢复迁移事务？|如何将 Contract V2 激活扩展为逐 Task 的可恢复迁移事务？]]
- [[agentic-sdlc-contract-runtime#Contract 激活崩溃时，如何保证版本与 Task 状态的事务原子性？|Contract 激活崩溃时，如何保证版本与 Task 状态的事务原子性？]]
- [[agentic-sdlc-contract-runtime#Planner 并发修改 Contract 时，如何保证 SQLite 保存的是同一份已校验快照？|Planner 并发修改 Contract 时，如何保证 SQLite 保存的是同一份已校验快照？]]
- [[agentic-sdlc-contract-runtime#Preflight 如何用 SHA-256 绑定证据，以及能否阻止过期检查后的派发？|Preflight 如何用 SHA-256 绑定证据，以及能否阻止过期检查后的派发？]]
- [[agentic-sdlc-contract-runtime#只读 Preflight 依赖 Prompt 还是程序权限，如何防止 pytest 等工具产生副作用？|只读 Preflight 依赖 Prompt 还是程序权限，如何防止 pytest 等工具产生副作用？]]
- [[agentic-sdlc-contract-runtime#WinError 206 如何定位与修复，启动传输失败为何不能扣 Executor 重试预算？|WinError 206 如何定位与修复，启动传输失败为何不能扣 Executor 重试预算？]]
- [[agentic-sdlc-contract-runtime#如何区分 PROCESS_STARTED、EXECUTOR_READY 与 TASK_STARTED？|如何区分 PROCESS_STARTED、EXECUTOR_READY 与 TASK_STARTED？]]
- [[agentic-sdlc-contract-runtime#Executor 失联后如何避免重复执行数据库迁移等外部副作用？|Executor 失联后如何避免重复执行数据库迁移等外部副作用？]]

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

## executor-dispatch.lock 会限制哪些调用，锁的真实粒度和异常边界是什么？

**结论：它是 PSC 的工作流级关键操作互斥锁，不是 Task 级锁，也不是把某个源代码文件锁成只读。** 同一个 PSC 项目下，原生 Executor 调度、Contract 激活、Supervisor 正式状态提交及若干恢复/关闭操作共享这一锁；它保护的是程序执行的临界区（Critical Section），而不是直接控制 Executor 或其他进程对代码文件的写权限。

### 锁文件、作用域与获取过程

锁路径为 `Path(project).resolve() / "runtime" / "executor-dispatch.lock"`。其中 `project` 是 PSC 工作流目录；`task_continuity.LOCK_NAME` 的常量值即 `executor-dispatch.lock`。因此：

- **同一个 Workflow，哪怕是不同 Task，也争用同一把锁。** T-001 与 T-002 即使修改互不相干的代码，也无法经由当前原生 Executor 派发路径同时执行。
- **不同 Workflow 使用不同的锁文件。** 即使它们都指向同一 Git 仓库，工作流锁也不会自动提供仓库级互斥。
- **锁粒度以 Workflow 为单位，而非整个 MCP Server。** 没有申请该锁的只读或辅助工具仍可运行，不能理解成“一个 MCP Server 每次只能调用一个工具”。

真正的互斥逻辑位于 `workflow_registry._locked(path)`。程序打开一个**保留在磁盘上的锁文件**（不通过删除文件释放锁），Windows 使用 `msvcrt.locking(..., LK_NBLCK, 1)` 锁定起始 1 字节，类 Unix 平台使用 `fcntl.flock(..., LOCK_EX | LOCK_NB)` 获取排他锁；两者都是操作系统级文件锁，而不是 Python 的线程锁。获取失败每隔约 **50 ms** 重试一次，最长约 **10 秒**，仍不能获取便抛出 `TimeoutError`。成功后在 `with` 范围内保持锁，在退出该范围时调用解锁操作；持锁过程可跨越不同 MCP 服务进程的调用。

参考：[工作流文件锁的实际实现（workflow_registry.py）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/workflow_registry.py)、[锁名与连续性常量（task_continuity.py）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/task_continuity.py)。

### 哪些调用会被这把锁串行化？

以下是源码中能够确认的**主要六类受保护操作**。它们共享的是同一工作流目录下同一锁文件，但持锁时长各不相同：

| 操作与入口 | 实际锁住的范围 | 工程目的 |
| --- | --- | --- |
| `psc_invoke_executor` → `_invoke_executor_impl` | 从进入核心派发实现、检查连续性与 Preflight，到 Executor 阻塞执行及结果处理结束 | 不允许同工作流同时派发多个 Executor |
| `activate_contract()` | Approved Contract 的选择、必要连续性迁移、Task 记录重建与 `workflow_state.json` 版本激活 | 不让执行过程和 Contract 生效版本同时改变 |
| `psc_commit_supervisor_transition` → `commit_supervisor_transition()` | 读取并校验版本/Task/状态 SHA，落地 Review、Result 和状态变更 | 不让 PASS/返工提交与执行、激活发生并发竞态 |
| `psc_recover_task_continuity` → `task_continuity.recover()` | 跨版本待完成任务的尝试/连续性账本恢复 | 避免恢复与新执行记账交错 |
| `resolve_retry_exhaustion()` | 重试耗尽后的预算重置、执行权接管等恢复决策 | 避免重试决策与执行过程交错 |
| `psc_close_workflow` → `close_workflow()` | 检查可关闭条件、持久化关闭标记及登记 | 不允许在执行或提交中途关闭同一工作流 |

另外，Supervisor 的正式提交使用**固定锁顺序**：先获取 `executor-dispatch.lock`，再获取 `supervisor-transition.lock`；关闭工作流也采用相同顺序。第二把锁进一步保护 Supervisor 状态提交，但不能把它理解为另一套独立的 Executor 派发权限。

这并不表示所有 MCP 工具都持锁。例如 `psc_supervisor_snapshot` 属于只读上下文查询，独立调用的 `psc_preflight_check` 也不通过 Executor 派发锁；`psc_ensure_executor_ready` 的健康/Smoke 检查亦不等同于进入核心派发临界区。尤其要区分：**独立 Preflight 不持此锁；在 `_invoke_executor_impl` 内执行的 Preflight 因为处于上层 `with` 中而受到锁保护。**

参考：[MCP 派发与工具注册（psc_mcp_server.py）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)、[Contract 激活和重试决策（psc_runtime.py）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)、[Supervisor 双锁与状态提交（supervisor_runtime.py）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/supervisor_runtime.py)、[任务连续性恢复（task_continuity.py）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/task_continuity.py)、[关闭工作流（workflow_registry.py）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/workflow_registry.py)。

### 为什么一次长任务会阻塞 Contract 激活或 PASS？

`psc_mcp_server.py` 通过装饰器 `_serialize_executor_dispatch` 给阻塞式 `_invoke_executor_impl` 包上 `with _locked(...)`。锁不是在“启动 Executor”之后马上释放，而是直到核心函数返回为止。因此，如果 A 的执行过程持续 30 分钟，期间 V2 激活或 Supervisor PASS 提交会尝试等待锁；约 10 秒仍拿不到便失败，而不是绕过锁更新状态。只有 **A 的执行路径退出、锁释放以后**，这些状态操作才可能继续进入自己的检查流程。

这项串行化是一种**保守的单工作流执行模型**：牺牲同一工作流内彼此独立 Task 的并发潜力，换取“执行、版本激活、验收提交”之间更清晰的顺序，减少状态文件与任务账本的竞态。它主要解决执行边界的顺序问题，不会让所有业务状态自动正确；Supervisor 提交 PASS 时仍需独立检查 Contract 版本、当前 Task 和可选的状态 SHA。

### 能保证什么，不能保证什么？

**能够保证的前提**是：操作走 PSC 的受控入口，竞争者位于能够正确遵守同一操作系统文件锁语义的环境，且持锁的管理进程持续存活。此时同一工作流的上述临界区不会并发进入。

**不能推出的保证**包括：

1. **不是代码仓库级锁。** 两个 PSC Workflow 指向同一仓库时可以各自成功持锁，仍可能修改相同文件。
2. **不是强制文件写入权限。** 绕过 PSC 的工具、人工编辑器或孤儿进程仍可直接修改仓库；执行锁不会自动拦截文件 I/O。
3. **不等于 Executor 进程存活证明。** 如果持锁的 MCP Server 崩溃，操作系统可能释放锁，但它启动的 Executor 子进程仍在运行；后继派发有可能获得新锁并与旧进程并发写入。
4. **不是跨服务器的可靠分布式执行权协议。** 共享网络文件系统的锁语义依赖部署环境；当前没有以租约、Fencing Token、受控写入或独立工作区实现端到端的分布式单写入者保证。

因此，**“锁被成功获取”只能说明当前受控入口没有其他活跃持锁者，不能证明不存在旧 Executor 或其他代码写入者。** 若未来要支持多个 Task 并行，可在独立工作区和仓库级提交控制的前提下细化锁粒度，并对共享工作流状态继续使用串行化或 CAS；这些都属于后续设计，不是当前已实现的保障。

关联：[[agentic-sdlc-contract-runtime#MCP 断连后，PSC 如何避免重复启动 Executor 和并发写入？|MCP 断连后的重复派发]]、[[agentic-sdlc-contract-runtime#文件锁失效后，如何防止旧 Executor 继续写入与提交？|孤儿执行器与执行权失效]]。

**复习时可记住：锁的是 Workflow 的关键操作临界区，不是 Task、MCP 连接、Executor 进程或 Git 仓库；锁管受控调用的顺序，不管进程异常后的所有文件写入。**

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

---

## 文件锁失效后，如何防止旧 Executor 继续写入与提交？

**文件锁只能约束正常调度，不能证明失去锁的旧进程已经停止。** 例如管理进程崩溃后，Executor A 可能仍在写文件，Executor B 却已获取新锁。要解决这个问题，需要三层保障：

![[psc-q8-fencing-layered-architecture.svg]]

1. **调度控制层——谁可以开始？** 现有 PSC 使用操作系统文件锁 `executor-dispatch.lock` 防止同工作流正常并发派发；后续可加入单调递增的执行代际（Fencing Token），明确当前有效执行者。
2. **执行隔离层——谁能修改哪里？** 每次执行分配独立 Git Worktree / 容器，并配合操作系统文件权限或沙箱，使 A 即使继续运行，也无法修改 B 或正式工作区。**只有 Worktree 路径隔离、没有写入权限隔离，并不够。**
3. **结果提交层——谁的结果能生效？** Executor 不能直接更新正式分支；受控提交模块原子检查 Task / Run 身份、当前代际、Git 基线和 Contract 验收结果。A 的旧 Token 即使携带正确代码，也必须被拒绝。

**现状与边界：** PSC 已有文件锁、`execution_owner`、`expected_state_sha256` 与执行文件指纹，但它们不能直接撤销旧进程的文件写权限。**独立工作区、强制写入隔离、Fencing Token 和原子提交门仍是后续设计。** 对尚未隔离、仍拥有共享目录写权限的旧任务，应先阻断接管，确认旧进程已停止或其权限已被撤销，再允许 B 在共享目录执行。

一句话概括：**锁管启动，隔离管写入，Fencing + 受控提交管结果生效。** 参考：[MCP 调度](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)、[文件锁](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/workflow_registry.py)及[Supervisor 状态提交](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/supervisor_runtime.py)。

---

## PSC 为什么需要版本化 Contract，如何将需求转化为可执行任务？

**Contract 的价值不是比 TODO List 写得更详细，而是将需求、实现边界和验收依据变成可持久化、可校验、可执行的协议。** 普通 Prompt 主要靠模型理解；PSC 则让 Runtime 也能够读取并执行其中一部分约束。

以“给 FastAPI 增加 JWT 认证”为例，Planner 先与用户明确登录、Token 校验与权限规则，再形成 Draft Contract，交由人审查。Contract 保存在独立的 `contract/vN/` 中，包含六个文件：

| 文件 | 职责及本例内容 |
| --- | --- |
| `requirements.md` | 稳定需求 ID（`REQ-###`）：登录、鉴权、权限控制 |
| `acceptance.md` | 验收 ID（`AC-###`）：错误密码返回 401、过期 Token 被拒绝、权限不足返回 403 |
| `tasks.md` | `T-###` 任务、REQ/AC 引用、依赖、Allowed/Forbidden Scope、必要验证 |
| `constraints.md` | 全局安全与兼容约束，如不能泄漏密钥 |
| `implementation.md` | 架构建议，不等同于必须采用的唯一实现 |
| `metadata.json` | 版本、状态、来源及工作流变更策略 |

例如可以把登录实现、Token 验证、受保护路由与权限测试划分为相互依赖的 Task。**这只是示例拆解，不代表 PSC 为 JWT 自动生成固定模板。**

Planner 导出的 Bundle 先由 Runtime 校验：六文件结构、ID 唯一性及引用、依赖无环、任务必填声明、需求与验收覆盖关系等；不符合要求就拒绝或升级给 Planner，不能直接拿去执行。通过审查的 Approved Contract 以不可变版本保存。参考：[Contract 校验与导入](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)。

执行时，Supervisor 按当前有效 Contract 选择任务；Runtime 为 Executor 生成只含当前任务相关 REQ、AC、实现建议及全局约束的 **Task-Scoped Contract Packet**。Executor 的实际修改由 Git 快照采集并做 Scope 检查，最终由 Supervisor 对照 AC 与测试证据独立验收。参考：[任务上下文与文件范围检查](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/invoke_executor.py)。

**工程边界：** 结构与引用校验不能证明 JWT 安全方案在语义上正确；目前的 Scope 检查主要是**执行后检测越界**，不是文件系统级的实时写入隔离。Contract 真正区别于 TODO 的，是其**稳定身份、可检查约束、明确验收、不可变版本与运行时状态绑定**，而不是名称本身。

---

## Contract 升级时，PSC 如何选择迁移策略并防止跨版本误验收？

**Contract 变更的核心问题，是确定“新版本应继承哪些旧成果，以及从哪里重新承担验收责任”。** PSC 不默认全部重做，也不自动相信旧任务仍然有效，而是通过 `activate_contract()` 支持的三种显式策略，让 Planner 与用户决定变更影响范围，再由 Runtime 执行确定性的状态迁移。

### 三种策略：运行时行为与设计取舍

| 策略 | 源码实际行为 | 设计理念与适用场景 |
| --- | --- | --- |
| `restart: all` | 重建新版本任务记录，清空 `last_completed_task`，从任务序列起点重新推进 | **正确性优先**：需求或架构大范围改变，无法安全继承旧验收成果时，宁愿付出重做成本 |
| `restart: pending_only` | 保留已完成边界；校验跨版本 Task 身份与完成前缀，并把兼容的未完成任务重试记录迁移到新版本 | **连续性优先**：主要调整执行计划、实现说明或验证方式，任务身份及验收责任仍应连续；避免重复开发和丢失恢复上下文 |
| `invalidate_from_task: T-006` | 将当前任务设为 `T-006`，将 `last_completed_task` 设为其前一任务（此例为 `T-005`） | **精准失效**：明确知道变更从哪个 Task 开始影响正确性，保留此前验收边界，从指定任务按新版 Contract 重验收 |

这三种策略都不会自动删除或回滚产品代码。所谓“重做”或“失效”，首先是**工作流验收资格的调整**，旧代码是否可复用仍需根据新 Contract 独立判断。特别是 `pending_only` 的连续性校验依据 Task 身份字段（如目标、REQ/AC 引用、依赖和禁止范围）及来源哈希，**不等于能自动理解验收文本的语义是否改变**；因此不能拿它代替 Planner 对影响范围的判断。参考：[版本激活逻辑](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)、[任务连续性约束](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/task_continuity.py)。

### V1 → V2：10 个 Task 中修改 T-006～T-008

![[psc-contract-lifecycle-v1-v2.svg]]

首先让 Planner 编制并审批 V2，明确 `workflow_policy.invalidate_from_task: T-006`。**导入 V2 不等于激活 V2**：现有工作流的生效版本由 `workflow_state.json.contract_version` 记录，只有正式激活才更新。

激活与 Executor 派发、Supervisor 状态提交共用工作流执行锁。正常本地运行时，正在执行 V1 的 T-006 会阻止并发激活；应先等待本轮结束，或者在锁超时时停止激活尝试，而不是直接让 V2 Executor 写同一工作区。完成激活后，V1 的 T-001～T-005 保留完成边界，T-006 起重新按 V2 检查与开发，T-007、T-008 使用更新后的 AC；既有代码和历史证据继续保留，但**V1 的通过记录不能自动算作 V2 的通过**。

正式验收时，Runtime 会检查当前 Task、有效 Contract 版本及可选的 `expected_state_sha256`：工作流已切换 V2 后，拿 V1 Contract 提交 PASS 将被拒绝；基于过时状态快照的提交也可被拒绝。参考：[Supervisor 状态提交](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/supervisor_runtime.py)。

**仍然存在的边界：** 当前 PASS 尚未强制绑定同版本、同轮次的 Executor Invocation ID 和验收证据哈希；如果 Supervisor 用 V2 身份提交，却错误沿用 V1 证据，Runtime 不一定能自动识别。后续可将 Contract SHA、Task SHA、执行轮次和验证证据一起绑定，使**旧代码可以复用，但必须重新取得新版验收资格**。

**总结：** 三种激活策略体现不同的工程取舍：`all` 选择全面重新确认，`pending_only` 选择严格条件下的连续性，`invalidate_from_task` 选择显式风险边界；确定性 Runtime 负责落实迁移与版本检查，Planner 和用户负责判断变更究竟影响了哪些需求。

---

## Supervisor 基于过期 Contract 提交 PASS 时，Runtime 如何处理？

这是典型的 **TOCTOU（检查与提交之间状态发生变化）** 问题：Supervisor 按 V1 完成了 T-006 的 Code Review，但正式提交 PASS 前，Planner 已经激活 V2。**Review 只是验收判断，不能直接修改工作流状态；最终由 Runtime 按提交时的权威状态决定是否允许 PASS。**

![[psc-q12-stale-pass-guards.svg]]

PSC 现有三层保护：

1. **Contract 激活联动状态机。** `activate_contract()` 根据新版本的 `workflow_policy` 重建任务边界。若使用 `invalidate_from_task: T-006`，V2 激活后更新 `workflow_state.json`：`contract_version=2`、`current_task=T-006`、`last_completed_task=T-005`。激活不仅更换文档，也是一项持久化工作流状态变更。
2. **互斥保护状态转换。** Contract 激活和 Supervisor 提交均获取同一工作流的 `executor-dispatch.lock`，在正常本地运行时串行执行；不能一边切换生效版本，一边完成旧版 PASS 提交。
3. **提交时重新校验。** `commit_supervisor_transition()` 会读取当前状态，检查**可选的** `expected_state_sha256`、提交的 Contract 版本及当前 Task。如果 Supervisor 携带旧状态 SHA，拒绝并报 `workflow_state_conflict`；如果省略 SHA 但仍使用 V1 Contract，则因 `Contract version mismatch` 拒绝。两者都不会把 T-006 标记为 PASS 或推进到 T-007。

**尚未完全解决：** Runtime 校验的是**提交声明与当前状态是否匹配**，还不能严格溯源 Review 具体依据哪个版本生成。假如旧 V1 Review 被错误地当成 V2 验收证据，且以有效 V2 身份提交，现有检查未必能发现。后续需要将 Review 与 Contract SHA、Task SHA 及代码快照等证据绑定。参考：[Contract 激活](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)、[Supervisor 状态提交](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/supervisor_runtime.py)。

**总结：PSC 的核心做法是把 Supervisor 的验收判断和 Runtime 的状态提交分离。** 即使 Supervisor 有权提交 PASS，也不能绕过 Runtime 对当前 Contract、Task 边界和状态版本的检查。**Review 可以基于过期状态产生，但过期的状态转换会被拒绝；Review 内容本身的版本溯源仍需更强的证据绑定机制。**

---

## 如何将 Contract V2 激活扩展为逐 Task 的可恢复迁移事务？

**目标：把 V2 激活由“按一个策略切换任务边界”，扩展为“逐 Task 明确迁移意图、经过独立校验与必要批准、可从崩溃中恢复的状态迁移事务”。** Planner 提案不等于 Runtime 的授权，迁移计划也不能直接覆盖 V1。

**现有基础：** PSC 已将 Contract 存为不可变的 `contract/vN/`，`activate_contract()` 支持 `restart: all`、`restart: pending_only`、`invalidate_from_task: T-###` 三种策略，并以工作流级 `executor-dispatch.lock` 串行化激活。`pending_only` 还会迁移带有来源版本、Task 身份和 Contract 哈希的兼容重试状态。**但现有机制以顺序任务边界为主，尚没有独立的逐 Task Migration Plan、审批绑定和完整激活事务。** 参考：[当前激活实现](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)、[连续性迁移](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/task_continuity.py)。

![[psc-q18-migration-plan-six-steps.svg]]

### 六步扩展设计

1. **接收并校验计划。** Planner 提交 Approved V2 与结构化 Migration Plan，绑定源/目标 Contract 的版本及 SHA，为全部相关 Task 明确声明保留 `PASS`、重新执行、重新验收、新增或删除。版本、Task ID、声明覆盖或一致性不符则**拒绝激活**。
2. **独立检查迁移安全。** Runtime 对比 AC、Task 身份与依赖关系：验收标准改变、上游任务失效或证据无法证明兼容时，不允许直接继承旧 `PASS`。Planner 解释业务影响，Runtime 强制确定性规则；语义风险需重新验证，而非自动判断“没影响”。
3. **核验用户批准。** 删除已验收 Task、改动关键 AC、继承有风险的历史 PASS 等操作应列为需授权事项。批准记录绑定规范化 Migration Plan 的哈希；若缺失、过期或计划被修改，**拒绝激活**。
4. **获取执行锁并重读状态。** 沿用当前工作流级执行锁，进入提交阶段重新确认有效版本仍为 V1、状态 SHA 未变，且没有无法确认已终止的旧 Executor。遇并发更新、状态漂移或未隔离的存活执行器，按 **fail closed** 拒绝本轮切换。
5. **构造完整 V2 目标状态。** 按计划生成新 Task 状态表，例如 T-001/T-002 继承 PASS，T-003 重新执行，T-005/T-008 重新验收，T-018 新增。保留 V1 的 Review、执行与重试证据；**只生成和校验暂存状态，不直接覆盖旧状态**。
6. **事务化提交与崩溃恢复。** 暂存目标状态、Task 记录、重试账本和迁移审计，写入 `PREPARED` 等事务日志；全部校验成功后再通过**单一权威生效点**原子切换到 V2，并记录 `COMMITTED`。准备失败时 V1 继续生效；切换途中崩溃时，根据日志和当前权威指针幂等补全或恢复，不能依靠猜测重跑迁移。

**拒绝条件与工程边界：** 计划结构不合法、历史 PASS 继承规则不满足、缺少有效批准、版本/状态冲突、旧执行器存活性不明或目标状态准备失败，都不能发布 V2。多文件写入本身**不是**一个原子事务：必须先准备一致的暂存数据，再切换单一权威状态，并保证恢复流程可重复执行。当前 PSC 尚未完整实现这六步，也尚不具备天然的孤儿进程隔离保障。

**总结：真正需要扩展的不只是 Migration Plan JSON，而是让计划校验、用户授权、任务状态迁移与 Contract 激活共同形成可审计、可拒绝、可恢复的事务边界。**

---

## Contract 激活崩溃时，如何保证版本与 Task 状态的事务原子性？

**核心判断：文件锁解决并发进入，`os.replace()` 解决单文件原子替换，但两者加起来也不能保证多文件迁移是一个事务。** 如果 V2 版本指针已切换，而 T-005、T-008 仍继承 V1 的 PASS，就可能发生跨版本错误验收。要做到“全部生效或全部不生效”，必须把 **Contract 版本、完整 Task 状态和迁移记录** 置于同一个权威提交边界。

### PSC 当前实现：有局部保护，尚无完整事务

`activate_contract()` 持有工作流级 `executor-dispatch.lock`，验证新的 Approved Contract 后，针对 `pending_only` 先执行带来源哈希的连续性账本迁移；随后 `_rebuild_task_records()` **删除并重建** `developing/tasks/T-*.md`，最后才更新 `workflow_state.json` 中的有效版本、`current_task`、`last_completed_task` 等字段。

`dump_json()` 通过临时文件和 `os.replace()` 更新单个 JSON 文件；若在任务文件重建后、状态版本更新前崩溃，就会产生**V2 任务文件 + V1 工作流状态**的不一致。重试连续性账本提供局部幂等检查，但不等于整个激活具有事务性。参考：[激活与文件持久化](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)、[连续性账本](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/task_continuity.py)。

**题目假设的 T-005、T-008 独立 PASS/PENDING 行，目前也尚未完整实现**：PSC 主要使用 `last_completed_task` / `current_task` 表达顺序任务边界。离散 Task 状态迁移属于进一步扩展。

### 两种可落地的事务方案

| 方案 | 单一提交点 | 实施要点 |
| --- | --- | --- |
| **继续使用文件系统** | 原子替换 `active_snapshot.json` 指针 | 先构建不可变的 `snapshots/v2/`，完整包含 Contract 版本、所有 Task 状态、任务视图与迁移 ID；校验并确保暂存内容持久化后，才切换唯一权威指针 |
| **改用 SQLite（优先考虑）** | 数据库事务 `COMMIT` | 在一个 `BEGIN IMMEDIATE` 事务内核验 V1、写入 V2 的**完整** Task 状态、迁移审计记录，再更新唯一有效 Contract 版本；任何异常则 `ROLLBACK` |

文件方案的关键约束是：**执行器、Supervisor 和恢复器必须全部通过同一权威快照读取状态**。如果某模块仍直接读取被提前覆盖的 `developing/tasks/`，单独原子替换 `workflow_state.json` 并不能解决问题。指针和快照应位于可靠的同一持久化域，使用同文件系统的 `os.replace()`，必要时进行文件及目录 `fsync`，以应对断电故障。

SQLite 方案可将 `migration_id` 设为唯一键，按 `(project_id, contract_version, task_id)` 存储 Task 状态，**保留 V1 历史记录而非覆盖**。事务中使用条件更新并检查实际修改行数，防止版本漂移；数据库之外的 Contract 文件需事先准备并验证。SQLite 事务不会自动回滚对产品代码仓库的修改，也不替代执行器生命周期隔离。

### 重启后如何判断迁移是否完成？

| 崩溃时机 | 恢复时权威状态 | 处理 |
| --- | --- | --- |
| 开始准备前，或 `COMMIT` 前任意一步 | V1（旧快照 / 未提交事务） | 继续 V1；清理或忽略未生效暂存数据 |
| `COMMIT` 成功后，响应尚未返回 | 完整 V2，存在对应 `migration_id` | 返回 `already_activated`，**不得重复重置 Task** |
| 权威指针损坏、快照缺失或迁移账本不一致 | 无法确认 | **阻断调度**，进入明确的恢复/人工介入流程 |

重启时应以**权威提交结果**为准，不以“是否收到成功响应”或普通日志是否写了成功来猜测：SQLite 查有效版本及迁移 ID；文件方案查当前快照指针并校验所指向的不可变快照。采用事务日志时，也必须与这个唯一提交点保持可判定、可幂等的恢复关系。

**面试收尾：** PSC 已具备执行锁、单文件原子替换和部分迁移幂等保障，但尚无覆盖 Contract 激活全过程的多文件事务。下一步可以优先将权威状态集中到 SQLite；若沿用文件架构，则采用**不可变快照 + 单一原子生效指针**。原则始终是：**先准备完整 V2，再一次性发布；提交前崩溃保留 V1，提交后崩溃恢复完整 V2，状态不可验证时拒绝继续执行。**

---

## Planner 并发修改 Contract 时，如何保证 SQLite 保存的是同一份已校验快照？

**核心问题：SQLite 只能保证数据库内部的事务原子性，不能保证从多个正在编辑的 Markdown 文件中读到同一版本。** 如果校验用的是旧 `tasks.md`，入库时又重新读取了 Planner 刚修改的文件，即使事务成功，保存的内容与 Hash 仍可能不一致。这是跨文件读取的 TOCTOU 问题。

### 扩展方案：Git Commit → 内存快照 → SQLite 事务

1. **固定数据来源。** Planner 可以持续编辑工作区，但每次提交可供激活的 Contract，都必须先将六个规范文件作为一个 Git Commit 发布，并把**确定的 Commit SHA** 交给 Runtime。Runtime 依据该 Commit 的 Tree/Blob 读取六个文件，**不再读取可变工作区**；后续编辑不会改变所选快照。Git Commit 负责锁定来源内容，并不自动证明这份 Contract 在业务上合理。
2. **只校验一次内存事实。** Runtime 将该 Commit 的六份原始文件内容一次性读取为不可变的内存数据，分别计算文件 SHA-256 与整体 Contract Hash；在这**同一组字节**上完成格式、REQ/AC/T 引用、依赖无环和验收覆盖校验。失败则拒绝激活。校验后不重新读取源文件，也不重新生成待存储内容。
3. **同一事务保存并生效。** 直接使用已校验的内存字节及对应 Hash，在一个 SQLite 事务中写入完整 Contract 快照、Commit SHA、Task 目标状态、迁移记录，并更新生效版本；所有写入成功才 `COMMIT`。提交前失败则保留 V1；成功后数据库中的权威 V2 内容与其 Hash 必然对应同一份已校验快照。
4. **重启幂等检查。** 依据数据库中已提交的有效版本、Commit SHA 和迁移 ID 判断 V2 是否生效：已经提交则不重复迁移，未提交则继续 V1；若记录损坏或快照校验失败，则阻断调度。

**分工与边界：** **Git Commit 保证读取来源不可变；内存快照保证校验和入库使用同一内容；SQLite 事务保证 Contract、Task 状态与权威版本同时生效。** SQLite 不会自动保护库外文件和代码工作区，因此执行必须读取数据库中的权威 Contract 快照（或受其 Hash 校验的不可变副本）。

**与 PSC 现状的区别：** 当前 `import_bundle()` 已对**单个 Bundle 文件**执行一次 `read_bytes()` 并计算 Hash、解析与校验，然后将六文件落入版本目录；但尚未实现**按 Git Commit 读取六文件快照**或**SQLite 事务激活**。这套方案是 Q19 原子激活设计向上游数据来源一致性的延伸。参考：[现有 Bundle 导入与校验](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_runtime.py)。

**总结：不要靠反复读取和比较 Hash 去追赶 Planner 的修改；先冻结输入版本，再用同一份内存数据完成校验与事务提交，从源头消除跨文件版本混杂。**

---

## Preflight 如何用 SHA-256 绑定证据，以及能否阻止过期检查后的派发？

**定位：Preflight 是 Executor 启动前的只读准入检查，不是代码修改的权限隔离机制。** 它用独立检查器判断当前 Task 是否具备执行条件；`DENY`、超时、不可验证或证据过期均按 fail closed 阻断派发，而不是让 Executor 冒险继续。

1. **采集并绑定证据。** Runtime 收集当前 Task、Task-Scoped Contract Packet、上一轮 Review、Contract 绑定信息，以及**有界的**相关仓库文件；对文件和相关上下文计算 SHA-256，形成 Preflight Evidence Bindings。检查器只能依据这份受约束的只读证据作出 `ALLOW` / `DENY` 判断。
2. **ALLOW 后再次验证。** 在准备启动 Executor 前，Runtime 通过 `revalidate_evidence()` 重新收集证据并对比各项 Hash/绑定信息。即使检查器返回 `ALLOW`，只要相关文件或上下文在检查期间发生变化，最终结果仍转为 `UNKNOWN`，原因是 `preflight_evidence_stale`，**不启动 Executor**，也不消耗其重试额度。
3. **承认剩余竞态窗口。** 最后一次 Hash 比对与 Executor 真正开始修改文件之间，仍存在 TOCTOU 时间窗口；外部进程可以继续修改共享工作区。且校验针对绑定的证据集合，并不等于保证仓库所有文件始终不变。**当前 PSC 实现的是乐观一致性检测，不是强制写入隔离。**

**后续改进：** 从固定 Git 基线构建 Executor 专属工作区（例如受权限约束的 Worktree / 容器），保证 Preflight 与实际执行针对同一代码基线，并限制其他进程对该工作区的写入。仅凭最后一次 Hash 校验，无法彻底消除 TOCTOU。

**总结：Preflight 用 SHA-256 把“允许执行”的判断绑定到具体证据，并在启动前复核；能发现复核前的变化，却不能保证复核后代码绝不会再变。**

源码：[Preflight 证据收集与重校验](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/preflight_checker.py)、[MCP 派发准入](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)。

---

## 只读 Preflight 依赖 Prompt 还是程序权限，如何防止 pytest 等工具产生副作用？

**核心判断：PSC 的“只读 Preflight”不只是 Skill Prompt 约束，而是 Runtime 在启动独立 Checker 时施加的工具限制和环境限制；但目前不能声称拥有严格、经过验证的操作系统级无副作用隔离。**

### 当前实际机制

1. **受控证据输入，而非开放仓库权限。** Runtime 先收集 Task、Task-Scoped Contract、历史 Review 及有界的代码证据，计算 SHA-256 后通过 Prompt 交给独立 Checker；Checker 不需要自己遍历仓库。检查失败、超时、配置不可验证或证据过期时阻断 Executor 派发。
2. **Harness 级工具限制。** **Codex** 强制使用 `--sandbox read-only --ask-for-approval never`；**DSH** 通过运行时 `--patch` 禁用 Shell、写文件、代码编辑、MCP 和外部工具等能力，并校验组合配置，无法验证就拒绝运行；**Claude Code** 使用 `--tools "" --disallowedTools "*" --permission-mode dontAsk`，关闭工具访问。三者均在仓库外的隔离空工作目录运行，Runtime 还检查该目录是否出现非预期文件。
3. **明确权限边界。** Prompt 可以要求“不要修改代码”，但不是安全边界。上述措施能限制正常 Harness 的工具调用路径，**不能等同于对进程、插件或外部资源施加了完整的 OS 级只读沙箱**。例如仅看 `pytest` 的名称不能把它当作只读命令：测试可能写缓存、数据库或调用外部 API。当前 Checker 的职责是分析证据和提出可执行的验证计划，而不是直接获得通用测试执行权。

### 后续方案：将证据分析和测试执行分离

- **Checker 只分析。** 不提供命令执行、任意文件访问或外部 MCP 工具；由 Runtime 通过受控接口采集证据，Checker 只返回结构化准入判断。
- **需要实际运行 `pytest` 时，交给独立测试执行器。** 在一次性容器/沙箱中运行，源码只读挂载，缓存、临时文件及测试输出定向到隔离的可写目录；默认断网、无真实数据库凭证及 API Key，并使用测试替身或临时数据库。必要时还应限制进程、文件系统和资源权限，结束后销毁环境并保存测试证据。

**总结：Prompt 约束“应该做什么”，Harness 工具配置限制“通常能调用什么”，真正严格的副作用隔离则需要独立执行环境与 OS 权限边界。PSC 已实现前两类程序化限制，但尚未完整实现第三层。**

源码：[Preflight Checker 运行与证据采集](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/preflight_checker.py)、[Codex 适配器](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/adapters/codex.py)、[DSH 适配器](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/adapters/dsh.py)、[Claude 适配器](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/adapters/claude.py)。

---

## WinError 206 如何定位与修复，启动传输失败为何不能扣 Executor 重试预算？

**这是实际开发中暴露的“进程尚未创建，却被当作 Executor 失败”的状态机问题。** 当时 Task Packet 过长，PSC 将整段 Prompt 放进 Windows `subprocess` 命令行，触发 `OSError: [WinError 206]`。故障发生在进程创建阶段，Executor 未真正执行；历史案例中首次派发及三次异常重试均未产生有效产品修改，却耗尽了重试额度。排查重点因此从“为什么模型失败”转向了**Prompt 传输、进程启动位置和重试记账边界**。

### 实际修复：输入传输与异常分类分开处理

1. **长 Prompt 不再进入 `argv`。** `_prepare_prompt_transport()` 使 **Codex / Claude Code** 用 `-` 作为 stdin 标记，通过进程标准输入传递完整 Prompt；**DSH** 使用仓库 `.agentic-sdlc/runtime/executor-inputs/` 中短生命周期的 Runtime 自有提示词文件，命令行仅传简短的文件读取指令，执行结束后清理。这样可避开 Windows 命令行长度限制。
2. **将启动传输错误独立分类。** `invoke_executor.py` 的 `_spawn_failure_reason()` 把 `winerror == 206` 或 `errno.ENAMETOOLONG` 映射成 `launch_transport_failed`，结果标记为 `retryable=False`；不能只凭 `status=failed` 认定模型已执行。
3. **让重试记账遵循真实执行边界。** MCP Runtime 的 `_charge_actual_attempt()` 对 `launch_transport_failed` / 明确不可重试结果不扣预算，也不标记本轮首次 Executor 尝试已发生；`_mark_nonretryable_runtime_blocked()` 记录 `runtime_failure`，将工作流置为 `blocked`，待修复传输或环境问题后再继续同一 Task。
4. **真正启动后的异常另行处理。** 进程已执行但超时、非零退出或输出无效时，保留日志与 Git 代码变更证据；按异常重试路径处理。若程序执行完成但代码不符合 AC，则由 Supervisor 独立验收、决定质量返工，**进程结果不直接等于 Task PASS**。质量返工派发本身发生异常时，Runtime 也会优先计入异常预算，而非消耗一次质量返工机会。

| 情况 | 当前分类 / 处理 | 预算原则 |
| --- | --- | --- |
| WinError 206、`ENAMETOOLONG`，Executor 未创建 | `launch_transport_failed`；Runtime Failure 并阻断 | **不计首次执行，不扣任何重试预算** |
| Executor 已运行但超时、非零退出 | `timeout` / `process_failed`；保留执行证据 | 根据派发轮次计入异常重试 |
| Executor 完成但未通过 Contract 验收 | Supervisor 决定 `quality_rework` | 只在真实质量返工尝试时消耗相应预算 |

**验证依据：** 仓库已有针对 5 万字符 Codex stdin 传输、DSH 短引导文件、`ENAMETOOLONG` → 不可重试分类，以及 MCP 不扣初始尝试/异常重试/质量返工预算并保存阻断状态的回归测试。参考：[Executor 实现](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/invoke_executor.py)、[MCP 记账与阻断](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)、[传输与分类测试](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/tests/test_runtime_hardening.py)、[预算测试](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/tests/test_executor_mcp.py)。

**实现边界：** 当前对 `launch_transport_failed` 已有明确的“不扣预算”保护；但其他 `spawn_failed` 并未全部统一标记为 `retryable=False`，不能宣称所有启动前失败都已严格分离。后续应引入明确的 `NOT_STARTED / STARTED / FINISHED` 进程生命周期证据，统一启动异常的分类与重试记账规则。

**总结：Runtime 必须区分“传输/启动失败”“启动后执行失败”“执行完成但验收不通过”。没有真正发生的 Executor 尝试不应消耗重试预算，Supervisor 的最终 PASS 仍需独立验证。**

---

## 如何区分 PROCESS_STARTED、EXECUTOR_READY 与 TASK_STARTED？

**核心原则：OS 进程创建、Harness 完成初始化、Executor 开始处理 Task，是三个不同的事实，不能用 PID、日志出现或代码差异相互代替。** 例如 Codex 已获得 PID，却在加载配置或连接 API 时退出，此时最多能确认进程启动，不能把该 Task 当成真实执行失败并直接扣重试预算。

### PSC 当前已经实现什么？

- **进程调用与异常分类。** `invoke_executor.py` 默认使用 `subprocess.run()`；开启流式进度时由 `executor_progress.run_streaming()` 使用 `subprocess.Popen()`，并发读取 stdout/stderr、处理超时及退出码。`WinError 206` / `ENAMETOOLONG` 已单独分类为 `launch_transport_failed`，但还没有三阶段生命周期状态机。
- **Harness 输出解析与进度观察。** Codex、Claude Code、DSH 各有响应解析路径；流式进度将不同事件映射为工具调用、模型步骤、最终响应等**观察事件**，并保存进度/心跳。这些事件用于展示进度，**不是已验证的 Ready 或 Task Started 凭证**。例如 `ProgressRecorder` 在真正调用 `Popen()` 前就会发出文案为 `Executor started` 的 `started` 事件，不能把它当作 OS 启动确认。
- **独立 Smoke Check。** 正式派发前会验证与 Executor 配置指纹绑定的 Smoke Artifact；隔离工作区中的 Smoke Check 能检验曾经可启动并完成受控小任务，**但不能证明这一次派发已经 Ready 或开始处理当前 Task**。

### 改进方案：Runtime 状态机 + Adapter 事件规范化

| 阶段 | 可以信任的推进证据 | 不能据此推断的事 |
| --- | --- | --- |
| `PROCESS_STARTED` | 本次 `Popen()` **成功返回**进程对象及 PID，记录 Run ID、PID、启动时间、配置指纹 | PID 存在 ≠ Harness 初始化完成；瞬时退出也可能发生 |
| `EXECUTOR_READY` | Adapter 解析到与当前运行对应的**明确初始化完成 / Ready 握手**，或经过定义的受控就绪探测 | 仅出现 stdout、进程存活或历史 Smoke PASS，不足以证明本次 Ready |
| `TASK_STARTED` | 收到绑定当前 Run/Task 的**任务接收确认、首个明确的任务处理事件**等可信信号 | 普通心跳、模型连接成功、任意仓库 diff 都不能单独证明已开始本 Task |

具体实现时，让 **Runtime 管 `Popen()`、进程身份、状态持久化和转移规则；Harness Adapter 管解析**：把 Codex、Claude Code、DSH 不同版本的结构化日志映射为统一 `PROCESS_STARTED`、`EXECUTOR_READY`、`TASK_STARTED`、`FAILED` 等事件，并附上来源事件、Run/Task ID 和可验证的时间顺序。状态只允许依据证据单向推进；退出时记录**最后已确认阶段**，区分启动前、初始化期和任务执行期故障。

**没有 Ready 信号怎么办？** 不通过“有 PID / stdout / diff”猜测，而是把就绪状态保留为 `UNKNOWN`，可补充显式握手或 Adapter 专用探测；证据不足时不自动认定 `TASK_STARTED`。因此，**重试预算的最终扣费规则应以可证明的实际任务尝试为依据**；对状态未知的尝试应阻断并调查，不能直接当作“完全未执行”或“执行失败”去扣费或免费重试。这属于后续改进，当前 PSC 尚未完整实现跨 Harness 的统一生命周期证明。

**总结：进程启动成功不等于 Harness 就绪，Harness 就绪不等于 Task 已开始；每个状态转换都必须有本次运行的对应证据。**

源码：[Executor 调用与 Smoke Check](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/invoke_executor.py)、[流式 Popen、事件和心跳](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/executor_progress.py)、[MCP 预算管理](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/psc_mcp_server.py)。

---

## Executor 失联后如何避免重复执行数据库迁移等外部副作用？

**核心原则：Executor 失联不等于任务失败，更不意味着可以安全重试。** 尤其是 Alembic 数据库迁移这类外部副作用，即便没有收到 MCP Completion，数据库结构也可能已经改变；直接重派可能造成重复建表、版本冲突，甚至与尚在运行的旧 Executor 并发操作。

**当前 PSC 已实现的部分：** `task_execution_memory.py` 为历史尝试归档不可变 Execution Memory，记录执行状态、失败原因、修改文件指纹及有界交接信息；`invoke_executor.py` 在异常重试时提供兼容的同 Task/Contract 历史上下文；Supervisor 通过 Contract、代码差异与验证证据独立验收，**不会仅因执行器自报失败就机械判定产品未完成**。但这些机制主要覆盖仓库与 Executor 证据，**尚不能可靠追踪数据库、外部 API 等副作用，也不提供跨外部系统的 Exactly-Once 保证**。

### 拟议改进：副作用声明、持久意图、恢复门禁

1. **任务副作用分类。** Planner 在 Contract 中声明只读、可幂等重放、需恢复检查或不可逆等风险等级，并指定外部目标和验证方式；Runtime 根据分类选择重试策略。普通只读任务可以考虑自动重试，外部写操作不能默认重放。
2. **执行前持久化操作意图。** 为副作用操作分配稳定 `operation_id`，记录操作目标、预期结果和幂等键；支持幂等键的 API 重试时沿用同一键。Alembic 使用明确的 Revision / 迁移链标识并检查目标数据库。**Revision 不是通用的 Exactly-Once 锁**，仍需核实实际表结构和迁移是否部分完成。
3. **失联后先恢复检查，再决定是否重派。** 对副作用未确认的任务引入拟议 `UNKNOWN` 状态，阻断自动重试。Supervisor 结合 `alembic_version`、实际数据库 Schema、操作日志和 Execution Memory 复核结果；同时确认旧 Executor 已停止或失去相关外部资源的操作权限，避免新旧执行器并发写库。

| 恢复检查结论 | 下一步处理 |
| --- | --- |
| **确认未执行** | 可重新执行，必要时复用同一 `operation_id` |
| **确认已完成** | 不重复迁移；只继续剩余工作与独立验收 |
| **部分完成** | 先制定补偿/修复方案，核验后恢复 |
| **状态无法确认或旧进程仍可能执行** | 保持 `UNKNOWN`，阻断重派并升级人工检查 |

**实现边界：** 目前 PSC 有持久化执行记录、跨尝试交接和 Supervisor 决策；**任务级副作用分类、操作意图账本、数据库状态探测、强制恢复门禁及外部操作权撤销**都还需要实现。`UNKNOWN` 在这里表示期望引入的恢复语义，不能误称为当前 Runtime 已完备的正式状态机枚举。对不可事务化的外部效果，即使引入幂等键，也要考虑补偿与人工介入。

**总结：让任务重试从“失败后重新执行”升级为“先验证执行证据与外部状态，再决定重试、跳过、恢复或补偿”。幂等性降低重复操作风险，Execution Memory 提供上下文，Supervisor 负责验收决策，Runtime 则必须阻断未经确认的副作用重放。**

参考：[Execution Memory](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/task_execution_memory.py)、[Executor 异常恢复](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/invoke_executor.py)、[Supervisor 状态与验收](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/blob/main/scripts/supervisor_runtime.py)。
