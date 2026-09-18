# GRPO

[[LLM/后训练/RL-based Post-training/RL-based Post-training|返回上级：RL-based Post-training]] · [[main|返回知识主干]]

围绕 Group Relative Policy Optimization（GRPO）的核心机制、组内相对 Advantage、完整训练迭代，以及 Dr.GRPO 等针对原始目标函数的改进整理 Q&A。

## 问题目录

- [[GRPO#GRPO 是什么，它相对 PPO 改了什么？|GRPO 是什么，它相对 PPO 改了什么？]]
- [[GRPO#GRPO 如何利用同一 Prompt 的多条 Rollout 构造 Advantage？|GRPO 如何利用同一 Prompt 的多条 Rollout 构造 Advantage？]]
- [[GRPO#GRPO 如何进行 Policy Update？|GRPO 如何进行 Policy Update？]]
- [[GRPO#一次完整 GRPO iteration 如何执行？|一次完整 GRPO iteration 如何执行？]]
- [[GRPO#GRPO 相比 PPO 节省了什么，又付出了什么代价？|GRPO 相比 PPO 节省了什么，又付出了什么代价？]]
- [[GRPO#为什么组内 Reward 没有方差时，GRPO 几乎得不到学习信号？|为什么组内 Reward 没有方差时，GRPO 几乎得不到学习信号？]]
- [[GRPO#原始 GRPO 的 Group Reward 标准化为什么会产生 Difficulty Bias？|原始 GRPO 的 Group Reward 标准化为什么会产生 Difficulty Bias？]]
- [[GRPO#Dr.GRPO 如何修正 Group Reward 标准化带来的 Difficulty Bias？|Dr.GRPO 如何修正 Group Reward 标准化带来的 Difficulty Bias？]]
- [[GRPO#原始 GRPO 的 Sequence Length Normalization 为什么会产生 Length Bias？|原始 GRPO 的 Sequence Length Normalization 为什么会产生 Length Bias？]]
- [[GRPO#DAPO 与 Dr.GRPO 如何改进序列长度归一化？|DAPO 与 Dr.GRPO 如何改进序列长度归一化？]]
- [[GRPO#现代 GRPO 可以把哪些 Normalization 设计看成独立旋钮？|现代 GRPO 可以把哪些 Normalization 设计看成独立旋钮？]]
- [[GRPO#为什么 GRPO 的 Token-level Ratio 会导致 MoE Training Collapse？|为什么 GRPO 的 Token-level Ratio 会导致 MoE Training Collapse？]]
- [[GRPO#GRPO 还留下了什么结构性问题？|GRPO 还留下了什么结构性问题？]]

---

## GRPO 是什么，它相对 PPO 改了什么？

GRPO（Group Relative Policy Optimization）最早由 DeepSeekMath 提出，是 PPO 的一个变体。它保留了 Policy Rollout、Importance Ratio、Clipping 和 Policy Update 等 PPO 核心机制，但**不再训练独立 Critic / Value Model**，而是通过同一个 Prompt 下多条 Rollout 的相对 Reward 构造 Advantage。原始工作将减少 PPO 中 Value Model 带来的显存和计算开销作为主要动机之一。参考：[DeepSeekMath](https://arxiv.org/abs/2402.03300)。

PPO 的核心链路可以简化为：

> **Reward → Critic / Value → GAE → Advantage → PPO Clip**

GRPO 则变为：

> **同一 Prompt 的 Group Rollouts → Group-relative Reward → Advantage → PPO-style Clip**

因此 GRPO 最关键的结构变化是：

$$
\boxed{\text{删除 Critic / Value Model，用 Group Baseline 代替 Learned Value Baseline}}
$$

它并不是把 PPO 完全替换成另一类训练方法。GRPO 仍然属于 Policy Optimization，只是重新设计了 Advantage 的构造方式。

---

## GRPO 如何利用同一 Prompt 的多条 Rollout 构造 Advantage？

对于一个 Prompt $q$，当前 Policy 一次生成 $G$ 条 Response：

$$
o_1,o_2,\ldots,o_G
$$

Reward System 分别给出：

$$
r_1,r_2,\ldots,r_G
$$

原始 GRPO 先计算组内 Reward 均值与标准差：

$$
\mu_q
=
\frac{1}{G}
\sum_{i=1}^{G}r_i
$$

$$
\sigma_q
=
\operatorname{Std}(r_1,\ldots,r_G)
$$

再得到每条 Response 的 Group-relative Advantage：

$$
\hat A_i
=
\frac{
r_i-\mu_q
}{
\sigma_q+\epsilon
}
$$

例如同一道题生成四条 Response，Reward 为：

$$
[1,1,0,0]
$$

则组内均值为 $0.5$。若标准差按 $0.5$ 计算，则得到：

$$
[1,1,-1,-1]
$$

于是：

- 高于同组平均水平的 Response 得到正 Advantage；
- 低于同组平均水平的 Response 得到负 Advantage。

这里的 baseline 不再来自 Learned Critic，而来自**同一问题下其他 Rollout 的实际 Reward**。

对于典型 Outcome-based GRPO，同一条 Response 的 Sequence-level Advantage 通常会应用到其全部有效生成 Token。也就是说，一条最终高 Reward 的轨迹整体被强化，一条低 Reward 轨迹整体被压低。这比 PPO 的 Critic + GAE Credit Assignment 更粗粒度，但在 Math / Code 等 Outcome 容易验证的 Reasoning 场景中可以非常有效。

---

## GRPO 如何进行 Policy Update？

GRPO 并没有删除 PPO 中的 Importance Ratio 与 Clipping。

对于第 $i$ 条 Response 的第 $t$ 个 Token：

$$
\rho_{i,t}(\theta)
=
\frac{
\pi_\theta(o_{i,t}\mid q,o_{i,<t})
}{
\pi_{old}(o_{i,t}\mid q,o_{i,<t})
}
$$

原始 GRPO 仍采用 PPO-style clipped surrogate：

$$
\min\left(
\rho_{i,t}\hat A_i,
\operatorname{clip}
\left(
\rho_{i,t},1-\epsilon,1+\epsilon
\right)\hat A_i
\right)
$$

其直觉仍然与 PPO 一致：

> **提高高 Advantage Response 中已采样 Token 的概率，降低低 Advantage Response 中 Token 的概率，但限制单轮 Policy Update 不要过大。**

原始 GRPO 还可以加入相对 Reference Policy 的 KL Regularization。现代实现中是否使用 Reference KL 是可选设计，而不是 GRPO“删除 Critic”这一核心定义的一部分。参考：[DeepSeekMath](https://arxiv.org/abs/2402.03300)、[TRL GRPO Trainer](https://huggingface.co/docs/trl/grpo_trainer)。

---

## 一次完整 GRPO iteration 如何执行？

假设 Prompt Batch Size 为 $B$，每个 Prompt 采样 $G$ 条 Response，则一次 Rollout 会产生约 $B\times G$ 条 completion。

完整流程可以分成三步。

### Phase A：Grouped Rollout

对每个 Prompt 复制 $G$ 份，用当前 Policy 生成多条 Response：

> **Prompt → $G$ 条 Rollout → Reward / Verifier**

同时保存生成这些 Response 时的 Old Log-probabilities：

$$
\log\pi_{old}(o_{i,t}\mid q,o_{i,<t})
$$

Reward 通常是 Sequence-level 的，可以来自 Rule、Verifier、Reward Model 或 Environment。

### Phase B：Group-relative Advantage

把 Reward 按 Prompt 分组，得到形如：

$$
[B,G]
$$

的 Reward Tensor。

原始 GRPO 在每个 Group 内计算均值与标准差，并得到：

$$
\hat A_i
=
\frac{r_i-\mu_q}{\sigma_q+\epsilon}
$$

这些 Sequence-level Advantage 再应用到对应 Response 的有效 Token。

这里没有：

- Critic Forward；
- Old Value；
- GAE；
- Return；
- Value Loss。

### Phase C：Policy Update

对固定 Rollout 重新计算当前 Policy 的 New Log-probabilities：

$$
\log\pi_\theta
$$

再计算：

$$
\rho_{i,t}
=
\exp
\left(
\log\pi_\theta
-
\log\pi_{old}
\right)
$$

使用 PPO-style Clipping 构造 Policy Loss，并进行 Backward / Optimizer Step。

核心伪代码可以简化为：

~~~python
for step in training:

    prompts = sample_prompt_batch()

    completions = policy.generate(
        repeat_each(prompts, G)
    )

    old_logprobs = policy.logprob(
        prompts,
        completions
    ).detach()

    rewards = reward_fn(
        prompts,
        completions
    )

    grouped_rewards = rewards.reshape(B, G)

    group_mean = grouped_rewards.mean(dim=1)
    group_std = grouped_rewards.std(dim=1)

    advantages = (
        grouped_rewards
        - group_mean[:, None]
    ) / (
        group_std[:, None] + eps
    )

    token_advantages = broadcast_to_tokens(
        advantages
    )

    new_logprobs = policy.logprob(
        prompts,
        completions
    )

    ratio = torch.exp(
        new_logprobs - old_logprobs
    )

    unclipped = ratio * token_advantages

    clipped = (
        torch.clamp(
            ratio,
            1 - clip_eps,
            1 + clip_eps,
        )
        * token_advantages
    )

    policy_loss = -masked_mean(
        torch.minimum(
            unclipped,
            clipped,
        )
    )

    optimizer.zero_grad()
    policy_loss.backward()
    optimizer.step()
~~~

实际现代实现还会加入分布式 Rollout、Reference KL、不同 Loss Aggregation、Off-policy Correction 等机制，但上面已经包含原始 GRPO 的核心结构。

---

## GRPO 相比 PPO 节省了什么，又付出了什么代价？

PPO 与 GRPO 的主要差别可以概括为：

| 维度 | PPO | GRPO |
| --- | --- | --- |
| Baseline | Learned Critic / Value Model | 同 Prompt 的 Group Reward |
| Advantage | Critic + GAE | Group-relative Reward |
| Critic | 需要 | 不需要 |
| Value Loss | 有 | 无 |
| 每个 Prompt | 可以采一条或多条 | 通常需要多条 Rollout |
| Credit Assignment | 可做 state / token-level 估计 | 主要是 sequence-level 相对信号 |
| 主要额外成本 | Critic Training | 更多 Rollout Generation |

因此 GRPO 不是单纯“更便宜的 PPO”，而是一次资源交换：

> **删除 Critic 的训练和显存成本，换成同一 Prompt 更多 Monte Carlo Rollout。**

对于长 CoT、大模型 Reasoning RL，Critic 很昂贵，而 Math / Code 又能够廉价验证多个候选结果，因此这种交换尤其有吸引力。

---

## 为什么组内 Reward 没有方差时，GRPO 几乎得不到学习信号？

GRPO 依赖同组 Rollout 之间的相对 Reward。

如果一道题太容易：

$$
[1,1,1,1,1,1,1,1]
$$

所有 Response 都和组内均值相同，因此：

$$
r_i-\mu_q=0
$$

如果一道题太难：

$$
[0,0,0,0,0,0,0,0]
$$

同样没有相对差异。

因此 GRPO 最有信息量的 Prompt 往往是：

> **当前 Policy 有时能做对、有时会做错的中等难度任务。**

这意味着 Prompt Difficulty、Dynamic Sampling、Curriculum 和 Reward Variance 本身都是 GRPO 数据工程的重要问题。当前 TRL 也提供组内 Reward 标准差、零方差比例等监控指标，用于识别无法提供 Group-relative Signal 的 Prompt。参考：[TRL GRPO Trainer](https://huggingface.co/docs/trl/grpo_trainer)。

---

## 原始 GRPO 的 Group Reward 标准化为什么会产生 Difficulty Bias？

原始 GRPO 使用：

$$
\hat A_i
=
\frac{
r_i-\mu_q
}{
\sigma_q
}
$$

问题不在于减去 Group Mean，而在于每道题都使用自己的 $\sigma_q$ 做缩放。

对于二值 Reward $r\in\{0,1\}$，假设当前 Policy 在某道题上的成功率为 $p$，则：

$$
\mu=p
$$

$$
\sigma=\sqrt{p(1-p)}
$$

正确样本的 Advantage 为：

$$
A_+
=
\frac{1-p}{\sqrt{p(1-p)}}
=
\sqrt{\frac{1-p}{p}}
$$

错误样本则为：

$$
A_-
=
-\sqrt{\frac{p}{1-p}}
$$

当问题非常难、$p$ 很小时，罕见正确样本会因为较小的 Group Std 被额外放大；当问题非常容易、$p$ 接近 $1$ 时，罕见错误样本也会被额外放大。

因此每个 Prompt 自己的 Reward Variance 实际成为一个隐式的 Question Weight：

> **梯度大小不仅由 Response 相对组内平均水平的好坏决定，还受到该 Prompt 当前难度的额外调制。**

Dr.GRPO 将这一现象分析为 Question-level Difficulty Bias。参考：[Understanding R1-Zero-Like Training: A Critical Perspective](https://arxiv.org/abs/2503.20783)。

---

## Dr.GRPO 如何修正 Group Reward 标准化带来的 Difficulty Bias？

Dr.GRPO 的改动非常直接：保留 Group-relative Centering，但取消 Group Std Scaling。

原始 GRPO：

$$
\hat A_i^{GRPO}
=
\frac{
r_i-\mu_q
}{
\sigma_q
}
$$

Dr.GRPO：

$$
\boxed{
\hat A_i^{Dr.GRPO}
=
r_i-\mu_q
}
$$

例如：

$$
[1,0,0,0]
$$

组内均值为：

$$
\mu=0.25
$$

则 Advantage 直接为：

$$
[0.75,-0.25,-0.25,-0.25]
$$

罕见正确样本仍然比其他样本获得更强正信号，但不再因为 $\sigma_q$ 很小而被额外放大。

因此这一改进可以概括为：

> **保留 Group-relative Baseline，删除 Per-question Variance Reweighting。**

现代工程实现还可以使用 Batch-level Std 作为统一缩放尺度，在保持整体数值稳定的同时避免每个 Prompt 各自改变梯度尺度。当前 TRL 将 Group Std、Batch Std 和 No Scaling 暴露为独立选项，并明确标注 Dr.GRPO 推荐取消 Group Std Scaling。参考：[TRL GRPO Trainer](https://huggingface.co/docs/trl/grpo_trainer)。

---

## 原始 GRPO 的 Sequence Length Normalization 为什么会产生 Length Bias？

原始 GRPO 对每条 Response 先按自身长度平均 Token Loss，再对 Group 内 Response 平均：

$$
L_{GRPO}
=
-
\frac{1}{G}
\sum_{i=1}^{G}
\frac{1}{|o_i|}
\sum_{t=1}^{|o_i|}
l_{i,t}
$$

其中 $l_{i,t}$ 表示第 $i$ 条 Response、第 $t$ 个 Token 对 Policy Objective 的贡献。

这个形式等价于让**每条 Response 整体等权**。因此对于长度为 $|o_i|$ 的 Response，每个 Token 的有效权重近似与：

$$
\frac{1}{|o_i|}
$$

成正比。

假设两条成功 Response 的 Advantage 都是正的：

- Response A：100 Token；
- Response B：1000 Token。

原始 GRPO 中，A 的单 Token 权重大约是 B 的十倍。于是短的 Positive Response 会受到更强的逐 Token 强化。

反过来，对负 Advantage Response，长 Response 的每个 Token 又会受到更弱的惩罚。

因此会形成：

> **短 Positive Response 被更强强化，长 Negative Response 被更弱惩罚。**

这就是原始 GRPO 的 Response Length Bias。现代 TRL 文档也已经明确不推荐原始 sequence-level normalization 用于长 CoT GRPO。参考：[TRL GRPO Trainer](https://huggingface.co/docs/trl/grpo_trainer)。

---

## DAPO 与 Dr.GRPO 如何改进序列长度归一化？

### DAPO：按全局 Active Token 做归一化

DAPO 并不是简单的“GRPO 小改版”，它是一套更完整的大规模 RL recipe；这里仅摘录它与 GRPO **Sequence Length Normalization** 直接相关的改动。

DAPO 将原始：

$$
-
\frac{1}{G}
\sum_i
\frac{1}{|o_i|}
\sum_t l_{i,t}
$$

改为：

$$
\boxed{
L_{DAPO}
=
-
\frac{
\sum_i\sum_t l_{i,t}
}{
\sum_i|o_i|
}
}
$$

也就是：

> **不再让每条 Response 自己除以长度，而是把当前全局累计 Batch 中所有有效 Token 放在一起平均。**

这样每个 Active Token 在当前 Batch 中拥有相同权重，减少了原始 GRPO 因“每条 Sequence 整体等权”导致的 Length Bias。

这一机制在 DAPO 中被称为 Token-level Policy Gradient Loss。DAPO 本身还包含 Decoupled Clip、Dynamic Sampling、Overlong Reward Shaping 等其他设计，后续应单独讨论，不在 GRPO 笔记中展开。参考：[DAPO: An Open-Source LLM Reinforcement Learning System at Scale](https://arxiv.org/abs/2503.14476)。完整 DAPO Recipe 见 [[LLM/后训练/RL-based Post-training/DAPO/DAPO|DAPO]]。

### Dr.GRPO：使用固定常数归一化

Dr.GRPO 进一步指出，即使使用：

$$
\sum_i |o_i|
$$

作为 denominator，梯度尺度仍然与当前 Batch 实际采样出的 Response Length 分布耦合。

因此它使用固定常数：

$$
\boxed{
L_{Dr.GRPO}
=
-
\frac{1}{LG}
\sum_{i=1}^{G}
\sum_{t=1}^{|o_i|}
l_{i,t}
}
$$

其中 $L$ 通常取最大 completion 长度，$G$ 为 Group Size。

这样 denominator 不再依赖本次 Rollout 实际生成了多少 Token，使 gradient scale 与 sampled response length 进一步解耦。

参考：[Dr.GRPO](https://arxiv.org/abs/2503.20783)。

因此三种形式可以概括为：

| 方法 | Normalization | 直觉 |
| --- | --- | --- |
| **原始 GRPO** | 每条 Response 除自身长度 | 每条 Sequence 整体等权 |
| **DAPO 摘录** | 除全局 Active Token 数 | 当前 Batch 每个 Token 等权 |
| **Dr.GRPO** | 除固定 $L\times G$ | Token 尺度不随实际采样长度变化 |

当前 TRL 已把这些 Loss Aggregation 形式暴露为不同 loss type；这是现代实现对这些研究改进的直接工程映射。参考：[TRL GRPO Trainer](https://huggingface.co/docs/trl/grpo_trainer)。

---

## 现代 GRPO 可以把哪些 Normalization 设计看成独立旋钮？

GRPO 中至少有两个容易混在一起、但实际上正交的设计位置。

### 1. Advantage Scaling

决定：

> **Group Reward 如何变成 Advantage？**

典型选择包括：

原始 GRPO：

$$
\frac{r_i-\mu_{group}}{\sigma_{group}}
$$

Dr.GRPO：

$$
r_i-\mu_{group}
$$

也可以采用统一 Batch Std 做全局尺度控制。

### 2. Loss Aggregation

决定：

> **各 Token 的 Policy Loss 最后怎样聚合成 Batch Loss？**

典型形式包括：

- 原始 GRPO：按每条 Response 长度归一化；
- DAPO：按全局 Active Token 数归一化；
- Dr.GRPO：按固定 $L\times G$ 归一化。

因此：

> **Reward / Advantage 的 Normalization 与 Token Loss 的 Aggregation 是两个不同问题。**

现代实现完全可以组合：

- No Group-Std Scaling + DAPO-style Token Aggregation；
- No Group-Std Scaling + Dr.GRPO Fixed Aggregation；

而不需要把这些设计机械绑定为单一算法。

---

## 为什么 GRPO 的 Token-level Ratio 会导致 MoE Training Collapse？

MoE 的 Expert Routing 具有离散性和波动性。Rollout 与训练重新 Forward 时，如果个别 Token 激活了不同 Expert，其 Token likelihood 可能明显变化；GRPO 又直接使用每个 Token 的 Importance Ratio 做 Clipping，因此这些局部 Routing 差异会被放大为异常 Ratio、过度 Clipping 和噪声梯度。

当这种 train-inference routing mismatch 在大量 Token 上持续累积时，有效 Policy Update 会被严重干扰，训练可能无法正常收敛甚至发生 collapse。Qwen 团队因此在 GRPO 训练 MoE 时曾使用 Routing Replay 缓解该问题。参考：[Qwen GSPO](https://qwenlm.github.io/zh/blog/gspo/)。

相关改进：[[LLM/后训练/RL-based Post-training/GSPO/GSPO#GSPO 为什么能消除 MoE 中这类 token-level routing 噪声对训练的影响？|GSPO 为什么能消除这种噪声的影响？]]

---

## GRPO 还留下了什么结构性问题？

即使修正 Difficulty Bias 与 Length Bias，经典 GRPO 仍保留一个更结构性的张力：

> **Reward / Advantage 通常是 Sequence-level，但 Importance Ratio 与 Clipping 仍然发生在 Token-level。**

也就是说，一整条 Response 因最终结果获得一个共同 Advantage：

$$
\hat A_i
$$

但 Policy Stability 是通过每个 Token 各自的：

$$
\rho_{i,t}
$$

和 Clipping 来控制。

对于很长的 CoT、MoE 模型以及 Long-horizon Agent Trajectory，这种“Sequence-level Evaluation + Token-level Optimization”是否最合适，会进一步影响训练稳定性和优化语义。

这个问题已经超出了单纯修改 Normalization 的范围，详见 [[LLM/后训练/RL-based Post-training/GSPO/GSPO|GSPO]]。

---

相关主题：[[LLM/后训练/RL-based Post-training/RL-based Post-training|RL-based Post-training]] · [[LLM/后训练/RL-based Post-training/PPO/PPO|PPO]] · [[LLM/后训练/RL-based Post-training/GSPO/GSPO|GSPO]] · [[LLM/后训练/RL-based Post-training/DAPO/DAPO|DAPO]] · [[LLM/后训练/RL-based Post-training/DHPO/DHPO|DHPO]] · [[Reward Hacking]] · [[推理能力]]
