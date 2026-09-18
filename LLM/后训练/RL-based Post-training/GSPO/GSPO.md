# GSPO

[[LLM/后训练/RL-based Post-training/RL-based Post-training|返回上级：RL-based Post-training]] · [[main|返回知识主干]]

围绕 Group Sequence Policy Optimization（GSPO）的 Sequence-level Importance Ratio、Sequence-level Clipping、训练稳定性，以及其与 GRPO 的关系整理 Q&A。

## 问题目录

- [[GSPO#GSPO 是什么，它主要解决 GRPO 的什么问题？|GSPO 是什么，它主要解决 GRPO 的什么问题？]]
- [[GSPO#GSPO 为什么把 Importance Ratio 从 Token-level 提升到 Sequence-level？|GSPO 为什么把 Importance Ratio 从 Token-level 提升到 Sequence-level？]]
- [[GSPO#GSPO 的 Sequence-level Importance Ratio 如何计算？|GSPO 的 Sequence-level Importance Ratio 如何计算？]]
- [[GSPO#GSPO 的 Clipping 与 GRPO 有什么区别？|GSPO 的 Clipping 与 GRPO 有什么区别？]]
- [[GSPO#一次完整 GSPO iteration 如何执行？|一次完整 GSPO iteration 如何执行？]]
- [[GSPO#GSPO 为什么对长 CoT 与训推分离更稳定？|GSPO 为什么对长 CoT 与训推分离更稳定？]]
- [[GSPO#GSPO 为什么能消除 MoE 中这类 token-level routing 噪声对训练的影响？|GSPO 为什么能消除 MoE 中这类 token-level routing 噪声对训练的影响？]]
- [[GSPO#GSPO-token 是什么，它想恢复 GSPO 丢失的什么信息？|GSPO-token 是什么，它想恢复 GSPO 丢失的什么信息？]]
- [[GSPO#为什么 GSPO-token 必须有真正随 Token 变化的 Advantage？|为什么 GSPO-token 必须有真正随 Token 变化的 Advantage？]]
- [[GSPO#GSPO-token 如何结合 Sequence-level Importance Correction 与 Token-level Advantage？|GSPO-token 如何结合 Sequence-level Importance Correction 与 Token-level Advantage？]]
- [[GSPO#GSPO 相比 GRPO 做了什么取舍？|GSPO 相比 GRPO 做了什么取舍？]]
- [[GSPO#PPO、GRPO 与 GSPO 的核心演化关系是什么？|PPO、GRPO 与 GSPO 的核心演化关系是什么？]]

---

## GSPO 是什么，它主要解决 GRPO 的什么问题？

GSPO（Group Sequence Policy Optimization）由 Qwen 团队提出。它保留 GRPO 的 **Grouped Rollout 与 Group-relative Advantage**，但把 Policy Update 的核心约束从 Token-level 提升到 Sequence-level。

GRPO 的典型结构是：

> **Sequence-level Reward / Advantage + Token-level Importance Ratio / Clipping**

GSPO 则改为：

> **Sequence-level Reward / Advantage + Sequence-level Importance Ratio / Clipping**

因此 GSPO 的核心不是重新设计 Advantage，而是让 **Reward、Advantage 与 Policy Constraint 使用更一致的 Sequence 粒度**。Qwen 报告 GSPO 相比 GRPO 在长时间 RL 和 MoE 模型训练中具有更好的稳定性与可扩展性。参考：[GSPO: Towards Scalable Reinforcement Learning for Language Models](https://qwenlm.github.io/blog/gspo/)、[GSPO 论文](https://arxiv.org/abs/2507.18071)。

---

## GSPO 为什么把 Importance Ratio 从 Token-level 提升到 Sequence-level？

GRPO 对第 $i$ 条 Response 的每个 Token 都单独计算：

$$
\rho_{i,t}
=
\frac{
\pi_\theta(y_{i,t}\mid x,y_{i,<t})
}{
\pi_{old}(y_{i,t}\mid x,y_{i,<t})
}
$$

但同一条 Response 通常共享一个 Sequence-level Reward / Advantage：

$$
\hat A_i
$$

因此 GRPO 存在一种粒度不一致：

> **整条 Sequence 被统一评价，但 Policy Update 的稳定性却由每个 Token 各自决定。**

对于长 CoT、MoE 和训推分离系统，单 Token likelihood 容易受到数值精度、并行实现和 Expert Routing 波动影响。Token-level Ratio 会直接把这些局部波动带入 Clipping 与梯度。

GSPO 改为用整条 Sequence 的平均 likelihood shift 决定更新幅度，使局部 Token 波动不再单独决定 Policy Constraint。

---

## GSPO 的 Sequence-level Importance Ratio 如何计算？

对于 Response $y_i$，完整 Sequence 的 likelihood ratio 为：

$$
\frac{
\pi_\theta(y_i\mid x)
}{
\pi_{old}(y_i\mid x)
}
$$

由于自回归 Sequence Probability 是各 Token Probability 的乘积，直接使用完整乘积会随长度快速放大或缩小。GSPO 因此使用长度归一化后的 Sequence-level Importance Ratio：

$$
\boxed{
s_i(\theta)
=
\left(
\frac{
\pi_\theta(y_i\mid x)
}{
\pi_{old}(y_i\mid x)
}
\right)^{\frac{1}{|y_i|}}
}
$$

等价地：

$$
\boxed{
s_i(\theta)
=
\exp
\left[
\frac{1}{|y_i|}
\sum_{t=1}^{|y_i|}
\log
\frac{
\pi_\theta(y_{i,t}\mid x,y_{i,<t})
}{
\pi_{old}(y_{i,t}\mid x,y_{i,<t})
}
\right]
}
$$

它可以理解为：

> **新 Policy 相对 Old Policy 对整条 Response 的平均 Token likelihood 改变了多少。**

数学上，它等价于各 Token Importance Ratio 的几何平均。长度归一化能够降低不同 Response 长度带来的数值尺度差异。参考：[GSPO 论文](https://arxiv.org/abs/2507.18071)。

---

## GSPO 的 Clipping 与 GRPO 有什么区别？

GRPO 对每个 Token 的 Ratio 分别做 Clipping：

$$
\rho_{i,t}
\rightarrow
\operatorname{clip}
(\rho_{i,t},1-\epsilon,1+\epsilon)
$$

GSPO 则先得到每条 Response 唯一的 Sequence Ratio $s_i$，再在 Sequence level 做 Clipping：

$$
\boxed{
L_i^{GSPO}
=
\min
\left(
s_i\hat A_i,
\operatorname{clip}
(s_i,1-\epsilon,1+\epsilon)
\hat A_i
\right)
}
$$

因此 GSPO 的 Policy Constraint 可以理解为：

> **限制整条 Response 的平均 Policy Shift，而不是限制每一个 Token 的局部 Policy Shift。**

虽然 Ratio 与 Clipping 提升到了 Sequence level，梯度仍然会通过 $s_i$ 中的 Token log-probability 反向传播到所有生成 Token，因此 GSPO 并不是“不训练 Token”，而是改变了 Policy Update 的约束粒度。

---

## 一次完整 GSPO iteration 如何执行？

GSPO 与 GRPO 的前半段基本一致。

### Phase A：Grouped Rollout

对每个 Prompt 生成 $G$ 条 Response，并保存 Old Policy 对实际生成 Token 的 log-probability。

### Phase B：Reward 与 Group-relative Advantage

Reward System 对各 Response 评分，再按 Group 构造：

$$
\hat A_i
$$

这部分可以沿用 GRPO / Dr.GRPO 等 Group-relative Advantage 设计。

### Phase C：Sequence-level Policy Update

当前 Policy 在固定 Response 上重新计算 Token Log-probability：

$$
\log\pi_\theta(y_{i,t}\mid x,y_{i,<t})
$$

先计算各 Token 的 log-ratio：

$$
\Delta_{i,t}
=
\log\pi_\theta
-
\log\pi_{old}
$$

再沿 Sequence 求平均：

$$
\bar\Delta_i
=
\frac{1}{|y_i|}
\sum_t
\Delta_{i,t}
$$

最后：

$$
s_i
=
\exp(\bar\Delta_i)
$$

用 $s_i$ 与 $\hat A_i$ 进行 Sequence-level Clipping 和 Policy Update。

因此 GRPO 与 GSPO 最直接的工程差异可以概括为：

> **GRPO 的 Ratio Tensor 主要是 Token-level；GSPO 最终用于 Policy Objective 的 Ratio 是每条 Response 一个 Sequence-level Scalar。**

---

## GSPO 为什么对长 CoT 与训推分离更稳定？

长 CoT 中包含大量 Token，单个 Token 的 likelihood 容易出现局部异常。GRPO 的 Token-level Ratio 会把这些异常直接带入 Clipping，而 GSPO 先对整条 Sequence 的 log-ratio 做长度归一化平均：

$$
\frac{1}{|y_i|}
\sum_t
\left(
\log\pi_\theta
-
\log\pi_{old}
\right)
$$

局部的正负波动可以在 Sequence aggregation 中被平滑，因此 Policy Constraint 对单 Token 数值误差更不敏感。

这也使 GSPO 更适合 Rollout Engine 与 Training Engine 分离的系统：两个引擎之间轻微的 log-probability 数值差异不再逐 Token 直接决定 Clipping。Qwen 将这种更高的 precision tolerance 视为 GSPO 简化 RL infrastructure 的重要潜力。参考：[Qwen GSPO](https://qwenlm.github.io/blog/gspo/)。

---

## GSPO 为什么能消除 MoE 中这类 token-level routing 噪声对训练的影响？

MoE 的 Expert Routing 具有离散性和波动性。Rollout 与训练重新 Forward 时，只要个别 Token 激活了不同 Expert，其 Token likelihood 就可能明显变化；GRPO 的 Token-level Ratio 会直接把这种局部变化放大为异常 Ratio、Clipping 与梯度，从而破坏训练稳定性。

GSPO 改用**整条 Sequence 的长度归一化 likelihood ratio**。单个 Token 因 Routing 变化产生的 likelihood 波动只占 Sequence 平均的一小部分，不再直接决定该 Token 是否触发 Policy Clipping。因此这类 token-level routing noise 对优化信号的直接影响被显著削弱，Qwen 的实验中也因此无需 GRPO 所依赖的 Routing Replay 即可稳定训练 MoE。参考：[Qwen GSPO](https://qwenlm.github.io/zh/blog/gspo/)。

> **GSPO 不是让 MoE Routing 波动本身消失，而是让局部 Routing 波动不再直接支配 Policy Update。**

---

## GSPO-token 是什么，它想恢复 GSPO 丢失的什么信息？

GSPO 为了稳定训练，把 Importance Ratio 与 Clipping 提升到 Sequence level，但标准形式仍然让整条 Response 共用一个 Sequence-level Advantage：

$
\hat A_i
$

这会弱化 Sequence 内部不同 Token / Step 的 Credit Assignment。

GSPO-token 是 GSPO 论文提出的 token-level objective 扩展：**保留 GSPO 的 Sequence-level Importance Correction，同时允许使用真正随 Token 变化的 Advantage $\hat A_{i,t}$。**

因此它希望同时获得：

> **GSPO 的 Sequence-level 稳定性 + 更细粒度的 Token / Step Credit Assignment。**

当前 TRL 将 GSPO-token 放在实验性模块中，可通过 `importance_sampling_level="sequence_token"` 使用；实验 API 可能随版本变化，不应视为稳定生产接口。参考：[TRL Experimental - GSPO-token](https://huggingface.co/docs/trl/main/experimental)。

---

## 为什么 GSPO-token 必须有真正随 Token 变化的 Advantage？

GSPO-token 真正增加的信息来自：

$
\hat A_{i,t}
$

随 $t$ 改变。

如果仍然把同一条 Response 的 Sequence Advantage 广播到所有 Token：

$
\hat A_{i,t}
=
\hat A_i
$

那么 GSPO-token 的梯度与普通 GSPO 等价，并没有获得更细粒度的 Credit Assignment。

因此 GSPO-token 本身**不会自动解决 Credit Assignment**。真正的 Token / Step Advantage 还需要来自 Process Reward、Step Verifier、Turn-level Reward、Environment Feedback、Value Estimation 或 Reward Redistribution 等更细粒度反馈机制。TRL 当前文档也明确说明，只有提供随 Token 变化的 $\hat A_{i,t}$ 时 GSPO-token 才有实际区别。参考：[TRL Experimental - GSPO-token](https://huggingface.co/docs/trl/main/experimental)。

---

## GSPO-token 如何结合 Sequence-level Importance Correction 与 Token-level Advantage？

GSPO-token 仍以 GSPO 的 Sequence-level Ratio：

$
s_i(\theta)
$

作为整条 Response 的 Importance Correction，但通过 stop-gradient 技巧，让梯度能够按 Token 与对应的 $\hat A_{i,t}$ 结合。

可以把其设计直观理解为：

> **Sequence level 决定“这整条轨迹的 Policy Shift 应被整体放大或限制多少”；Token level 决定“轨迹内部每个 Token / Step 应承担多少 Credit”。**

因此它并不是重新回到 GRPO 的 Token-level Ratio，而是把两个粒度拆开：

| 维度 | GSPO | GSPO-token |
| --- | --- | --- |
| Importance Correction | Sequence-level | Sequence-level |
| Advantage | Sequence-level $\hat A_i$ | Token-level $\hat A_{i,t}$ |
| 主要目标 | 稳定 Policy Update | 稳定性 + 细粒度 Credit Assignment |

参考：[GSPO 论文](https://arxiv.org/abs/2507.18071)、[TRL Experimental - GSPO-token](https://huggingface.co/docs/trl/main/experimental)。

---

## GSPO 相比 GRPO 做了什么取舍？

GSPO 用更粗粒度的 Sequence-level Policy Constraint 换取稳定性。

GRPO 保留每个 Token 各自的 Importance Ratio，因此能够反映不同 Token 的局部 Policy Shift，但也更容易受到局部 likelihood noise 影响。

GSPO 把一整条 Response 压缩成一个 Sequence Ratio：

$$
s_i
$$

因此更加稳定，却会弱化“Sequence 内不同 Token 发生不同程度 Policy Shift”的细粒度信息。

可以概括为：

> **GRPO：更细粒度，但方差与噪声更大。**  
> **GSPO：更粗粒度，但 Sequence-level 稳定性更强。**

因此 Token-level 与 Sequence-level Policy Optimization 仍然是现代 RLVR 中一个持续演进的设计轴。

---

## PPO、GRPO 与 GSPO 的核心演化关系是什么？

三者可以沿两个问题理解：

| 方法 | Advantage / Baseline | Policy Constraint 粒度 |
| --- | --- | --- |
| **PPO** | Critic / Value + GAE | Token-level |
| **GRPO** | Group-relative Reward | Token-level |
| **GSPO** | Group-relative Reward | Sequence-level |

因此主要演化关系是：

> **PPO → GRPO：删除 Critic，用 Group-relative Advantage 替代 Learned Value Baseline。**

> **GRPO → GSPO：保留 Group-relative Advantage，把 Importance Ratio 与 Clipping 从 Token level 提升到 Sequence level。**

这使得 GSPO 可以理解为：

$$
\boxed{
\text{GSPO}
=
\text{GRPO-style Group Advantage}
+
\text{Sequence-level Policy Constraint}
}
$$

---

相关主题：[[LLM/后训练/RL-based Post-training/RL-based Post-training|RL-based Post-training]] · [[LLM/后训练/RL-based Post-training/PPO/PPO|PPO]] · [[LLM/后训练/RL-based Post-training/GRPO/GRPO|GRPO]] · [[LLM/后训练/RL-based Post-training/DHPO/DHPO|DHPO]] · [[推理能力]]
