# PPO

[[LLM/后训练/RL-based Post-training/RL-based Post-training|返回上级：RL-based Post-training]] · [[main|返回知识主干]]

围绕 Proximal Policy Optimization（PPO）的核心动机、Clipped Objective、Critic / GAE，以及在 LLM 后训练中的一次完整工程迭代整理 Q&A。

## 问题目录

- [[PPO#PPO 是什么，它主要解决什么问题？|PPO 是什么，它主要解决什么问题？]]
- [[PPO#PPO 中最核心的 Probability Ratio 与 Clipping 在做什么？|PPO 中最核心的 Probability Ratio 与 Clipping 在做什么？]]
- [[PPO#PPO 中的 Old Policy 与 Reference Policy 有什么区别？|PPO 中的 Old Policy 与 Reference Policy 有什么区别？]]
- [[PPO#Critic / Value Model 与 GAE 在 PPO 中做什么？|Critic / Value Model 与 GAE 在 PPO 中做什么？]]
- [[PPO#LLM PPO 一次完整 iteration 需要哪些模型与数据？|LLM PPO 一次完整 iteration 需要哪些模型与数据？]]
- [[PPO#LLM PPO 如何从 Sequence Reward 构造 Token-level Reward？|LLM PPO 如何从 Sequence Reward 构造 Token-level Reward？]]
- [[PPO#一次 PPO iteration 如何完整执行？|一次 PPO iteration 如何完整执行？]]
- [[PPO#一个简化的 PPO 工程伪代码是什么样的？|一个简化的 PPO 工程伪代码是什么样的？]]
- [[PPO#为什么同一批 Rollout 可以做多轮 PPO Epoch？|为什么同一批 Rollout 可以做多轮 PPO Epoch？]]
- [[PPO#PPO 的工程实现为什么比较重？|PPO 的工程实现为什么比较重？]]
- [[PPO#PPO 训练中应该监控哪些指标？|PPO 训练中应该监控哪些指标？]]

---

## PPO 是什么，它主要解决什么问题？

PPO（Proximal Policy Optimization）是一类 Policy Gradient 方法。它交替执行两件事：

1. 用当前 Policy 与环境交互并采集 Rollout；
2. 在这批 Rollout 上优化一个受约束的 surrogate objective。

普通 Policy Gradient 如果更新太小，学习速度很慢；更新太大，则新 Policy 可能迅速偏离采样数据对应的旧 Policy，导致训练不稳定。PPO 的核心思想就是：**利用已有 Rollout 做有效更新，但限制一次 Policy Update 不要走得太远。**

原始 PPO 工作的一个关键目标，是在保留类似 Trust Region 思想的同时，让实现比 TRPO 更简单，并允许同一批采样数据进行多个 minibatch epoch 的更新。参考：[Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347)。

对于 Policy $\pi_\theta$，基础目标可以写成：

$$
J(\theta)=\mathbb{E}_{\tau\sim\pi_\theta}[R(\tau)]
$$

Policy Gradient 则希望根据 Advantage $A_t$ 调整某个 Action 的生成概率：

$$
\nabla_\theta J
\approx
\mathbb{E}\left[
A_t\nabla_\theta\log\pi_\theta(a_t\mid s_t)
\right]
$$

其中：

- $A_t>0$：这个行为比预期更好，应提高其概率；
- $A_t<0$：这个行为比预期更差，应降低其概率。

PPO 的重点不是改变这个基本方向，而是**控制这种概率调整的幅度**。

---

## PPO 中最核心的 Probability Ratio 与 Clipping 在做什么？

Rollout 是由旧 Policy $\pi_{old}$ 产生的，而参数更新过程中当前 Policy $\pi_\theta$ 会不断变化。PPO 用 Probability Ratio 衡量某个已采样 Action 的概率变化：

$$
r_t(\theta)
=
\frac{
\pi_\theta(a_t\mid s_t)
}{
\pi_{old}(a_t\mid s_t)
}
$$

实际实现通常在 log-probability 空间计算：

$$
r_t(\theta)
=
\exp\left(
\log\pi_\theta(a_t\mid s_t)
-
\log\pi_{old}(a_t\mid s_t)
\right)
$$

如果直接最大化 $r_tA_t$，高 Advantage Action 的概率可能被一次推得过高，低 Advantage Action 的概率也可能被一次压得过低。PPO-Clip 因此使用：

$$
L^{CLIP}(\theta)
=
\mathbb{E}_t\left[
\min\left(
r_t(\theta)A_t,
\operatorname{clip}
\left(
r_t(\theta),1-\epsilon,1+\epsilon
\right)A_t
\right)
\right]
$$

当 $A_t>0$ 时，如果 $r_t$ 已经超过 $1+\epsilon$，继续提高这个 Action 的概率不会再获得额外 surrogate objective 收益；当 $A_t<0$ 时，如果 $r_t$ 已经低于 $1-\epsilon$，继续压低概率同样不会再被鼓励。

因此 Clipping 的直觉是：

> **好行为可以提高概率，坏行为可以降低概率，但一次不要改得太猛。**

需要注意，Clipping **并不硬性保证** $r_t$ 永远落在 $[1-\epsilon,1+\epsilon]$ 内。Ratio 仍然可以超出区间，只是 surrogate objective 不再继续奖励沿该方向的过度变化。因此 PPO-Clip 是一种 soft stabilization，而不是严格的 Trust Region Constraint。

---

## PPO 中的 Old Policy 与 Reference Policy 有什么区别？

在 LLM PPO / RLHF 中经常同时出现 $\pi_{old}$ 与 $\pi_{ref}$，两者用途不同。

### Old Policy

$\pi_{old}$ 是**生成当前 Rollout 时的 Policy 快照**，主要用于计算 PPO Ratio：

$$
r_t
=
\frac{\pi_\theta(a_t\mid s_t)}
{\pi_{old}(a_t\mid s_t)}
$$

工程中不一定真的复制一份 Old Policy。通常只需要在 Rollout 时保存：

$$
\log\pi_{old}(a_t\mid s_t)
$$

后续多轮 PPO Epoch 中保持这些 old log-probabilities 不变即可。

### Reference Policy

$\pi_{ref}$ 通常是 RL 阶段开始前冻结的 SFT / Instruction-tuned Model，用于长期约束 Actor 不要偏离原始可靠行为分布太远。

常见目标会加入 KL Penalty：

$$
\max_\theta
\;\mathbb{E}[R]
-
\beta D_{KL}(\pi_\theta\|\pi_{ref})
$$

因此可以这样理解：

| 对象 | 时间尺度 | 主要用途 |
| --- | --- | --- |
| $\pi_{old}$ | 当前 Rollout Batch | 控制单轮 PPO 更新幅度 |
| $\pi_{ref}$ | 整个 RL 阶段 | 作为长期行为锚点 |

PPO Ratio / Clip 解决的是“**这一轮别更新太猛**”，Reference KL 解决的是“**整个 RL 训练过程中别逐渐漂离原模型太远**”。

---

## Critic / Value Model 与 GAE 在 PPO 中做什么？

PPO 常采用 Actor-Critic 结构。

Actor 是 Policy：

$$
\pi_\theta(a_t\mid s_t)
$$

Critic 则估计当前状态未来能够获得的期望 Return：

$$
V_\phi(s_t)
\approx
\mathbb{E}[R\mid s_t]
$$

仅知道最终 Reward 还不够，因为 Policy Update 需要判断某个行为相对于“这个状态本来就能期待的结果”究竟好多少。Advantage 可以理解为：

> **这次行为的结果，相比当前状态下原本的预期表现好多少。**

经典形式为：

$$
A(s_t,a_t)=Q(s_t,a_t)-V(s_t)
$$

实际 PPO 中常使用 GAE（Generalized Advantage Estimation）估计 Advantage。先计算 TD Error：

$$
\delta_t
=
r_t
+
\gamma V(s_{t+1})
-
V(s_t)
$$

再从 trajectory 尾部向前递推：

$$
A_t
=
\delta_t
+
\gamma\lambda A_{t+1}
$$

最后构造 Critic 的训练目标 Return：

$$
Return_t=A_t+V(s_t)
$$

GAE 的作用可以概括为：**利用 Critic 把未来 Reward 信息分配回 trajectory 的各个时间步，并在 bias 与 variance 之间做折中。**

---

## LLM PPO 一次完整 iteration 需要哪些模型与数据？

经典 LLM RLHF / PPO 系统通常包含四类模型角色：

| 模型角色 | 是否训练 | 作用 |
| --- | --- | --- |
| **Actor / Policy** | 是 | 生成 Response，并接受 PPO 更新 |
| **Reference Policy** | 否 | 提供长期 KL 锚点 |
| **Reward Model / Verifier** | 否 | 给 Rollout 评分 |
| **Critic / Value Model** | 是 | 预测每个状态的 Value |

经典 InstructGPT 流程就是 SFT → Human Preference → Reward Model → PPO Policy Optimization。参考：[Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155)。

Rollout 后，一批 PPO Experience 通常至少保存：

- Prompt / Response；
- Response Mask；
- Old Log-probabilities；
- Reference Log-probabilities；
- Old Values；
- Token-level Rewards；
- Advantages；
- Returns。

若 Batch Size 为 $B$、Response 最大长度为 $T$，核心张量通常可以理解为：

$$
old\_logprobs,\ old\_values,\ rewards,\ advantages,\ returns
\in
\mathbb{R}^{B\times T}
$$

Response Mask 用来屏蔽 Prompt Token、EOS 后 Padding 等不参与 PPO Loss 的位置。

---

## LLM PPO 如何从 Sequence Reward 构造 Token-level Reward？

Reward Model 或 Verifier 往往只对完整 Response 给一个 Sequence-level Score：

$$
R_{task}
$$

但 PPO / GAE 需要沿 trajectory 处理 token-level 学习信号。

一种经典做法是先根据 Actor 与 Reference Policy 的 log-probability 差，对每个生成 Token 加入 KL Penalty：

$$
r_t^{KL}
=
-\beta
\left(
\log\pi_{old}(a_t\mid s_t)
-
\log\pi_{ref}(a_t\mid s_t)
\right)
$$

然后把最终任务 Reward 加在最后一个有效生成 Token 上：

$$
r_T
\leftarrow
r_T^{KL}+R_{task}
$$

前面的 Token 主要得到 KL shaping reward，最终 Token 再得到 Sequence Reward。随后再通过 Value Model 与 GAE，把末端 Reward 的影响传播回前面的生成步骤。

这里需要区分：

- **Task / RM Reward**：评价最终 Response 或任务结果；
- **KL Penalty**：限制 Policy 相对 Reference 的漂移；
- **Advantage**：最终用于 Policy Gradient 的相对学习信号。

---

## 一次 PPO iteration 如何完整执行？

一次完整 LLM PPO iteration 可以分成三个阶段。

### Phase A：Collect Experience

首先采样一批 Prompt，让当前 Actor 真正生成 Response：

> **Prompt → Actor Rollout → Response**

同时记录生成时的：

$$
\log\pi_{old}(a_t\mid s_t)
$$

然后对同一批固定 Response：

1. 用 Reference Policy 计算 $\log\pi_{ref}$；
2. 用 Reward Model / Verifier 计算 Sequence Reward；
3. 用 Critic 预测每个 Token State 的 Old Value；
4. 根据 Reward 与 KL 构造 Token-level Rewards。

这时并不更新参数。

### Phase B：Compute Learning Signal

根据 Token-level Reward 与 Old Value，从尾到头计算 GAE：

$$
\delta_t
=
r_t
+
\gamma V_{t+1}
-
V_t
$$

$$
A_t
=
\delta_t
+
\gamma\lambda A_{t+1}
$$

再得到：

$$
Return_t=A_t+V_t
$$

实际工程中常对有效 Token 的 Advantage 做 normalization / whitening，以降低不同 Batch 或 Token 间尺度差异。

### Phase C：PPO Update

Rollout 固定后，对 Experience 做若干 PPO Epoch。每个 Epoch 会 shuffle 数据并切成 minibatch。

对某个 minibatch：

1. Actor 在**固定的已采样 Response** 上重新 forward，不重新 generate；
2. 得到当前 $\log\pi_\theta$；
3. 计算 Ratio：

$$
r_t
=
\exp(
\log\pi_\theta
-
\log\pi_{old}
)
$$

4. 计算 Clipped Policy Objective；
5. Critic 重新 forward，得到新的 $V_\phi(s_t)$；
6. 用 Return 计算 Value Loss；
7. 合并 Actor / Critic Loss，执行 backward 与 optimizer step。

Critic 的朴素损失为：

$$
L_V
=
\left(
V_\phi(s_t)-Return_t
\right)^2
$$

PPO 工程实现中也常对 Value Update 做 clipping，避免 Critic 一次变化过大。

整个流程可以压缩为：

> **Rollout → Reward / KL → GAE → PPO Actor-Critic Update → 丢弃 Experience → 用更新后的 Actor 重新 Rollout**

---

## 一个简化的 PPO 工程伪代码是什么样的？

下面只保留核心数据流：

~~~python
actor = load_sft_model()
reference = deepcopy(actor).eval().freeze()

critic = load_value_model()
reward_model = load_reward_model().eval().freeze()

for iteration in range(num_iterations):

    # Phase A: rollout / collect experience
    prompts = sample_prompts()

    with torch.no_grad():
        responses = actor.generate(prompts)

        old_logprobs = actor.logprob(prompts, responses)
        ref_logprobs = reference.logprob(prompts, responses)
        old_values = critic(prompts, responses)

        task_scores = reward_model(prompts, responses)

        kl = old_logprobs - ref_logprobs
        token_rewards = -beta * kl
        token_rewards[:, last_valid_token] += task_scores

        advantages, returns = gae(
            rewards=token_rewards,
            values=old_values,
            gamma=gamma,
            lam=lam,
        )

        advantages = whiten(advantages)

    # Phase B/C: several PPO epochs on fixed experience
    for epoch in range(num_ppo_epochs):
        shuffle(experience)

        for minibatch in experience:

            new_logprobs = actor.logprob(prompts, responses)
            new_values = critic(prompts, responses)

            ratio = torch.exp(
                new_logprobs - old_logprobs
            )

            pg1 = ratio * advantages
            pg2 = torch.clamp(
                ratio,
                1 - clip_eps,
                1 + clip_eps,
            ) * advantages

            policy_loss = -masked_mean(
                torch.minimum(pg1, pg2)
            )

            value_loss = value_objective(
                new_values,
                old_values,
                returns,
            )

            loss = (
                policy_loss
                + value_coef * value_loss
            )

            optimizer.zero_grad()
            loss.backward()
            clip_grad_norm_(...)
            optimizer.step()

    # 当前 experience 到此失效
    # 下一 iteration 重新用更新后的 actor rollout
~~~

当前 Hugging Face TRL 的 PPO 实现仍体现这一基本结构，并保留 num_ppo_epochs、cliprange、cliprange_value、gamma、lam、kl_coef 等典型配置。参考：[TRL PPOConfig](https://github.com/huggingface/trl/blob/main/trl/experimental/ppo/ppo_config.py)。

---

## 为什么同一批 Rollout 可以做多轮 PPO Epoch？

普通 On-policy Policy Gradient 中，Policy 一旦更新，旧数据就会迅速变得过时。PPO 的 Clipped Objective 让同一批 Rollout 可以被有限度地重复利用。

一开始：

$$
r_t\approx 1
$$

随着多轮 PPO Epoch，$\pi_\theta$ 逐渐偏离生成这批数据时的 $\pi_{old}$，越来越多 Token 的 Ratio 会接近或越过 clipping boundary。此时继续沿相同方向优化的收益会被截断。

因此 PPO 形成一种：

> **On-policy + Limited Data Reuse**

的训练方式。

Old Log-probabilities、Old Values、Advantages 和 Returns 在当前 PPO Epoch 循环中保持固定；变化的是 Actor 与 Critic 的当前参数。多个 PPO Epoch 结束后，这批 Experience 被丢弃，下一轮重新 Rollout。

这也是 PPO 原论文相较最基础 Policy Gradient 的一个重要设计目标：允许同一批 sample 做多个 minibatch epoch。参考：[PPO 原论文](https://arxiv.org/abs/1707.06347)。

---

## PPO 的工程实现为什么比较重？

经典 LLM PPO 同时需要：

- Trainable Actor；
- Frozen Reference Policy；
- Reward Model / Verifier；
- Trainable Critic；
- Rollout Generation；
- KV Cache；
- Actor / Critic 的 Forward + Backward；
- Optimizer State 与分布式通信。

此外 Actor 同时承担两种工作负载：

1. **Rollout Phase**：高吞吐自回归生成；
2. **Training Phase**：需要梯度的 Forward / Backward。

两者对 GPU 内存和算子优化的需求不同，因此大规模 RL 系统常把 Rollout Workers 与 Training Workers 分离，并使用高吞吐 inference engine 生成 trajectory，再把 Experience 送给训练集群。

Critic 本身也是 PPO 的重要系统负担。它必须预测每个长生成前缀的 Value，如果 Value 估计不准，GAE 得到的 Advantage 也会变得噪声较大。

这正是后续理解 GRPO 的一个重要入口：**能否不训练独立 Critic，而用同一 Prompt 的多条 Rollout 之间的相对 Reward 构造 baseline？**

---

## PPO 训练中应该监控哪些指标？

不能只看训练 Reward。至少应同时监控：

| 指标 | 主要含义 |
| --- | --- |
| **Task / RM Reward** | 外部任务或偏好评价是否提高 |
| **Reference KL** | Actor 是否逐渐偏离 Reference Policy |
| **PPO Approx KL** | 当前 PPO Update 相对 Old Policy 是否过大 |
| **Clip Fraction** | 有多少 Token 触发 Ratio Clipping |
| **Policy Loss** | Actor 的优化状态 |
| **Value Loss** | Critic 是否能拟合 Return |
| **Value / Return Statistics** | Critic 估计是否合理 |
| **Entropy** | Policy 是否过早变得过于确定 |
| **Response Length** | 是否出现 Length Bias / Length Hacking |
| **EOS / Truncation Rate** | 生成是否正常结束 |

这里特别要区分两个 KL：

- **Reference KL**：Actor 与长期冻结的 $\pi_{ref}$ 的距离；
- **PPO Approx KL**：当前 $\pi_\theta$ 与产生本批 Rollout 的 $\pi_{old}$ 的更新幅度。

前者主要用于长期行为约束，后者主要用于判断单轮 PPO 更新是否过猛。

---

相关主题：[[LLM/后训练/RL-based Post-training/RL-based Post-training|RL-based Post-training]] · [[偏好学习]] · [[Reward Model（RM）]] · [[Reward Hacking]]
