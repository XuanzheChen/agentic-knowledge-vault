# DAPO

[[LLM/后训练/RL-based Post-training/RL-based Post-training|返回上级：RL-based Post-training]] · [[main|返回知识主干]]

围绕 DAPO（Decoupled Clip and Dynamic sAmpling Policy Optimization）的核心动机、四项训练设计，以及它与 GRPO / Dr.GRPO / GSPO 的关系整理 Q&A。

## 问题目录

- [[DAPO#DAPO 是什么，它和 GRPO 是什么关系？|DAPO 是什么，它和 GRPO 是什么关系？]]
- [[DAPO#DAPO 为什么要使用 Clip-Higher？|DAPO 为什么要使用 Clip-Higher？]]
- [[DAPO#DAPO 的 Dynamic Sampling 在解决什么问题？|DAPO 的 Dynamic Sampling 在解决什么问题？]]
- [[DAPO#Dynamic Sampling 为什么可以看作一种在线 Curriculum？|Dynamic Sampling 为什么可以看作一种在线 Curriculum？]]
- [[DAPO#DAPO 为什么改用 Token-level Policy Gradient Loss？|DAPO 为什么改用 Token-level Policy Gradient Loss？]]
- [[DAPO#DAPO 的 Token-level PG Loss 与 GSPO 的 Sequence-level Ratio 是一回事吗？|DAPO 的 Token-level PG Loss 与 GSPO 的 Sequence-level Ratio 是一回事吗？]]
- [[DAPO#Overlong Reward Shaping 在解决什么问题？|Overlong Reward Shaping 在解决什么问题？]]
- [[DAPO#一次完整 DAPO iteration 如何执行？|一次完整 DAPO iteration 如何执行？]]
- [[DAPO#DAPO 与 Dr.GRPO、GSPO 的关系是什么？|DAPO 与 Dr.GRPO、GSPO 的关系是什么？]]
- [[DAPO#为什么 DAPO 更像一套 Reasoning RL Recipe，而不是单一公式改动？|为什么 DAPO 更像一套 Reasoning RL Recipe，而不是单一公式改动？]]

---

## DAPO 是什么，它和 GRPO 是什么关系？

DAPO 全称 **Decoupled Clip and Dynamic sAmpling Policy Optimization**。它不是只针对 GRPO 某一个公式做局部修补，而是一套面向大规模 Long-CoT Reasoning RL 的完整训练 Recipe。

DAPO 延续了 GRPO 的基本骨架：

- 同一个 Prompt 采样多条 Rollout；
- 使用 Group-relative Advantage；
- 不依赖独立 Critic / Value Model；
- 使用 Token-level Importance Ratio 与 PPO-style Clipping 更新 Policy。

在此基础上，DAPO针对大规模训练中的实际问题加入四项主要设计：

| 问题 | DAPO 设计 | 修改位置 |
| --- | --- | --- |
| Entropy Collapse / Exploration 不足 | **Clip-Higher** | Policy Update |
| 全对 / 全错 Group 没有学习信号 | **Dynamic Sampling** | Rollout / Data |
| 长 Response 的 Token 梯度被稀释 | **Token-level Policy Gradient Loss** | Loss Aggregation |
| 截断造成错误 Reward | **Overlong Reward Shaping** | Reward |

DAPO 论文在 Qwen2.5-32B Base 上展示了这些机制组合对大规模 Reasoning RL 的效果。参考：[DAPO: An Open-Source LLM Reinforcement Learning System at Scale](https://arxiv.org/abs/2503.14476)。

> **DAPO 更适合被理解为一组经过验证的 Reasoning RL 训练组合，而不是“GRPO 的单一后继算法”。**

---

## DAPO 为什么要使用 Clip-Higher？

PPO / GRPO 常使用对称 Clipping：

$$
\rho_t
\in
[1-\epsilon,1+\epsilon]
$$

DAPO 观察到，大规模 Reasoning RL 中 Policy 容易逐渐变得过于确定，生成熵下降，Rollout Diversity 随之缩小，形成 **Entropy Collapse**。

尤其对原本概率很低、但偶然产生高 Reward 的探索性 Token，如果 Upper Clip 太紧，即使其 Advantage 为正，单轮训练也只能把其 Probability 提高有限比例，使新探索策略难以快速进入主分布。

因此 DAPO 将上下边界解耦：

$$
\boxed{
\rho_t
\in
[
1-\epsilon_{low},
1+\epsilon_{high}
]
}
$$

并设置：

$$
\epsilon_{high}>
\epsilon_{low}
$$

论文中的典型配置为：

$$
\epsilon_{low}=0.2,
\qquad
\epsilon_{high}=0.28
$$

其核心直觉是：

> **给高 Reward、低概率的新行为更多上升空间，同时不要过快把低概率行为彻底压到接近零。**

这就是 DAPO 名字中的 **Decoupled Clip / Clip-Higher**。参考：[DAPO](https://arxiv.org/abs/2503.14476)。

---

## DAPO 的 Dynamic Sampling 在解决什么问题？

GRPO 依赖同一 Prompt 的多条 Rollout 之间存在 Reward 差异。

如果一组 Rollout 全部正确：

$$
[1,1,1,1]
$$

或者全部错误：

$$
[0,0,0,0]
$$

则 Group-relative Advantage 几乎为零，无法提供有效梯度。

随着模型训练变强，越来越多简单 Prompt 会变成“全对”；在模型较弱或题目很难时，又可能出现大量“全错”。如果这些 Group 仍然占据固定训练 Batch，就会造成大量无效训练样本。

DAPO 因此采用 **Dynamic Sampling**：

> **先过量生成 Prompt Group，只保留组内 Reward 有差异的 Group，直到凑够目标有效训练 Batch。**

对于二值正确性 Reward，典型筛选条件可写为：

$$
\boxed{
0<
\#\text{correct}
<
G
}
$$

也就是同一 Prompt 的 $G$ 条 Rollout 中：

- 至少一个正确；
- 至少一个错误。

这样真正进入 Policy Update 的 Group 都能够产生相对学习信号。参考：[DAPO](https://arxiv.org/abs/2503.14476)。

---

## Dynamic Sampling 为什么可以看作一种在线 Curriculum？

Dynamic Sampling 并没有预先给每道题标记固定难度，而是让**当前 Policy 的实际成功率**决定该 Prompt 是否进入训练。

对于当前模型：

- 太容易的 Prompt：几乎全部做对，被过滤；
- 太难的 Prompt：几乎全部做错，被过滤；
- 能力边界附近的 Prompt：有对有错，被保留。

因此随着 Policy 能力变化，真正进入训练的 Prompt 分布也会不断变化。

可以把它理解为：

$$
\boxed{
\text{Model-dependent Online Curriculum}
}
$$

模型主要在“**已经有可能解决，但还没有稳定掌握**”的任务上获得 GRPO-style 相对学习信号。

代价是 Dynamic Sampling 会增加 Rollout 开销，因为被过滤掉的 Group 已经完成了生成与 Reward Evaluation，因此工程上需要关注 Valid Group Ratio、Resampling Rate 与 Generation Throughput。

---

## DAPO 为什么改用 Token-level Policy Gradient Loss？

原始 GRPO 通常先对每条 Response 内的 Token Loss 求平均，再对各 Response 求平均：

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

这相当于让每条 Response 整体等权。于是 Response 越长，每个 Token 的有效权重越小。

在 Long-CoT 场景中，这会导致：

- 高质量的长 Reasoning 中，每个有价值 Token 的强化被稀释；
- 低质量的长 Response 中，大量无效 Token 的惩罚也被稀释。

DAPO 改为对当前全局训练 Batch 的所有有效 Token 一起平均：

$$
\boxed{
L_{DAPO}
=
-
\frac{
\sum_i\sum_t l_{i,t}
}{
\sum_i |o_i|
}
}
$$

即：

> **每个 Active Token 在当前 Batch 中具有相同权重，而不是每条 Sequence 整体等权。**

DAPO 将这一机制称为 **Token-level Policy Gradient Loss**。参考：[DAPO](https://arxiv.org/abs/2503.14476)。

这一设计也是 DAPO 与 GRPO 的 Sequence Length Normalization 问题直接相交的部分，相关对比见 [[LLM/后训练/RL-based Post-training/GRPO/GRPO#DAPO 与 Dr.GRPO 如何改进序列长度归一化？|GRPO 中的长度归一化改进]]。

---

## DAPO 的 Token-level PG Loss 与 GSPO 的 Sequence-level Ratio 是一回事吗？

不是。两者修改的是完全不同的位置。

DAPO 的 Token-level Policy Gradient Loss 修改：

> **Token Loss 最后怎样聚合成 Batch Loss。**

DAPO 仍然使用 Token-level Importance Ratio：

$$
\rho_{i,t}
=
\frac{
\pi_\theta(o_{i,t}\mid\cdots)
}{
\pi_{old}(o_{i,t}\mid\cdots)
}
$$

并在 Token level 做 Clipping。

GSPO 修改的则是：

> **Importance Ratio 与 Policy Constraint 在哪个粒度计算。**

GSPO 将多个 Token 的 log-ratio 聚合成 Sequence-level Ratio，再进行 Sequence-level Clipping。

因此可以概括为：

| 设计 | DAPO | GSPO |
| --- | --- | --- |
| Advantage | Group-relative | Group-relative |
| Importance Ratio | Token-level | Sequence-level |
| Clipping | Token-level | Sequence-level |
| Loss Aggregation | Global Active-token Mean | Sequence-level Policy Objective |

> **DAPO 的“Token-level”主要指 Loss Aggregation；GSPO 的“Sequence-level”主要指 Importance Ratio / Policy Constraint。**

---

## Overlong Reward Shaping 在解决什么问题？

Long-CoT RL 通常会设置最大生成长度 $L_{max}$。如果 Response 在达到长度上限时仍未结束，它会被截断。

若直接把所有截断 Response 当作“答案错误”并赋予强负 Reward，就会产生 Reward Noise：

> 一条 trajectory 可能前面的推理基本正确，只是因为计算过程过长而未能在 Token Budget 内结束；如果直接给最低正确性 Reward，模型会把“推理过长”和“推理错误”混为一谈。

DAPO 因此把长度限制引入 Reward Shaping。

一种典型 Soft Overlong Punishment 可写为：

$$
R_{length}(y)
=
\begin{cases}
0,
&
|y|\le L_{max}-L_{cache}
\\[6pt]
\dfrac{
(L_{max}-L_{cache})-|y|
}{
L_{cache}
},
&
L_{max}-L_{cache}<|y|\le L_{max}
\\[10pt]
-1,
&
|y|>L_{max}
\end{cases}
$$

其作用是：

- 在正常长度范围内不惩罚；
- 接近长度上限时逐渐增加负 Reward；
- 超过上限时给予最大长度惩罚。

这样模型得到的是一个更平滑的信号：

> **“推理可能是对的，但计算预算正在超限。”**

而不是在截断位置突然把整条 trajectory 判为完全错误。

DAPO 论文也讨论了直接过滤 Overlong Sample 与 Soft Overlong Punishment 等策略。参考：[DAPO](https://arxiv.org/abs/2503.14476)。

---

## 一次完整 DAPO iteration 如何执行？

DAPO 可以看成在 GRPO Backbone 上加入四类工程机制：

> **Prompt Pool → Over-sampling → Grouped Rollout → Reward / Verifier → Overlong Reward Shaping → Dynamic Sampling → Group-relative Advantage → Token-level Ratio → Clip-Higher → Global Active-token Loss → Policy Update**

可以拆成：

1. **过量采样 Prompt**，每个 Prompt 生成 $G$ 条 Rollout；
2. 使用 Verifier / Reward Function 得到 Outcome Reward；
3. 对接近长度上限的 Response 加入 Overlong Reward Shaping；
4. 使用 Dynamic Sampling 过滤全对与全错 Group；
5. 对保留的 Group 计算 Group-relative Advantage；
6. 计算 Token-level Old / New Policy Ratio；
7. 使用非对称 Clip：

$$
[1-\epsilon_{low},1+\epsilon_{high}]
$$

8. 将所有 Active Token 的 Policy Loss 进行全局平均；
9. Backward 并更新 Policy；
10. 使用新 Policy 继续下一轮 Rollout。

DAPO 继承 GRPO 不需要 Critic / GAE / Value Loss 的特点。

---

## DAPO 与 Dr.GRPO、GSPO 的关系是什么？

三者虽然都从 GRPO-style RL 出发，但修改的是不同维度。

### DAPO 与 Dr.GRPO

DAPO 解决了 GRPO 的 Sequence Length Normalization 问题，但其原始 Recipe 仍沿用了 Group Reward Standardization。

Dr.GRPO 则进一步针对：

$$
\frac{
r_i-\mu_{group}
}{
\sigma_{group}
}
$$

中的 Group Std Scaling 分析 Difficulty Bias，并建议保留 Group Centering、取消 Per-prompt Std Scaling。

因此现代系统可以组合：

> **DAPO-style Clip-Higher + Dynamic Sampling + Token-level Loss + Overlong Shaping**

与：

> **Dr.GRPO-style No Group-Std Scaling**

它们不是互斥设计。

### DAPO 与 GSPO

DAPO 保留 Token-level Importance Ratio / Clipping；GSPO 则把 Policy Constraint 提升到 Sequence level。

因此 DAPO 的 Dynamic Sampling、Reward Shaping 等思想原则上也可以与 Sequence-level Policy Optimization 组合。

这反映出一个更一般的现代 RL 认识：

> **Advantage Estimator、Reward Scaling、Sampling Strategy、Loss Aggregation、Importance Ratio 粒度、Clip Strategy、KL 与 Length Shaping 都可以看成相对独立的设计旋钮。**

---

## 为什么 DAPO 更像一套 Reasoning RL Recipe，而不是单一公式改动？

DAPO 的四项关键设计分别作用于不同环节：

- **Clip-Higher**：保护探索空间；
- **Dynamic Sampling**：提高进入训练 Batch 的 Group 信息量；
- **Token-level PG Loss**：修正 Long-CoT 的 Loss Aggregation；
- **Overlong Reward Shaping**：降低截断造成的 Reward Noise。

因此 DAPO 的重要意义不只是提出一个新的 Policy Objective，而是说明：

> **大规模 Reasoning RL 的效果取决于 Rollout、Reward、Sampling、Loss Aggregation 和 Policy Update 共同构成的训练系统。**

这也是从“理解 GRPO 算法公式”进一步走向“理解 LLM RL Training System”的一个重要过渡。

---

相关主题：[[LLM/后训练/RL-based Post-training/RL-based Post-training|RL-based Post-training]] · [[LLM/后训练/RL-based Post-training/GRPO/GRPO|GRPO]] · [[LLM/后训练/RL-based Post-training/GSPO/GSPO|GSPO]] · [[Reward Hacking]]
