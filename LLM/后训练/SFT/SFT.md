# SFT

[[后训练|返回上级：后训练]] · [[main|返回知识主干]]

围绕监督微调（Supervised Fine-Tuning, SFT）的基本原理、数据、能力作用与工程要点整理 Q&A。

## 问题目录

- [[SFT#什么是 SFT？|什么是 SFT？]]
- [[SFT#SFT 实际优化什么？|SFT 实际优化什么？]]
- [[SFT#SFT 数据有哪些类型、从哪里来？|SFT 数据有哪些类型、从哪里来？]]
- [[SFT#SFT 能给模型带来什么？|SFT 能给模型带来什么？]]
- [[SFT#SFT 为什么不能解决所有后训练问题？|SFT 为什么不能解决所有后训练问题？]]
- [[SFT#SFT 工程的关键是什么？|SFT 工程的关键是什么？]]

---

## 什么是 SFT？

SFT（Supervised Fine-Tuning，监督微调）使用高质量的 **输入—目标输出（Demonstration）** 数据继续训练已有模型，让模型更稳定地生成期望的回答、推理或行动轨迹。

它本质上是一种 **Imitation / Behavior Cloning**：通过示范告诉模型“在这种上下文下应该怎样做”。

---

## SFT 实际优化什么？

对于 Decoder-only LLM，SFT 通常仍使用 Causal Language Modeling 的 Token-level Cross Entropy，最大化目标 Response 中正确 Token 的条件概率：

> **Prompt + Ground-truth Response Prefix → Predict Next Ground-truth Token**

模型通常会看到完整的 Prompt 和目标 Response，但使用 **Loss Masking** 只让需要学习生成的 Token 参与损失。例如 Response-only SFT 中，System / User Token 仍作为上下文输入模型，只是其 Label 被设为 Ignore；Assistant Response Token 才计算交叉熵。

因此要区分：

- **Causal Mask**：防止看到未来 Token。
- **Attention Mask**：通常屏蔽 Padding 等无效位置。
- **Loss Mask / Label Mask**：决定哪些 Token 参与训练损失。

训练时还通常采用 **Teacher Forcing**：预测下一个 Response Token 时，前缀来自真实目标序列，而不是模型自己刚生成的序列。

---

## SFT 数据有哪些类型、从哪里来？

常见 SFT 数据包括：

- **Instruction / Conversation**：指令遵循和多轮对话。
- **Reasoning Trace**：数学、代码、逻辑等推理轨迹。
- **Tool-use / Agent Trajectory**：工具调用、Observation 与后续 Action。
- **Safety / Alignment Demonstration**：安全回答、拒答和行为约束。

数据来源通常包括人工标注、领域专家数据、真实交互修正数据、强模型生成的 Synthetic / Distillation Data，以及经过 Rejection Sampling、规则或 Verifier 筛选后的高质量样本。

---

## SFT 能给模型带来什么？

SFT 主要有三类作用：

1. **Behavior Shaping**：学习指令遵循、对话格式、JSON / Tool Call、回答风格等行为模式。
2. **Capability Elicitation**：把 Base Model 已经具备但不稳定出现的能力转化为更稳定、可调用的行为。
3. **Capability Improvement**：通过高质量推理、代码或工具轨迹进一步提高特定任务能力。

SFT 的能力提升通常高度依赖示范数据的质量与覆盖范围。

---

## SFT 为什么不能解决所有后训练问题？

SFT 主要学习已有 Demonstration，因此存在几个天然限制：

- **Imitation Ceiling**：容易受到 Teacher / Demonstration 能力上限约束。
- **缺少 Exploration**：不会自然探索训练数据中没有出现的新策略。
- **Preference 信息利用不足**：单个目标答案不能完整表达“A 比 B 更好”这样的相对偏好。
- **Train-Inference Gap**：Teacher Forcing 下训练始终沿 Ground-truth Prefix，而推理时依赖模型自己的生成前缀，可能产生 Exposure Bias。

因此现代后训练通常还会结合 Preference Optimization、RL-based Post-training 等方法。

---

## SFT 工程的关键是什么？

SFT 的工程效果主要取决于：

- **Data Quality / Data Mix**：正确性、覆盖率、难度和不同能力数据的配比。
- **Chat Template**：System / User / Assistant、Tool、Thinking 等角色和特殊 Token 的正确编码。
- **Loss Masking**：明确哪些 Token 应参与监督。
- **Packing / Sequence Construction**：提高训练效率并正确处理样本边界。
- **训练强度**：Learning Rate、Epoch、数据量等要避免过拟合和 Catastrophic Forgetting。
- **Evaluation**：既检查目标能力是否提升，也检查通用能力、安全性和行为是否发生回退。

> **SFT 的核心不是单纯“继续训练模型”，而是用高质量示范塑造模型在给定上下文下的目标行为分布。**

---

相关主题：[[后训练]] · [[微调]] · [[推理能力]] · [[评估]]
