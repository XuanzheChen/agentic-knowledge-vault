# DPO Family（直接偏好优化）

[[LLM/后训练/偏好学习/偏好学习|返回上级：偏好学习]] · [[main|返回知识主干]]

围绕 DPO（Direct Preference Optimization）及其后续变体整理直接偏好优化方法。当前先记录 DPO 本身的数学原理与主要局限，后续再逐步扩展 IPO、SimPO、ORPO、KTO 等方法。

## 问题目录

- [[DPO Family（直接偏好优化）#DPO 的数学原理是什么？|DPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#DPO 存在哪些主要缺点？|DPO 存在哪些主要缺点？]]

---

## DPO 的数学原理是什么？

DPO 的核心不是简单地“提高 Chosen、降低 Rejected”，而是从 **KL-Regularized RLHF** 的最优策略形式出发，把显式 Reward Model 消去，直接把 Pair-wise Preference 转成 Policy 的监督学习目标。

### 1. 从 KL-Regularized RLHF 出发

对 Prompt $x$，传统 RLHF 希望 Policy $\pi$ 获得更高 Reward，同时不要偏离 Reference Policy $\pi_{\mathrm{ref}}$ 太远：

$$
\max_{\pi}
\mathbb{E}_{y\sim\pi(y\mid x)}[r(x,y)]
-
\beta D_{\mathrm{KL}}
\left(
\pi(y\mid x)\Vert\pi_{\mathrm{ref}}(y\mid x)
\right)
$$

其中 $eta$ 控制“追求更高 Reward”和“保持接近 Reference Policy”之间的权衡。

这个目标的最优策略可以写成：

$$
\pi^*(y\mid x)
=
\frac{1}{Z(x)}
\pi_{\mathrm{ref}}(y\mid x)
\exp\left(\frac{r(x,y)}{\beta}\right)
$$

其中 $Z(x)$ 是只依赖 Prompt 的归一化常数。

将它反解为 Reward：

$$
r(x,y)
=
\beta\log\frac{\pi^*(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
+
\beta\log Z(x)
$$

这意味着，在该 KL-Regularized RLHF 框架下，**一个回答相对于 Reference Policy 被 Policy 提升了多少，可以被解释为它的隐式 Reward。**

参考：[Direct Preference Optimization](https://arxiv.org/abs/2305.18290)。

### 2. 把隐式 Reward 代入 Pair-wise Preference Model

对偏好数据 $(x,y_w,y_l)$，其中 $y_w$ 是 Chosen Response，$y_l$ 是 Rejected Response。经典 Bradley-Terry Preference Model 写作：

$$
P(y_w\succ y_l\mid x)
=
\sigma\left(r(x,y_w)-r(x,y_l)\right)
$$

将前面的 Reward 重参数化代入后，$eta\log Z(x)$ 在 Reward 差中抵消：

$$
r(x,y_w)-r(x,y_l)
=
\beta
\left[
\log\frac{\pi_\theta(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}
-
\log\frac{\pi_\theta(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}
\right]
$$

因此可以直接最大化“Chosen 胜过 Rejected”的 likelihood，得到 DPO Loss：

$$
\mathcal{L}_{\mathrm{DPO}}
=
-
\mathbb{E}_{(x,y_w,y_l)\sim\mathcal{D}}
\left[
\log\sigma
\left(
\beta
\left[
\log\frac{\pi_\theta(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}
-
\log\frac{\pi_\theta(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}
\right]
\right)
\right]
$$

因此 DPO 的推导链可以概括为：

> **KL-Regularized RLHF → 最优 Policy 的闭式形式 → Reward / Policy 重参数化 → Bradley-Terry Preference Model → DPO Loss**

DPO 不需要单独训练一个显式 Reward Model，也不需要像 PPO / GRPO 一样在训练过程中反复 Rollout、计算 Advantage 再做 Policy Gradient；训练形式更接近普通监督微调。参考：[Direct Preference Optimization](https://arxiv.org/abs/2305.18290)。

### 3. DPO 真正比较的是“相对 Reference 的变化”

定义：

$$
s_w
=
\log\pi_\theta(y_w\mid x)
-
\log\pi_{\mathrm{ref}}(y_w\mid x)
$$

$$
s_l
=
\log\pi_\theta(y_l\mid x)
-
\log\pi_{\mathrm{ref}}(y_l\mid x)
$$

那么 DPO 实际要求：

$$
s_w>s_l
$$

等价于：

$$
\frac{\pi_\theta(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}
>
\frac{\pi_\theta(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}
$$

所以 DPO 并不是直接要求：

$$
\pi_\theta(y_w\mid x)>\pi_\theta(y_l\mid x)
$$

而是要求：**Chosen 相对于 Reference Policy 的提升幅度，比 Rejected 相对于 Reference Policy 的提升幅度更大。** Reference Policy 因此承担了行为锚点的作用。

### 4. Language Model 中 Response 概率如何计算？

如果 Response 为 $y=(y_1,\ldots,y_T)$，则：

$$
\log\pi_\theta(y\mid x)
=
\sum_{t=1}^{T}
\log\pi_\theta(y_t\mid x,y_{<t})
$$

实际训练需要分别计算 Policy 与 Reference Model 对 Chosen / Rejected 的 Sequence Log Probability，然后代入 DPO Loss。Reference Model 保持冻结，只更新 $\pi_\theta$。

---

## DPO 存在哪些主要缺点？

DPO 大幅简化了经典 RLHF Pipeline，但它并没有消除 Preference Optimization 本身的假设和失效模式。主要问题可以从以下几个方面理解。

### 1. 仍依赖 Pair-wise Preference → Point-wise Reward 的建模假设

DPO 虽然绕过了“先训练独立 Reward Model、再让 RM 泛化到新 Policy 分布”这一步，但仍然利用 Bradley-Terry 一类模型，把 Pair-wise Preference 解释成潜在标量 Reward 之间的差异。

因此数据只告诉模型 $y_w\succ y_l$ 时，DPO 会持续推动对应的隐式 Reward Margin。对于接近确定性的 Preference，这种目标可能产生过强的 Margin 或过拟合，而 Preference 本身未必真的表达“$y_w$ 应该远远优于 $y_l$”。IPO / $\Psi$PO 正是从这一问题出发，尝试直接处理 Pair-wise Preference，而不是完全依赖这种 Point-wise Reward 表示。参考：[A General Theoretical Paradigm to Understand Learning from Human Preferences](https://arxiv.org/abs/2310.12036)。

### 2. Reference Model 带来额外计算与显存开销

经典 DPO 需要同时计算：

- Policy 对 Chosen / Rejected 的 Log Probability；
- Frozen Reference Model 对 Chosen / Rejected 的 Log Probability。

因此虽然它比“Reward Model + PPO”简单，但仍需要 Reference Model Forward，增加显存、存储和计算开销。SimPO 等 Reference-free 方法把去掉 Reference Model 作为主要设计目标之一。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 3. Sequence Log Probability 与长度耦合

DPO 使用完整 Response 的 Sequence Log Probability：

$$
\log\pi_\theta(y\mid x)
=
\sum_{t=1}^{T}\log\pi_\theta(y_t\mid x,y_{<t})
$$

因此 Score 的尺度天然与序列长度相关。Policy / Reference Ratio 会抵消一部分共同效应，但长度仍可能影响 Preference Optimization 的训练动态。SimPO 直接采用长度归一化的平均 Log Probability 作为隐式 Reward，就是针对这一设计问题的代表性修改。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 4. 对 Preference Noise 与错误标签敏感

经典 DPO 把观察到的 $(y_w,y_l)$ 当成有效 Preference。如果标注存在随机翻转、Annotator Disagreement 或 AI Judge 误判，错误 Pair 也会直接推动 Policy 沿错误方向更新。

Robust DPO 的研究专门分析了随机 Preference Flip 对 DPO 的影响，并通过去偏 Loss 提高对噪声标签的鲁棒性。参考：[Provably Robust DPO](https://arxiv.org/abs/2403.00409)。

### 5. 经典 DPO 是 Offline Preference Optimization，存在 Distribution Shift

经典 DPO 使用固定的 Preference Dataset：

> **旧 Policy 生成候选 → 构造 $(x,y_w,y_l)$ → 固定数据训练新 Policy**

随着 $\pi_\theta$ 更新，当前 Policy 的输出分布会逐渐偏离最初生成 Preference Data 的分布。旧数据可能持续纠正旧模型的问题，却覆盖不到新 Policy 出现的 Failure Mode 和 Hard Preference。

因此现代系统越来越重视 Online / Iterative Preference Optimization：让当前 Policy 持续产生新候选，再由 Human / AI / RM 评价并回流训练。参考：[Human Alignment of Large Language Models through Online Preference Optimisation](https://arxiv.org/abs/2403.08635)。

### 6. DPO 优化的是相对偏好，不直接保证绝对质量

如果一个 Pair 中两个回答都很差，只是 $y_w$ 比 $y_l$ 稍好，DPO 仍然会学习：

$$
y_w\succ y_l
$$

这说明 DPO 获得的是**相对排序信号**，而不是“$y_w$ 已经达到高质量标准”的绝对判断。因此 Preference Data 的候选质量、与 SFT / Verifier / Absolute Evaluation 的结合仍然重要。

此外，后续研究还观察到一种 **Likelihood Displacement**：Preference Margin 可以变好，但 Chosen Response 自身的 likelihood 仍可能下降，说明“Pair-wise 相对关系改善”不等价于“Chosen 的绝对概率一定上升”。参考：[DPO-Shift](https://arxiv.org/abs/2502.07599)。

综合来看，DPO 的优势是把显式 RM + RL 简化为稳定的 Pair-wise Policy Loss；它的代价是仍然依赖 Preference Model 假设、Reference Policy、离线数据质量以及相对比较目标。后续 DPO Family 的很多方法，本质上都在针对这些设计点做修改。