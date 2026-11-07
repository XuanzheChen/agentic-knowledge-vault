# agentic-sdlc-contract-runtime（PSC）

[[main|返回知识主干]]

本 Tree 记录 [Agentic SDLC Contract-Driven Runtime（PSC）](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime) 的实际工程架构与后续机制分析。当前先收录仓库实现流程图；后续问题与总结按知识库的 Q&A 规范逐步整理，不预先建立空子树。

## 实际实现流程架构

![[psc-actual-architecture.svg]]

这张图依据 PSC 仓库 `main` 分支提交 [`c21dff887222`](https://github.com/XuanzheChen/agentic-sdlc-contract-runtime/commit/c21dff887222c00786f4e9de35af6a312de24b8b) 的代码与运行时约定绘制，覆盖 Contract 导入、MCP 调度、Preflight、Executor 执行、Supervisor 验收、重试与持久化恢复。

**阅读边界：** Executor 返回 `completed` 仅代表执行进程结果；任务是否通过由 Supervisor 依据 Contract 验收条件和独立验证证据决定。Runtime 负责调度、隔离、范围约束、证据保存及状态提交，不能用执行器自述代替验收。
