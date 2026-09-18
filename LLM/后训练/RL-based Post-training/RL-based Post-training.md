# RL-based Post-training

[[后训练|返回上级：后训练]] · [[main|返回知识主干]]

围绕基于强化学习的后训练（RL-based Post-training）的基本框架、Rollout、Reward、Credit Assignment、策略优化与典型反馈来源整理 Q&A。

## 子树

| 子树      | 内容                                                                      |
| ------- | ----------------------------------------------------------------------- |
| [[PPO]] | Proximal Policy Optimization 的 Clipping、Critic / GAE 与一次完整 LLM PPO 工程迭代 |
| [[GRPO]] | Group Relative Policy Optimization、组内相对 Advantage、完整训练迭代与 Dr.GRPO 等改进 |
| [[GSPO]] | Group Sequence Policy Optimization、Sequence-level Ratio / Clipping 与 MoE 稳定性 |
| [[DAPO]] | 面向 Long-CoT Reasoning RL 的 Clip-Higher、Dynamic Sampling、Token-level PG Loss 与 Overlong Reward Shaping |
| [[DHPO]] | Dynamic Hybrid Policy Optimization，混合 Token-level 与 Sequence-level Importance Correction |

## 问题目录

- [[RL-based Post-training#什么是 RL-based Post-training？|什么是 RL-based Post-training？]]
- [[RL-based Post-training#如何把 LLM 映射到强化学习框架？|如何把 LLM 映射到强化学习框架？]]
- [[RL-based Post-training#Rollout 是什么，为什么它是 RL 后训练的核心？|Rollout 是什么，为什么它是 RL 后训练的核心？]]
- [[RL-based Post-training#Reward 从哪里来？|Reward 从哪里来？]]
- [[RL-based Post-training#Credit Assignment 与 Advantage 在解决什么问题？|Credit Assignment 与 Advantage 在解决什么问题？]]
- [[RL-based Post-training#策略优化在 RL-based Post-training 中做什么？|策略优化在 RL-based Post-training 中做什么？]]
- [[RL-based Post-training#为什么常常需要 Reference Policy 与 KL 约束？|为什么常常需要 Reference Policy 与 KL 约束？]]
- [[RL-based Post-training#RLHF、RLAIF、RLVR 与 Agent RL 是什么关系？|RLHF、RLAIF、RLVR 与 Agent RL 是什么关系？]]
- [[RL-based Post-training#RL-based Post-training 与 SFT、偏好学习是什么关系？|RL-based Post-training 与 SFT、偏好学习是什么关系？]]
- [[RL-based Post-training#RL-based Post-training 的主要风险与工程难点是什么？|RL-based Post-training 的主要风险与工程难点是什么？]]

---

## 什么是 RL-based Post-training？

RL-based Post-training 是在后训练阶段，让当前模型作为 **Policy** 自己生成回答、推理轨迹或 Agent 行动轨迹，再根据这些行为得到的 Reward 更新模型，使高回报行为出现得更频繁、低回报行为出现得更少。

它与 SFT 的关键区别是：SFT 主要学习外部已经给定的 Demonstration；RL-based Post-training 则让模型先产生自己的行为，再根据结果反馈调整 Policy，因此具备更强的 **Exploration** 能力。

其基本闭环可以写成：

> **Current Policy → Rollout → Reward → Credit Assignment / Advantage → Policy Update → New Policy**

现代 RL 后训练既可以用于偏好对齐，也可以用于 Reasoning、Coding、Tool Use 与 Agentic Behavior 等能力训练。DeepSeek-R1 展示了大规模 RL 对推理能力的强化，而 Qwen3 也将 Reasoning RL 与 General RL 作为后训练的重要阶段。参考：[DeepSeek-R1](https://arxiv.org/abs/2501.12948)、[Qwen3](https://qwenlm.github.io/blog/qwen3/)。

---

## 如何把 LLM 映射到强化学习框架？

对于普通 LLM，可以近似理解为：

| RL 概念 | LLM 中的对应 |
| --- | --- |
| **Policy** | 当前语言模型 $\pi_\theta$ |
| **State** | Prompt 与已经生成的 Token / Observation |
| **Action** | 下一个 Token，或更高层的 Tool Call / Agent Action |
| **Trajectory** | 完整 Response、CoT 或 Agent 执行轨迹 |
| **Reward** | 对最终结果或过程质量的评价 |

Policy 定义了在当前状态下选择 Action 的概率：

$$
\pi_\theta(a_t \mid s_t)
$$

RL-based Post-training 的目标可以概括为提高高 Reward trajectory 的期望概率：

$$
J(\theta)=\mathbb{E}_{\tau\sim\pi_\theta}[R(\tau)]
$$

在 Reasoning 场景中，一条 trajectory 通常是完整的推理过程加最终答案；在 Agent 场景中，则可能包含多轮 Tool Call、Environment Observation 与最终任务结果。

---

## Rollout 是什么，为什么它是 RL 后训练的核心？

**Rollout** 是让当前 Policy 在某个 Prompt 或 Environment 上真实运行一次，得到一条完整行为轨迹。

一个 Prompt 通常会采样多个 Rollout：

> **Prompt → Current Policy → 多个候选 Trajectory → Reward Evaluation**

这些 Rollout 是 RL 的训练经验来源。模型不是只学习静态标准答案，而是在当前 Policy 的真实分布上不断产生新行为，再利用反馈学习。

因此大规模 RL 后训练的成本不仅来自反向传播，还包括：

- Rollout / Inference；
- Reward / Verifier Evaluation；
- Policy Training。

随着 Reasoning 与 Agent 轨迹变长，Rollout 往往成为训练系统中非常重要的计算与基础设施成本。

---

## Reward 从哪里来？

现代 RL-based Post-training 的 Reward 可以来自多种来源：

| 来源 | 典型形式 | 常见用途 |
| --- | --- | --- |
| **Human Feedback** | 人工 Preference、Score | Helpfulness、Style、Alignment |
| **AI Feedback** | AI Judge、Constitution、Critique | 可扩展偏好与安全反馈 |
| **Rule / Verifier** | 数学答案、单元测试、格式规则 | Reasoning、Math、Code |
| **Environment** | Task Success、环境最终状态 | Tool Use、Agent、Long-horizon Task |

因此 RL-based Post-training 不等于 RLHF。RLHF 只是其中一种使用 Human Feedback 构造 Reward 的路线。

对于数学、代码等“结果难生成但容易验证”的任务，可验证奖励尤其重要。此类训练通常称为 **RLVR（Reinforcement Learning with Verifiable Rewards）**。

Reward 可以只评价最终结果，也可以评价中间过程：

- **Outcome Reward**：任务最终是否成功。
- **Process Reward**：中间推理、工具调用或轨迹是否合理。

Reward 的可靠性直接决定训练方向；如果代理 Reward 与真实目标存在偏差，Policy 可能出现 [[Reward Hacking]]。

---

## Credit Assignment 与 Advantage 在解决什么问题？

Reward 往往只在一条长 trajectory 的末尾得到，但模型需要知道：**这条轨迹中的哪些行为应该被强化，哪些应该被压低。**

这就是 **Credit Assignment** 问题。

Advantage 可以先直观理解为：

> **当前行为或 trajectory 的结果，比原本预期的表现好多少。**

若 Advantage 为正，则提高相关行为的概率；若为负，则降低相关行为的概率。

不同 RL 策略优化算法会用不同方式估计和利用 Advantage。后续学习 PPO、GRPO、GSPO 时，重点可以观察它们分别怎样解决：

- Advantage / Credit Assignment；
- Policy Update；
- 训练稳定性与计算成本。

---

## 策略优化在 RL-based Post-training 中做什么？

拿到 Reward 后，还需要把“哪些 Rollout 更好”转化为对模型参数的更新，这一步就是 **Policy Optimization（策略优化）**。

它的高层目标可以理解为：

> **提高高 Reward 行为的生成概率，降低低 Reward 行为的生成概率，同时避免一次更新让 Policy 变化过大。**

因此策略优化主要处理三个问题：

1. 如何利用 Reward / Advantage 构造有效训练信号；
2. 如何更新当前 Policy；
3. 如何限制更新幅度、保证训练稳定。

[[LLM/后训练/RL-based Post-training/PPO/PPO|PPO]]、[[LLM/后训练/RL-based Post-training/GRPO/GRPO|GRPO]]、[[LLM/后训练/RL-based Post-training/GSPO/GSPO|GSPO]]、[[LLM/后训练/RL-based Post-training/DAPO/DAPO|DAPO]] 与 [[LLM/后训练/RL-based Post-training/DHPO/DHPO|DHPO]] 都属于这一层的重要方法或训练 Recipe，但它们分别从 Advantage、Importance Correction 粒度、Sampling、Clipping、Loss Aggregation 与 Reward Shaping 等不同位置改造 RL 后训练系统。

---

## 为什么常常需要 Reference Policy 与 KL 约束？

如果只最大化 Reward，Policy 可能为了获得更高分迅速偏离原有模型分布，并进入 Reward System 不可靠的区域。

因此很多 RL 后训练方法会保留一个训练前或阶段性冻结的 **Reference Policy**，并通过 KL Divergence 等方式限制当前 Policy 与 Reference Policy 的距离。

高层目标可以写成：

$$
\max_\theta\;\mathbb{E}[R]
-\beta D_{KL}(\pi_\theta\|\pi_{ref})
$$

其直觉是：

> **提高 Reward，但不要让模型为了追逐 Reward 而一次偏离原来的可靠行为太远。**

这类约束不能消除 [[Reward Hacking]]，但可以降低对不完美 Reward 过度优化的风险。

---

## RLHF、RLAIF、RLVR 与 Agent RL 是什么关系？

它们主要描述 **Reward / Feedback 的来源或训练场景**，而不是彼此互斥的策略优化算法。

| 名称 | 主要反馈来源 | 典型目标 |
| --- | --- | --- |
| **RLHF** | Human Feedback / Human Preference | 人类偏好与 Alignment |
| **RLAIF** | AI Feedback / AI Judge / Constitution | 可扩展偏好与安全对齐 |
| **RLVR** | Rule / Verifier | Math、Code、Reasoning |
| **Agent RL** | Environment Outcome | Tool Use、Long-horizon Agent Behavior |

经典 RLHF pipeline 可以表示为：

> **SFT → Human Preference → Reward Model → RL Policy Optimization**

参考：[InstructGPT](https://arxiv.org/abs/2203.02155)。

RLAIF 的典型思路是用 AI Feedback 替代或扩展人工反馈，例如 Constitutional AI。参考：[Constitutional AI](https://arxiv.org/abs/2212.08073)。

Agent RL 则更接近传统 Environment Interaction：模型进行 Tool Call、接收 Observation、继续行动，最终根据环境状态或任务成败得到 Reward。Qwen3-Coder 已公开采用 Long-horizon Agent RL，并强调 Environment Scaling 对 Agent RL 的重要性。参考：[Qwen3-Coder](https://qwenlm.github.io/blog/qwen3-coder/)。

---

## RL-based Post-training 与 SFT、偏好学习是什么关系？

三者使用的反馈形式不同：

| 范式 | 主要信号 | 核心问题 |
| --- | --- | --- |
| **SFT** | Demonstration | “一个好行为应该怎样做？” |
| **偏好学习** | Preference | “多个行为中哪个更好？” |
| **RL-based Post-training** | Reward / Outcome | “模型自己行动后，怎样根据结果调整策略？” |

它们不是严格互斥的阶段。现实中的 Post-training Pipeline 经常组合使用：

> **SFT 初始化行为 → Preference / Reward System 建立评价信号 → RL Rollout 与 Policy Optimization 进一步探索和优化**

偏好学习中的 Reward Model 可以作为 RL 的 Reward Function；Human / AI Preference 也可以不进入 RL，而直接用于 DPO 等偏好优化方法。

因此应区分：

> **Feedback 从哪里来** 与 **Policy 如何被优化** 是两个正交维度。

---

## RL-based Post-training 的主要风险与工程难点是什么？

主要问题包括：

- **Reward Quality**：Reward 是否真的代表目标行为。
- **Reward Hacking / Overoptimization**：Policy 是否学会利用代理评价漏洞。
- **Credit Assignment**：长 trajectory 中如何分配最终 Reward。
- **Training Stability**：Policy 更新过快可能导致能力退化或行为坍缩。
- **Rollout Cost**：长 CoT、代码执行和 Agent 轨迹会显著增加训练成本。
- **Environment Scaling**：Agent RL 需要大量可并行、可重置、可验证的真实或模拟环境。
- **Evaluation**：Training Reward 上升不等于真实任务质量上升，需要独立 Eval 检查真实能力和安全性。

因此 RL 后训练不是单纯“选一个 RL 算法”，而是由 **Policy、Rollout、Reward System、策略优化、Environment 与 Evaluation** 共同组成的训练系统。

---

相关主题：[[后训练]] · [[SFT]] · [[偏好学习]] · [[Reward Model（RM）]] · [[LLM/后训练/RL-based Post-training/PPO/PPO|PPO]] · [[LLM/后训练/RL-based Post-training/GRPO/GRPO|GRPO]] · [[LLM/后训练/RL-based Post-training/GSPO/GSPO|GSPO]] · [[LLM/后训练/RL-based Post-training/DAPO/DAPO|DAPO]] · [[LLM/后训练/RL-based Post-training/DHPO/DHPO|DHPO]] · [[Reward Hacking]] · [[推理能力]] · [[Agent]] · [[评估]]
