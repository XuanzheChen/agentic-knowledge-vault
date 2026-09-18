# RM 与 RL-based Post-training

[[LLM/后训练/偏好学习/Reward Model（RM）/Reward Model（RM）|返回上级：Reward Model（RM）]] · [[main|返回知识主干]] · [[LLM/后训练/RL-based Post-training/RL-based Post-training|相关：RL-based Post-training]]

围绕不同类型 Reward Model 如何通过 Reward 改变 Advantage、Credit Assignment 与 Policy Optimization 整理 Q&A。

## 问题目录

- [[RM 与 RL-based Post-training#RM 在 RL-based Post-training 中如何影响 Advantage？|RM 在 RL-based Post-training 中如何影响 Advantage？]]
- [[RM 与 RL-based Post-training#Outcome RM 如何影响 RL-based Post-training？|Outcome RM 如何影响 RL-based Post-training？]]
- [[RM 与 RL-based Post-training#Process RM 如何改变 Advantage 与 Credit Assignment？|Process RM 如何改变 Advantage 与 Credit Assignment？]]
- [[RM 与 RL-based Post-training#有 Process RM 是否就等于有 Token-level Advantage？|有 Process RM 是否就等于有 Token-level Advantage？]]
- [[RM 与 RL-based Post-training#不同 RM 的 Reward Scale 与 Reward Ranking 会怎样影响 Advantage？|不同 RM 的 Reward Scale 与 Reward Ranking 会怎样影响 Advantage？]]
- [[RM 与 RL-based Post-training#Multi-objective RM、Generative RM 与 Online RM 分别会怎样影响 RL？|Multi-objective RM、Generative RM 与 Online RM 分别会怎样影响 RL？]]
- [[RM 与 RL-based Post-training#不同 Reward Granularity 与哪些 Policy Optimization 形式更自然匹配？|不同 Reward Granularity 与哪些 Policy Optimization 形式更自然匹配？]]
- [[RM 与 RL-based Post-training#ORM 与 PRM 在 RL 中的核心取舍是什么？|ORM 与 PRM 在 RL 中的核心取舍是什么？]]

---

## RM 在 RL-based Post-training 中如何影响 Advantage？

Reward Model 在 RL-based Post-training 中首先提供的是 **Reward**，而不是 Advantage 的 baseline。

可以把基本关系写成：

> **Reward Model / Reward System → Reward → Advantage Estimation → Policy Optimization**

例如：

- PPO 的 baseline 主要来自 Critic / Value Model；
- GRPO / GSPO 的 baseline 主要来自同一 Prompt 下的 Group Reward Mean；
- Dr.GRPO 同样使用 Group-relative Centering，只是取消了 Group Std Scaling。

因此更准确的关系是：

$$
\text{Reward-derived signal}
-
\text{Baseline}
\rightarrow
\text{Advantage}
$$

不同 RM 会通过改变 Reward 的**排序、尺度、粒度、时序位置与评价目标**，间接改变最终 Advantage。

经典 RLHF 就是先由 Reward Model 对完整 Response 给分，再由 PPO 把 Reward 转成 Policy Update。参考：[InstructGPT](https://arxiv.org/abs/2203.02155)。

---

## Outcome RM 如何影响 RL-based Post-training？

Outcome Reward Model（ORM）主要对完整 Response 或最终 Trajectory 给一个 Reward：

$$
R_i=R(x,y_i)
$$

它告诉 Policy：

> **这整条轨迹最终好不好。**

但不会直接指出中间哪个 Step 做得好、哪个 Step 做错。

对于 GRPO / GSPO，这种 Sequence-level Reward 很自然：同一个 Prompt 下多条 Rollout 得到各自的 $R_i$，再通过组内比较得到：

$$
\hat A_i
$$

于是整条 Response 通常共享同一个 Sequence-level Advantage。

优点是：

- Reward 定义简单；
- 对 Math / Code 等 Final Outcome 可验证任务特别自然；
- 对新颖但最终正确的 reasoning path 更宽容。

缺点则是 Credit Assignment 较粗：一条最终正确的轨迹中，错误绕路也可能被整体强化；一条最终失败的轨迹中，前面正确的步骤也可能整体受到负向更新。

---

## Process RM 如何改变 Advantage 与 Credit Assignment？

Process Reward Model（PRM）不只评价最终 Outcome，而是对中间 reasoning step、Tool Call、Action 或 State Transition 提供更细粒度评价：

$$
r_1,r_2,\ldots,r_T
$$

这会直接增加 Reward System 能够提供的局部信息，使 Advantage Estimation 不必完全依赖最终 Reward 向前传播。

在 PPO 中，Process Reward 可以直接进入：

$$
\delta_t
=
r_t
+
\gamma V(s_{t+1})
-
V(s_t)
$$

再通过 GAE 得到位置相关的：

$$
A_t
$$

因此 PPO 天然能够消费 Dense Process Reward。

在 Reasoning / Agent 场景中，PRM 的价值正是把：

$$
R(\tau)
$$

进一步细化成：

$$
r_1,r_2,\ldots,r_T
$$

从而让 Policy 更容易区分“哪里做得好、哪里做得差”。Process Supervision 的代表性工作可参考 [Let's Verify Step by Step](https://arxiv.org/abs/2305.20050)。

---

## 有 Process RM 是否就等于有 Token-level Advantage？

不等于。

PRM 能够提供 Step-level / Process-level Score，但这些 Score 怎样进入 Policy Optimization 仍然是另一个设计问题。

例如可以把一组 Process Score：

$$
r_1,r_2,\ldots,r_T
$$

先聚合成一个 Sequence Reward：

$$
R_i
=
\operatorname{Aggregate}
(r_1,\ldots,r_T)
$$

再交给 GRPO / GSPO。

这种情况下，虽然 RM 使用了 Process 信息，但最终仍然只有：

$$
\hat A_i
$$

而不是：

$$
\hat A_{i,t}
$$

真正的 Token / Step-level Advantage 还需要进一步的 Credit Assignment，例如：

- Dense Reward + Critic / GAE；
- Step-level Verifier；
- Turn-level Environment Reward；
- Reward Redistribution；
- 直接构造随位置变化的 $\hat A_{i,t}$。

这也是 [[LLM/后训练/RL-based Post-training/GSPO/GSPO#GSPO-token 是什么，它想恢复 GSPO 丢失的什么信息？|GSPO-token]] 有意义的前提：它可以消费 Token-varying Advantage，但不会自动生成这些 Advantage。

> **Process RM 提供更细粒度评价能力；Policy Optimization 是否真正利用这些粒度，是独立问题。**

---

## 不同 RM 的 Reward Scale 与 Reward Ranking 会怎样影响 Advantage？

不同 RM 对 RL 的影响首先体现在 **Reward Ranking**。

如果 RM A 认为：

$$
R(y_1)>R(y_2)
$$

而 RM B 认为：

$$
R(y_2)>R(y_1)
$$

那么相对 Advantage 的符号可能直接翻转，最终 Policy 会朝完全不同的方向更新。

Reward Scale 也会影响训练，但影响程度取决于 Advantage Normalization。

例如原始 GRPO：

$$
A_i
=
\frac{R_i-\mu}{\sigma}
$$

如果 Reward 做正的仿射变换：

$$
R_i'
=
aR_i+b,
\qquad a>0
$$

则标准化后的 Advantage 基本保持不变：

$$
A_i'=A_i
$$

因此原始 GRPO 对统一的正仿射 Reward Scaling 较不敏感。

但 Dr.GRPO：

$$
A_i
=
R_i-\mu
$$

若 Reward 变为 $aR_i+b$，则：

$$
A_i'
=
a(R_i-\mu)
$$

Reward Scale 会直接进入 Advantage Scale。

因此：

> **RM 的 Calibration 是否重要，和后续 Advantage Normalization 方式有关。**

Reward Model 与 Policy Optimization 并不是完全独立的两个模块。

---

## Multi-objective RM、Generative RM 与 Online RM 分别会怎样影响 RL？

不同 RM 设计不仅改变 Reward 粒度，也会改变 Reward 所表达的目标与可靠性。

### Multi-objective RM

Multi-objective RM 可以输出：

$$
\mathbf r
=
[r_1,r_2,\ldots,r_K]
$$

例如 Correctness、Safety、Helpfulness、Efficiency 等。

Policy Optimization 最终必须决定：

- 怎样加权；
- 哪些目标可以互相补偿；
- 哪些目标应作为硬约束；
- 是否需要 Context-dependent 权重。

因此 Multi-objective RM 实际改变的是 **Reward Landscape 本身的多目标结构**。参考：[ArmoRM](https://arxiv.org/abs/2406.12845)。

### Generative / Reasoning RM

Generative RM 会先生成 Critique、Rubric 检查或 Verification，再给出 Reward。它可能提高复杂任务的评价质量，也能够产生比单一 Scalar 更丰富的过程反馈。

如果这些 Critique 进一步被转化为 Process Reward 或 Step Credit，就可能影响更细粒度的 Advantage；如果最终仍然只压缩成一个 Scalar，则主要改善的是 Sequence Reward 的质量。参考：[Critique-out-Loud Reward Models](https://arxiv.org/abs/2408.11791)、[ThinkPRM](https://arxiv.org/abs/2504.16828)。

### Online / Policy-aware RM

Online RM 随当前 Policy 的输出分布持续更新：

> **Policy$_t$ → 新 Rollout → 新反馈 → RM$_{t+1}$ → Policy$_{t+1}$**

它主要影响 Reward 的**分布适配性**：降低固定 RM 面对新型 Policy Behavior 时出现 Distribution Shift、被 Policy 持续找到漏洞的风险。参考：[RLHF Workflow: From Reward Modeling to Online RLHF](https://arxiv.org/abs/2405.07863)。

---

## 不同 Reward Granularity 与哪些 Policy Optimization 形式更自然匹配？

不同 Reward 粒度与 Policy Optimization 之间没有强制绑定，但存在较自然的结构组合：

| Reward / Feedback | 典型粒度 | 更自然的 Advantage 形式 | 常见 Policy Optimization |
| --- | --- | --- | --- |
| **Outcome RM / Verifier** | Sequence | Sequence / Group Advantage | GRPO、GSPO、DAPO、DHPO |
| **Process RM** | Step / Process | Dense / Step Advantage | PPO + GAE、GSPO-token 等 |
| **Environment Reward** | Step / Turn / Outcome | Step / Turn / Trajectory Advantage | PPO、Agent RL、支持 Token / Turn Credit 的方法 |
| **Multi-objective RM** | Sequence 或 Process | 多目标聚合后的 Advantage | 可与多种 RL 方法组合 |
| **Generative RM** | 取决于输出方式 | Sequence 或 Process | 取决于 Critique 如何转成 Reward |

例如 PPO 能天然利用 Dense Process Reward，因为 Critic / GAE 本来就会产生随时间变化的 $A_t$；标准 GRPO / GSPO 更自然地消费 Sequence-level Reward；GSPO-token 则为更细粒度的 $A_{i,t}$ 提供了 Policy Optimization 接口。

这张对应关系不是算法限制，而是在说明：

> **Reward System 能提供多少局部信息，决定了后续 Advantage Estimator 最多能利用多少 Credit 信息。**

---

## ORM 与 PRM 在 RL 中的核心取舍是什么？

Outcome RM 与 Process RM 并不是简单的“粗糙版”和“高级版”。

ORM 的优势是：

- Reward 简单；
- 容易与可验证 Outcome 结合；
- 不需要规定唯一的中间 reasoning path；
- 对 novel but correct trajectory 更宽容。

PRM 的优势是：

- 能提供 Dense Feedback；
- Credit Assignment 更细；
- 能定位中间 reasoning / action error；
- 对 Long-horizon Reasoning 和 Agent trajectory 更有潜力。

但 PRM 也有明显风险：

- Step Label 获取昂贵；
- Process Unit 难定义；
- PRM 自身会产生 Judge / Model Bias；
- 可能压制与训练分布不同但最终正确的新颖推理；
- 也可能出现 Process-level Reward Hacking。

此外，不能简单把每一步 PRM Score 全部相加，否则长 Response 可能仅因为步骤更多而获得更高 Reward，形成 Length Hacking。Process Score 如何转成真正的 RL Reward，本身仍属于 Reward Shaping / Credit Assignment 问题。

因此更准确的取舍是：

$$
\boxed{
\text{Outcome Robustness}
\leftrightarrow
\text{Process Credit Precision}
}
$$

参考：[Let's Verify Step by Step](https://arxiv.org/abs/2305.20050)、[Process Reward Models for LLM Agents](https://arxiv.org/abs/2502.10325)。

---

相关主题：[[LLM/后训练/偏好学习/Reward Model（RM）/Reward Model（RM）|Reward Model（RM）]] · [[LLM/后训练/RL-based Post-training/RL-based Post-training|RL-based Post-training]] · [[LLM/后训练/RL-based Post-training/PPO/PPO|PPO]] · [[LLM/后训练/RL-based Post-training/GRPO/GRPO|GRPO]] · [[LLM/后训练/RL-based Post-training/GSPO/GSPO|GSPO]]
