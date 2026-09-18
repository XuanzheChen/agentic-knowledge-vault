# RM 与 RL-based Post-training

[[LLM/后训练/偏好学习/Reward Model（RM）/Reward Model（RM）|返回上级：Reward Model（RM）]] · [[main|返回知识主干]] · [[LLM/后训练/RL-based Post-training/RL-based Post-training|相关：RL-based Post-training]]

围绕不同类型 Reward Model 如何影响 RL-based Post-training 整理 Q&A。主线仍是 **Outcome RM（ORM）与 Process RM（PRM）对应的 Reward Granularity**：这一轴会直接影响 Reward 在 trajectory 中出现的位置与粒度，因此与 Advantage / Credit Assignment 深度交织。Multi-objective、Generative、Conditional、Online、Ensemble 等其他 RM 维度与这条轴大体正交，主要改变 Reward 的目标、质量、可靠性、条件或生命周期，而通常不改变 RL 方法消费 Reward 的基本机制。

## 问题目录

- [[RM 与 RL-based Post-training#RM 在 RL-based Post-training 中如何影响 Advantage？|RM 在 RL-based Post-training 中如何影响 Advantage？]]
- [[RM 与 RL-based Post-training#为什么 ORM / PRM 是与 RL-based Post-training 交织最深的一条 RM 轴？|为什么 ORM / PRM 是与 RL-based Post-training 交织最深的一条 RM 轴？]]
- [[RM 与 RL-based Post-training#Outcome RM 如何影响 RL-based Post-training？|Outcome RM 如何影响 RL-based Post-training？]]
- [[RM 与 RL-based Post-training#Process RM 如何改变 Advantage 与 Credit Assignment？|Process RM 如何改变 Advantage 与 Credit Assignment？]]
- [[RM 与 RL-based Post-training#有 Process RM 是否就等于有 Token-level Advantage？|有 Process RM 是否就等于有 Token-level Advantage？]]
- [[RM 与 RL-based Post-training#不同 RM 的 Reward Scale 与 Reward Ranking 会怎样影响 Advantage？|不同 RM 的 Reward Scale 与 Reward Ranking 会怎样影响 Advantage？]]
- [[RM 与 RL-based Post-training#除 ORM / PRM 外，其他主流 RM 类型如何影响 RL-based Post-training？|除 ORM / PRM 外，其他主流 RM 类型如何影响 RL-based Post-training？]]
- [[RM 与 RL-based Post-training#为什么这些正交 RM 维度通常不会改变 RL 方法如何利用 Reward？|为什么这些正交 RM 维度通常不会改变 RL 方法如何利用 Reward？]]
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

## 除 ORM / PRM 外，其他主流 RM 类型如何影响 RL-based Post-training？

这些 RM 类型主要改变的是 **Reward 本身是什么、是否可靠、是否适配当前任务与 Policy**，而不是像 ORM / PRM 一样直接改变 Reward 的时序粒度。

| RM / Reward 设计 | 主要改变 Reward 的什么属性 | 对 RL-based Post-training 的主要影响 |
| --- | --- | --- |
| **Scalar / Pair-wise RM** | Ranking、Margin、Calibration | 决定哪些 Rollout 被排得更高，以及 Reward 差距有多大 |
| **Multi-objective RM** | Objective / Trade-off | 决定 Correctness、Safety、Helpfulness、Efficiency 等目标如何组合成训练方向 |
| **Conditional / Rubric-conditioned RM** | Context-dependent Objective | 同一行为在不同任务、Rubric 或约束下可以获得不同 Reward |
| **Generative / Reasoning RM** | Evaluation Quality / Inference Compute | 通过 Critique、Verification、Reasoning 提高 Reward 判断质量；若输出 Process Signal，也可以进一步与 PRM 轴组合 |
| **Online / Policy-aware RM** | Lifecycle / Distribution Adaptation | 让 Reward Function 跟随当前 Policy 分布更新，减少固定 RM 的 Distribution Shift |
| **Ensemble / Uncertainty-aware RM** | Confidence / Robustness | 对 RM 分歧较大的样本降低有效 Reward 或采用保守目标，减少 Reward Overoptimization |
| **Verifier / Rule-based Reward** | External Grounding | 用数学答案、测试、环境结果等提高 Reward 的客观性与可靠性；严格来说属于更广义 Reward System，而不一定是 learned RM |

### Scalar / Pair-wise RM

经典 Pair-wise RM 主要学习：

$$
R(y_w)>R(y_l)
$$

它对 RL 最直接的影响是 **Reward Ordering 与 Margin**。如果两个 RM 对 Rollout 排序不同，后续得到的 Advantage 符号就可能不同；如果排序相同但分数间距不同，则 PPO、Dr.GRPO 等对 Reward Scale 更敏感的方法会感受到不同的优化强度。经典实现参考：[InstructGPT](https://arxiv.org/abs/2203.02155)。

### Multi-objective RM

Multi-objective RM 可以输出：

$$
\mathbf r
=
[r_1,r_2,\ldots,r_K]
$$

例如 Correctness、Safety、Helpfulness、Efficiency。进入普通 Policy Optimization 前，通常还需要加权、Gating、约束或其他聚合方式得到可使用的 Reward。它改变的是 **“什么叫好”以及多个目标如何权衡**，而不是 Policy Gradient 如何利用 Reward。参考：[ArmoRM](https://arxiv.org/abs/2406.12845)。

### Conditional / Rubric-conditioned RM

条件式 RM 写成：

$$
R(x,y,c)
$$

其中 $c$ 是任务 Criteria、Rubric、用户要求或安全约束。它使 Reward Landscape 随 Context 改变：同一个 Response 在不同 Rubric 下可以得到不同 Reward，但后面的 PPO / GRPO / GSPO 仍然按照各自原有方式处理这个 Reward。相关设计见 [[LLM/后训练/偏好学习/Reward Model（RM）/Reward Model（RM）#什么是条件式评分 RM？|条件式评分 RM]]。

### Generative / Reasoning RM

Generative RM 通过生成 Critique、Verification 或 Reasoning 后再给 Reward，主要改善复杂评价任务中的 **Reward Quality**。如果最后仍然压成一个 Sequence Scalar，则后续 RL 机制没有结构变化；只有当生成式评价进一步保留为 Step / Process Signal 时，它才会与 PRM 的 Reward Granularity 轴发生交互。参考：[Critique-out-Loud Reward Models](https://arxiv.org/abs/2408.11791)、[ThinkPRM](https://arxiv.org/abs/2504.16828)。

### Online / Policy-aware RM

Online RM 随 Policy 输出分布持续更新：

> **Policy$_t$ → 新 Rollout → 新反馈 → RM$_{t+1}$ → Policy$_{t+1}$**

它主要改善 Reward 对当前 Policy 分布的适配，降低固定 RM 被持续优化后出现 Distribution Shift 或漏洞暴露的问题。它使 Reward Function 本身随训练时间变化，但 PPO / GRPO / GSPO 如何消费当前 Reward 的基本机制仍保持不变。参考：[RLHF Workflow: From Reward Modeling to Online RLHF](https://arxiv.org/abs/2405.07863)。

### Ensemble / Uncertainty-aware RM

多个 RM 可以对同一 Response 给出一组 Reward：

$$
R_1,R_2,\ldots,R_M
$$

除了均值外，还可以利用模型间分歧估计不确定性，并构造更保守的 Effective Reward，例如对高方差样本降低奖励。其主要作用是避免 Policy 过度利用单个 RM 的错误高分区域，而不是改变 Advantage Estimator 的结构。Reward Model Ensemble 的研究表明，Worst-case 与 Uncertainty-weighted 等保守聚合可以降低 PPO 等方法中的 Reward Overoptimization。参考：[Reward Model Ensembles Help Mitigate Overoptimization](https://arxiv.org/abs/2310.02743)。

### Verifier / Rule-based Reward

数学答案、Code Test、Compiler、Schema、环境任务成败等 Verifier 可以提供更接近外部事实的 Reward。它们严格来说不一定属于 learned RM，但在现代 RLVR 中承担相同的 Reward 输入角色。

它们主要提高：

> **Reward 的 Grounding 与 Correctness。**

如果只输出 Final Outcome，它们依旧是 Sequence-level Sparse Reward；只有进一步产生 Process / Step Signal 时，才会改变 Credit Assignment 的粒度。

---

## 为什么这些正交 RM 维度通常不会改变 RL 方法如何利用 Reward？

可以把 RL-based Post-training 拆成两层：

$$
\boxed{
\text{Reward System}
\rightarrow
R
}
$$

以及：

$$
\boxed{
R
\rightarrow
\text{Advantage Estimation}
\rightarrow
\text{Importance Correction / Clipping}
\rightarrow
\text{Policy Update}
}
$$

Multi-objective、Generative、Conditional、Online、Ensemble 等 RM 主要作用在第一层：它们决定 Reward 的**语义、质量、可靠性、适用条件和生命周期**。

只要这些设计最终仍然输出相同粒度的 Reward，例如每条 Sequence 一个 Scalar：

$$
R_i
$$

那么后面的 GRPO 仍然可以照常计算：

$$
\hat A_i
=
f(R_i,R_{group})
$$

GSPO 仍然可以使用 Sequence-level Importance Ratio，PPO 也仍然按自己的 Return / Critic / GAE 机制计算 Advantage。

因此这些 RM 维度主要改变：

> **“RL 收到的 Reward 好不好、代表什么、可信度多高。”**

而不会自动改变：

> **“RL 方法怎样把 Reward 转成 Advantage，再怎样更新 Policy。”**

真正会跨过这层边界的是 **Reward Granularity**：当 ORM 的 Sequence Reward 变成 PRM 的 Step / Process Reward 时，后面的 Advantage / Credit Assignment 才有机会从 Sequence level 进一步细化。

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
