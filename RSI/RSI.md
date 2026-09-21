# RSI

[[main|返回知识主干]]

围绕递归式自我改进（Recursive Self-Improvement，RSI）整理概念、机制、自动化 AI R&D 闭环及其边界。当前先记录基础定义，后续只有在相关 Q&A 形成稳定概念簇后再继续拆分子树。

## 问题目录

- [[RSI#什么是 RSI？|什么是 RSI？]]

---

## 什么是 RSI？

RSI 指 **Recursive Self-Improvement（递归式自我改进）**。核心不是“AI 把某一次回答改得更好”，而是 **AI 系统参与改进 AI 系统本身，并且这种改进进入后续迭代，使下一代系统继续参与、甚至更有效地推动再下一轮改进**。

可以把它抽象成一个闭环：

```text
AI 系统 S0
  ↓
参与研究、设计、编码、训练或评估
  ↓
得到更强或更有效的系统 S1
  ↓
S1 再参与下一轮 AI 改进
  ↓
S2 → S3 → ...
```

因此，RSI 中“Recursive（递归）”强调的是：**改进后的系统重新进入“改进 AI”的过程本身。** 如果一个模型只是自我反思、重写答案、自动调 Prompt，或者在人类主导的研发流程里辅助写代码，这些都可以属于广义的 self-improvement 或 AI-assisted R&D，但还不能仅凭这一点称为完整 RSI。

更强意义上的 RSI 通常意味着，AI 不只是执行人类指定的局部优化任务，而是在 AI 研发闭环中承担越来越多角色，例如提出改进方向、实现修改、运行实验、评估结果，并把有效改进持续带入后继系统。OpenAI 在 2026 年的公开表述中把“完全自主的递归式自我改进”描述为 AI 独立推动一代又一代更强系统；Anthropic 则将其描述为 AI 最终能够自主设计和开发自己的后继系统。两者都明确指出，截至 2026 年 9 月，这种完整闭环尚未实现。

参考：[OpenAI — The AI policy window is open. We need to act.](https://openai.com/index/ai-policy-window/) · [Anthropic — When AI builds itself](https://www.anthropic.com/institute/recursive-self-improvement)

可以用一句话记住：

> **Self-improvement 是“AI 变得更好”；RSI 是“AI 变得更好之后，又更有能力参与制造下一轮更好的 AI”。**
