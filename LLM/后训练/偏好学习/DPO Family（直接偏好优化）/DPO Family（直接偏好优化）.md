# DPO Family（直接偏好优化）

[[LLM/后训练/偏好学习/偏好学习|返回上级：偏好学习]] · [[main|返回知识主干]]

围绕 DPO（Direct Preference Optimization）及其后续变体整理直接偏好优化方法。当前重点记录 DPO、IPO、SimPO、ORPO、CPO 与 KTO 的数学原理、改进关系、工程取舍和仍然存在的局限。

## 问题目录

- [[DPO Family（直接偏好优化）#DPO 的数学原理是什么？|DPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#DPO 存在哪些主要缺点？|DPO 存在哪些主要缺点？]]
- [[DPO Family（直接偏好优化）#IPO 的数学原理是什么？|IPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#IPO 相对 DPO 做了哪些改进？|IPO 相对 DPO 做了哪些改进？]]
- [[DPO Family（直接偏好优化）#IPO 仍然存在哪些不足？|IPO 仍然存在哪些不足？]]
- [[DPO Family（直接偏好优化）#SimPO 的数学原理是什么？|SimPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#SimPO 相对 IPO 做了哪些改进？|SimPO 相对 IPO 做了哪些改进？]]
- [[DPO Family（直接偏好优化）#SimPO 仍然存在哪些缺点？|SimPO 仍然存在哪些缺点？]]
- [[DPO Family（直接偏好优化）#ORPO 的基本原理是什么？|ORPO 的基本原理是什么？]]
- [[DPO Family（直接偏好优化）#ORPO 的核心 Trade-off 是什么？|ORPO 的核心 Trade-off 是什么？]]
- [[DPO Family（直接偏好优化）#ORPO 仍然存在哪些缺点？|ORPO 仍然存在哪些缺点？]]
- [[DPO Family（直接偏好优化）#CPO 的基本原理是什么？|CPO 的基本原理是什么？]]
- [[DPO Family（直接偏好优化）#CPO 与 ORPO、SimPO 的设计差异是什么？|CPO 与 ORPO、SimPO 的设计差异是什么？]]
- [[DPO Family（直接偏好优化）#CPO 的核心 Trade-off 与缺点是什么？|CPO 的核心 Trade-off 与缺点是什么？]]
- [[DPO Family（直接偏好优化）#KTO 的基本原理是什么？|KTO 的基本原理是什么？]]
- [[DPO Family（直接偏好优化）#KTO 相对 Pair-wise Preference 方法的核心 Trade-off 是什么？|KTO 相对 Pair-wise Preference 方法的核心 Trade-off 是什么？]]
- [[DPO Family（直接偏好优化）#KTO 仍然存在哪些缺点？|KTO 仍然存在哪些缺点？]]

---

## DPO 的数学原理是什么？

DPO 的核心不是简单地“提高 Chosen、降低 Rejected”，而是从 **KL-Regularized RLHF** 的最优策略形式出发，把显式 Reward Model 消去，直接把 Pair-wise Preference 转成 Policy 的监督学习目标。

### 1. 从 KL-Regularized RLHF 出发

对 Prompt $x$，RLHF 希望 Policy $\pi$ 获得更高 Reward，同时不要偏离 Reference Policy $\pi_{\mathrm{ref}}$ 太远：

$$
\max_{\pi}
\mathbb{E}_{y\sim\pi(y\mid x)}[r(x,y)]
-
\beta D_{\mathrm{KL}}
\left(
\pi(y\mid x)\Vert\pi_{\mathrm{ref}}(y\mid x)
\right)
$$

该目标的最优策略具有闭式形式：

$$
\pi^*(y\mid x)
=
\frac{1}{Z(x)}
\pi_{\mathrm{ref}}(y\mid x)
\exp\left(\frac{r(x,y)}{\beta}\right)
$$

反解 Reward：

$$
r(x,y)
=
\beta\log\frac{\pi^*(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
+
\beta\log Z(x)
$$

因此在这个框架中，一个 Response 相对于 Reference Policy 被 Policy 提升了多少，可以被解释为隐式 Reward。参考：[Direct Preference Optimization](https://arxiv.org/abs/2305.18290)。

### 2. 代入 Bradley-Terry Preference Model

对 Preference Pair $(x,y_w,y_l)$：

$$
P(y_w\succ y_l\mid x)
=
\sigma\left(r(x,y_w)-r(x,y_l)\right)
$$

代入前面的 Reward 重参数化后，$\beta\log Z(x)$ 抵消，得到 DPO Loss：

$$
\mathcal{L}_{\mathrm{DPO}}
=
-
\mathbb{E}_{(x,y_w,y_l)\sim\mathcal D}
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

所以 DPO 的推导链可以概括为：

> **KL-Regularized RLHF → 最优 Policy 闭式解 → Reward / Policy 重参数化 → Bradley-Terry Preference Model → DPO Loss**

### 3. DPO 比较的是“相对 Reference 的变化”

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

DPO 实际要求：

$$
s_w>s_l
$$

而不是简单要求：

$$
\pi_\theta(y_w\mid x)>\pi_\theta(y_l\mid x)
$$

因此 DPO 学的是：**Chosen 相对于 Reference Policy 的提升幅度，要比 Rejected 相对于 Reference Policy 的提升幅度更大。**

Language Model 对完整 Response 的概率由 Token 概率连乘，因此：

$$
\log\pi_\theta(y\mid x)
=
\sum_{t=1}^{T}
\log\pi_\theta(y_t\mid x,y_{<t})
$$

训练时分别计算 Policy 与冻结的 Reference Model 对 Chosen / Rejected 的 Sequence Log Probability，再代入 DPO Loss。

---

## DPO 存在哪些主要缺点？

DPO 大幅简化了经典“Reward Model + PPO”的 RLHF Pipeline，但它仍然保留了一些关键假设和失效模式。

### 1. Pair-wise Preference 仍被解释成潜在 Point-wise Reward Difference

DPO 虽然没有显式训练 Reward Model，但仍通过 Bradley-Terry / Logistic Link，把 Pair-wise Preference 解释成潜在 Scalar Reward 的差。

如果数据只告诉模型：

$$
y_w\succ y_l
$$

DPO 的 Logistic Loss 会持续鼓励对应 Margin 增大。对接近确定性的 Preference，这可能产生过强的 Margin，而 Preference 本身并没有告诉模型“$y_w$ 应该远远优于 $y_l$”。IPO / $\Psi$PO 正是从这里切入。参考：[A General Theoretical Paradigm to Understand Learning from Human Preferences](https://arxiv.org/abs/2310.12036)。

### 2. Reference Model 带来额外开销

经典 DPO 训练时需要同时获得 Policy 与 Frozen Reference Model 对 Chosen / Rejected 的 Log Probability，因此仍有额外显存、存储和 Forward 计算成本。SimPO 后续直接去掉了 Reference Model。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 3. Sequence Log Probability 与长度耦合

DPO 使用整段 Response 的 Sequence Log Probability：

$$
\log\pi_\theta(y\mid x)
=
\sum_{t=1}^{T}\log\pi_\theta(y_t\mid x,y_{<t})
$$

因此 Score 的尺度天然受到 Sequence Length 影响。Policy / Reference Ratio 会抵消一部分共同效应，但长度仍可能影响训练动态。SimPO 把长度归一化直接纳入 Reward 设计。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 4. 对 Preference Noise 敏感

经典 DPO 把观察到的 $(y_w,y_l)$ 当成有效 Preference。如果 Human / AI Judge 标注出错或存在系统性偏差，错误 Pair 仍会直接推动 Policy 沿错误方向更新。参考：[Provably Robust DPO](https://arxiv.org/abs/2403.00409)。

### 5. 经典 DPO 是 Offline Preference Optimization

Preference Dataset 通常来自旧 Policy。随着 $\pi_\theta$ 更新，当前输出分布会逐渐偏离数据生成分布，导致 Distribution Shift。旧 Preference Data 也覆盖不到新 Policy 的新 Failure Mode 与 Hard Negative。参考：[Human Alignment of Large Language Models through Online Preference Optimisation](https://arxiv.org/abs/2403.08635)。

### 6. 相对偏好不等于绝对质量

如果一个 Pair 中两个回答都很差，只是 $y_w$ 相对更好，DPO 仍然只会学习：

$$
y_w\succ y_l
$$

这说明它获得的是 Relative Preference，而不是“Chosen 已达到高质量”的绝对判断。后续研究还观察到 Likelihood Displacement：Preference Margin 改善时，Chosen Response 自身的 likelihood 仍可能下降。参考：[DPO-Shift](https://arxiv.org/abs/2502.07599)。

---

## IPO 的数学原理是什么？

IPO（Identity Preference Optimization）来自更一般的 $\Psi$PO 理论框架。它质疑 DPO 的一层隐含假设：**Pair-wise Preference 是否一定需要先被解释成某个 Point-wise Scalar Reward 的差？**

### 1. 直接从 Preference Probability 出发

记真实偏好概率为：

$$
p^*(y\succ y'\mid x)
$$

$\Psi$PO 直接对 Pair-wise Preference Probability 做变换：

$$
\Psi\left(p^*(y\succ y'\mid x)\right)
$$

IPO 采用最简单的 Identity Mapping：

$$
\Psi(p)=p
$$

因此“Identity”指的是：**直接使用 Preference Probability 本身，而不是像 DPO 那样通过 Logit / Bradley-Terry 将其映射成潜在 Reward Difference。** 参考：[A General Theoretical Paradigm to Understand Learning from Human Preferences](https://arxiv.org/abs/2310.12036)。

### 2. 定义 Policy / Reference 的 Pair-wise Log-Ratio Difference

$$
h_\pi(y,y')
=
\log\frac{\pi(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
-
\log\frac{\pi(y'\mid x)}{\pi_{\mathrm{ref}}(y'\mid x)}
$$

IPO 的 Population Objective 给出有限的最优条件。实际只有采样得到的 $(x,y_w,y_l)$ 时，可以得到平方误差形式：

$$
\mathcal{L}_{\mathrm{IPO}}
=
\mathbb{E}_{(x,y_w,y_l)\sim\mathcal D}
\left[
\left(
h_\theta(y_w,y_l)
-
\frac{1}{2\tau}
\right)^2
\right]
$$

许多工程实现把原论文中的 $\tau$ 记为 $\beta$，此时：

$$
\boxed{
h_\theta^*=\frac{1}{2\beta}
}
$$

参考：[A General Theoretical Paradigm to Understand Learning from Human Preferences](https://arxiv.org/abs/2310.12036)。

### 3. 为什么平方 Loss 很关键？

DPO：

$$
\mathcal L_{\mathrm{DPO}}
=-\log\sigma(\beta h)
$$

对固定 Pair 来说，没有有限的最优 Margin，理论方向仍是：

$$
h\rightarrow+\infty
$$

IPO：

$$
\mathcal L_{\mathrm{IPO}}
=
\left(h-\frac{1}{2\beta}\right)^2
$$

因此存在有限最优点：

$$
h^*=\frac{1}{2\beta}
$$

当 $h$ 过小时，IPO 把 Margin 推大；当 $h$ 已经过大时，IPO 会反向把它拉回目标值。

---

## IPO 相对 DPO 做了哪些改进？

IPO 修改的是 **Preference 建模与 Margin 行为**，而不是简单把 DPO 的 Sigmoid 换成平方 Loss。

### 1. 减少对 Point-wise Scalar Reward 假设的依赖

DPO 仍然利用 Bradley-Terry，把 Pair-wise Preference 映射成潜在 Scalar Reward Difference；IPO 所属的 $\Psi$PO 框架直接把 Pair-wise Preference Probability 作为基本对象，因此更贴近实际 Preference 本身。

### 2. 把无界 Margin 改成有限目标 Margin

DPO 的目标方向是：

$$
h\rightarrow+\infty
$$

IPO 则明确规定：

$$
h^*=\frac{1}{2\beta}
$$

因此一条 Pair 只需要把 Winner 与 Loser 区分到合适程度，不需要无限拉开。

### 3. 更符合 Pair-wise Label 的信息边界

一条 $(y_w,y_l)$ 数据只表达：

$$
y_w\succ y_l
$$

并不直接表达：

$$
y_w\gg y_l
$$

IPO 的有限 Margin 对这一点采取了更保守的建模。

### 4. 保留 DPO 的直接训练优势

IPO 仍然不需要独立 Reward Model，也不需要 PPO / GRPO 式的 Rollout、Advantage Estimation 和 Policy Gradient，因此保留了 Direct Preference Optimization 的主要工程优点。

| 维度 | DPO | IPO |
| --- | --- | --- |
| Preference 建模 | Bradley-Terry / Logistic，隐式 Point-wise Reward | $\Psi$PO 直接处理 Pair-wise Preference |
| Loss | $-\log\sigma(\beta h)$ | $(h-1/(2\beta))^2$ |
| 最优 Margin | $h\rightarrow+\infty$ | $h=1/(2\beta)$ |
| Margin 过大时 | 仍继续鼓励增大，只是梯度趋小 | 主动拉回目标值 |
| 独立 RM | 不需要 | 不需要 |
| Reference Policy | 需要 | 仍需要 |

---

## IPO 仍然存在哪些不足？

IPO 主要修正的是 **DPO 的 Preference / Reward 建模与无界 Margin 问题**，并没有同时解决 DPO Family 的所有局限。

### 1. 仍然需要 Reference Policy

IPO 的核心量仍然包含：

$$
\log\frac{\pi_\theta(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
$$

因此仍需要 Frozen Reference Model 的 Log Probability，没有消除 Reference Forward 的显存和计算开销。

### 2. 固定目标 Margin 仍由单个超参数控制

标准 IPO 使用：

$$
h^*=\frac{1}{2\beta}
$$

不同 Pair 的真实 Preference Strength 可能差异很大，但一个全局 $\beta$ 并不能表达所有 Pair 的细粒度 Preference Strength。

### 3. 仍依赖 Pair-wise Preference 数据质量

IPO 不能自动判断 Human / AI Judge 的 Preference Label 是否正确。有限 Margin 只能减少“过度放大”问题，不能纠正错误偏好。

### 4. 没有从理论上直接解决长度耦合

如果 $h_\theta$ 仍基于完整 Response 的 Sequence Log Probability，Sequence Length 仍会影响 Score 尺度。Length Normalization 可以作为额外实现选择，但并不是 IPO 的核心设计。

### 5. 经典 IPO 仍是 Offline Preference Optimization

固定 Dataset 仍会面临 Policy 更新后的 Distribution Shift，无法自动获得当前 Policy 的新 Hard Negative 与 Failure Mode。

### 6. 仍然主要学习相对质量

如果 Chosen / Rejected 都很差，IPO 仍然只学习相对关系，有限 Margin 并不提供绝对质量保证。

---

## SimPO 的数学原理是什么？

SimPO（Simple Preference Optimization）继续修改 DPO Family 的另一些设计点：**Reference Model 是否必要、Sequence Score 是否应该做长度归一化，以及训练时使用的隐式 Reward 是否应与 Policy 自身的生成 likelihood 更直接对齐。** 参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 1. 从 DPO 的 Reference-based Reward 出发

DPO 的隐式 Reward 为：

$$
r_{\mathrm{DPO}}(x,y)
=
\beta
\log
\frac{\pi_\theta(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
$$

SimPO 指出两个直接问题：

- 训练需要额外计算 $\pi_{\mathrm{ref}}$，增加计算和显存成本；
- DPO 实际优化的是 $\pi_\theta/\pi_{\mathrm{ref}}$ 的相对变化，而推理生成时真正使用的是当前 Policy $\pi_\theta$ 本身，二者可能形成 **Reward-Generation Mismatch**。

因此即使满足：

$$
r_{\mathrm{DPO}}(x,y_w)
>
r_{\mathrm{DPO}}(x,y_l)
$$

也不一定意味着当前 Policy 自身满足：

$$
\pi_\theta(y_w\mid x)
>
\pi_\theta(y_l\mid x)
$$

SimPO 的实验中也观察到，DPO 的 Reward Ranking 与按 Average Log-Likelihood 计算的 Policy Ranking 可能明显不一致。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 2. 使用长度归一化的 Average Log Probability 作为隐式 Reward

SimPO 直接定义：

$$
\boxed{
r_{\mathrm{SimPO}}(x,y)
=
\frac{\beta}{|y|}
\log\pi_\theta(y\mid x)
}
$$

其中：

$$
\log\pi_\theta(y\mid x)
=
\sum_{t=1}^{|y|}
\log\pi_\theta(y_t\mid x,y_{<t})
$$

因此：

$$
\frac{1}{|y|}\log\pi_\theta(y\mid x)
$$

就是 Response 的 **Average Token Log Probability**。

这里有两个关键变化：

1. Reward 只依赖当前 Policy $\pi_\theta$，因此不再需要 Reference Model；
2. 通过除以 $|y|$ 做 Length Normalization，避免直接使用 Sequence Log Probability 时 Score 随长度累加的问题。

Average Log Probability 也与 Perplexity 直接相关：

$$
\operatorname{PPL}(y)
=
\exp
\left(
-\frac{1}{|y|}\log\pi_\theta(y\mid x)
\right)
$$

因此提高 SimPO Reward，可以理解为让 Preferred Response 在当前 Policy 下具有更高平均 Token Likelihood。

### 3. 在 Bradley-Terry Objective 中加入 Target Reward Margin

仅要求：

$$
r_w>r_l
$$

还不够。SimPO 进一步加入 Target Reward Margin $\gamma>0$：

$$
P(y_w\succ y_l\mid x)
=
\sigma
\left(
r_w-r_l-\gamma
\right)
$$

于是最终 Loss 为：

$$
\boxed{
\mathcal L_{\mathrm{SimPO}}
=
-
\mathbb E_{(x,y_w,y_l)\sim\mathcal D}
\left[
\log\sigma
\left(
\frac{\beta}{|y_w|}\log\pi_\theta(y_w\mid x)
-
\frac{\beta}{|y_l|}\log\pi_\theta(y_l\mid x)
-
\gamma
\right)
\right]
}
$$

参考：[SimPO](https://arxiv.org/abs/2405.14734)。

如果定义：

$$
a_w
=
\frac{1}{|y_w|}\log\pi_\theta(y_w\mid x)
$$

$$
a_l
=
\frac{1}{|y_l|}\log\pi_\theta(y_l\mid x)
$$

那么：

$$
\mathcal L_{\mathrm{SimPO}}
=
-\log\sigma
\left(
\beta(a_w-a_l)-\gamma
\right)
$$

因此 $\gamma/\beta$ 可以直观理解为 Average Log-Likelihood Gap 的一个目标尺度。

### 4. SimPO 的 Margin 与 IPO 的有限最优 Margin不同

IPO：

$$
\mathcal L_{\mathrm{IPO}}
=
\left(h-c\right)^2
$$

存在明确的有限最优点：

$$
h=c
$$

如果 Margin 过大，IPO 会主动把它拉回来。

SimPO：

$$
\mathcal L_{\mathrm{SimPO}}
=
-\log\sigma(\beta\Delta-\gamma)
$$

即使：

$$
\Delta>\frac{\gamma}{\beta}
$$

继续增大 $\Delta$ 仍然会继续降低 Loss，只是梯度逐渐趋近于 $0$。

所以 SimPO 的 Target Reward Margin 更准确地理解为 **Margin Offset / Threshold**，而不是 IPO 那种“到达一个有限点后再大反而会被惩罚”的精确目标值。

---

## SimPO 相对 IPO 做了哪些改进？

SimPO 并不是简单沿着 IPO 的理论路线继续往前，而是针对 IPO 仍然保留的另一组问题做修改。

### 1. 去掉 Reference Model

IPO 虽然修正了 DPO 的无界 Margin，但仍然依赖：

$$
\log\frac{\pi_\theta}{\pi_{\mathrm{ref}}}
$$

SimPO 直接改成：

$$
r_{\mathrm{SimPO}}(x,y)
=
\frac{\beta}{|y|}
\log\pi_\theta(y\mid x)
$$

因此完全 Reference-free，减少 Reference Forward 带来的显存和计算成本。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 2. 让训练 Reward 更直接地与当前 Policy 的生成 Score 对齐

IPO 与 DPO 都主要比较 Policy 相对于 Reference 的变化；SimPO 直接使用当前 Policy 的 Average Log Probability，因此训练目标更直接地要求：

$$
\frac{1}{|y_w|}\log\pi_\theta(y_w\mid x)
>
\frac{1}{|y_l|}\log\pi_\theta(y_l\mid x)
$$

也就是让当前 Policy 自己更偏向 Preferred Response，而不只是“相对于 Reference 提升得更多”。

### 3. 把 Length Normalization 纳入 Reward 定义

IPO 的核心理论并没有专门解决 Sequence Length Coupling。SimPO 直接用：

$$
\frac{1}{|y|}\log\pi_\theta(y\mid x)
$$

代替 Sequence Log Probability，使不同长度 Response 的 Score 更可比较。SimPO 论文的消融实验也显示，去掉 Length Normalization 会显著改变 Reward 与长度之间的关系。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 4. 用显式 Margin 鼓励 Winner / Loser 分离

SimPO 使用：

$$
\beta(a_w-a_l)-\gamma
$$

作为 Bradley-Terry Logit，让 Winner 与 Loser 之间需要达到更明显的 Reward Separation。

不过要注意：这与 IPO 的“有限最优 Margin”不是同一机制。SimPO 并不会在 Margin 过大时主动把它拉回，只是通过 $\gamma$ 提高“达到较强 Preference Separation”的要求。

### 5. SimPO 与 IPO 更适合视为“修不同问题”，而不是线性替代

| 维度 | IPO | SimPO |
| --- | --- | --- |
| 核心关注点 | 修正 DPO 的 Preference / Reward 建模和无界 Margin | 去掉 Reference、长度归一化、Reward-Generation 对齐 |
| Reference Policy | 需要 | 不需要 |
| Score | Policy / Reference Log-Ratio | Average Policy Log Probability |
| Length Normalization | 非核心设计 | 核心设计 |
| Margin | 有限最优点 $1/(2\beta)$ | Bradley-Terry 中加入 $\gamma$ Offset |
| Margin 过大时 | 主动拉回 | 仍继续鼓励增大，但梯度趋小 |
| 独立 Reward Model | 不需要 | 不需要 |
| 经典训练形式 | Offline Pairwise | Offline Pairwise |

---

## SimPO 仍然存在哪些缺点？

SimPO 主要解决了 Reference Model、Length Normalization 和 Reward-Generation Mismatch，但并没有消除 Direct Preference Optimization 的根本局限。

### 1. 去掉 Reference Model 也意味着失去显式 KL Anchor

DPO / IPO 中的 Reference Policy 不只是计算负担，也承担了限制 Policy Drift 的作用。SimPO 删除 $\pi_{\mathrm{ref}}$ 后，没有显式的：

$$
D_{\mathrm{KL}}
\left(
\pi_\theta\Vert\pi_{\mathrm{ref}}
\right)
$$

约束。

SimPO 论文在其实验设置中观察到，即使没有显式 KL Regularization，Policy 仍能保持相对有限的分布漂移，但这更多依赖较小 Learning Rate、Preference Data 覆盖和模型本身的训练稳定性，而不是一个像 DPO 那样由 Reference Policy 明确给出的理论 Anchor。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 2. Target Reward Margin 仍依赖超参数 $\gamma$ 与 $\beta$

SimPO 中：

$$
\mathcal L
=
-\log\sigma\left(\beta\Delta-\gamma\right)
$$

因此 Preference Separation 的实际强度同时受到 $\beta$ 和 $\gamma$ 控制。Margin 太小可能区分不足，太大又可能导致过强优化。SimPO 论文的消融实验也显示 $\gamma$ 并不是越大越好。参考：[SimPO](https://arxiv.org/abs/2405.14734)。

### 3. Length Normalization 只能减少长度尺度问题，不能保证消除所有 Length Bias

把 Sequence Log Probability 除以 $|y|$ 能避免总 Log Probability 随长度线性累加，但并不意味着模型从此与长度完全无关。

Preference Dataset 本身可能偏好更长或更短回答；某些任务本来也需要较长推理。Average Log Probability 只是改变 Score 的尺度，并不能自动判断“这个长度是否真正合适”。

### 4. 仍然依赖 Pair-wise Preference 数据质量

SimPO 仍以：

$$
(x,y_w,y_l)
$$

为主要训练单位。因此 Human / AI Judge Bias、Label Noise、Sycophancy、Style Bias 等 Preference Failure Mode 仍然存在。

### 5. 经典 SimPO 仍然是 Offline Preference Optimization

SimPO 原始方法仍基于固定 Preference Dataset，因此随着 Policy 更新，同样会出现 Distribution Shift：数据描述的是旧 Policy 的错误，而当前 Policy 可能已经产生新的 Failure Mode。

因此它并没有自动解决 Online / Iterative Preference Data 更新问题。

### 6. 仍然只提供相对偏好，不保证绝对质量

如果两个候选都很差，只是：

$$
y_w\succ y_l
$$

SimPO 依然只会学习让当前 Policy 更倾向 $y_w$，而不会自动知道 $y_w$ 是否真正满足某个绝对质量标准。

因此仍然需要 SFT、高质量 Candidate Generation、Verifier、Absolute Evaluation 或其他 Reward Signal 配合。

### 7. Reference-free 不等于没有过优化风险

SimPO 仍然是在优化一个 Preference Proxy。只要 Preference Dataset 或 Judge 本身不完全代表真实目标，就仍然可能出现 Preference Overoptimization、Style Exploitation 或其他 [[LLM/后训练/Reward Hacking/Reward Hacking|Reward Hacking]] 类问题。

综合来看，SimPO 可以概括为：

> **把 DPO / IPO 的 Reference-based Log-Ratio Score 改成当前 Policy 的长度归一化 Average Log Probability，并用 Target Reward Margin 强化 Preferred / Rejected 的分离，从而实现 Reference-free Preference Optimization。**

但它并没有解决 Preference Data 噪声、Offline Distribution Shift、绝对质量缺失以及过优化等更一般的问题。

---

## ORPO 的基本原理是什么？

ORPO（Odds Ratio Preference Optimization）的核心不是单独再设计一个 Preference-only Loss，而是把 **监督微调（SFT）与 Preference Alignment 合并进同一个训练目标**。因此它被称为 **Monolithic Preference Optimization**：不再默认采用“先 SFT，再额外做 DPO”这样的两阶段 Pipeline，也不需要 Frozen Reference Model。参考：[ORPO: Monolithic Preference Optimization without Reference Model](https://arxiv.org/abs/2403.07691)。

### 1. ORPO 从 SFT 本身的局限出发

对 Preference Pair $(x,y_w,y_l)$，如果只使用 Chosen Response $y_w$ 做 SFT，则典型的 Causal Language Modeling Loss 为：

$$
\mathcal L_{\mathrm{SFT}}
=
-
\frac{1}{|y_w|}
\sum_{t=1}^{|y_w|}
\log\pi_\theta(y_{w,t}\mid x,y_{w,<t})
$$

它会明确提高 Chosen 的 likelihood，但没有显式机制压低 Rejected。ORPO 原论文的实验观察到，仅使用 Chosen 做 SFT 时，Chosen 与 Rejected 的 log probability 可能同时上升：SFT 能把模型带入目标 Domain / Style，却不一定能区分同一 Domain 中的 Preferred 与 Disfavored 行为。参考：[ORPO](https://arxiv.org/abs/2403.07691)。

因此 ORPO 希望在保留 SFT 强适应信号的同时，再对 Rejected Response 施加一个较弱的相对惩罚。

### 2. 用 Average Log-Likelihood 定义 Response Score

ORPO 对完整 Response 使用长度归一化后的平均 Token Log-Likelihood：

$$
\log P_\theta(y\mid x)
=
\frac{1}{|y|}
\sum_{t=1}^{|y|}
\log P_\theta(y_t\mid x,y_{<t})
$$

再用这个 Sequence Score 对应的 $P_\theta(y\mid x)$ 构造 Odds：

$$
\operatorname{odds}_\theta(y\mid x)
=
\frac{P_\theta(y\mid x)}{1-P_\theta(y\mid x)}
$$

Chosen 相对于 Rejected 的 Odds Ratio 为：

$$
\operatorname{OR}_\theta(y_w,y_l)
=
\frac{
\operatorname{odds}_\theta(y_w\mid x)
}{
\operatorname{odds}_\theta(y_l\mid x)
}
$$

因此 ORPO 比较的不是 Policy / Reference Ratio，而是**当前 Policy 对 Chosen 与 Rejected 的 Log-Odds Difference**。参考：[ORPO](https://arxiv.org/abs/2403.07691)。

### 3. Odds-Ratio Preference Loss

ORPO 把 Log Odds Ratio 放进 Logistic Loss：

$$
\mathcal L_{\mathrm{OR}}
=
-
\log\sigma
\left(
\log
\frac{
\operatorname{odds}_\theta(y_w\mid x)
}{
\operatorname{odds}_\theta(y_l\mid x)
}
\right)
$$

最小化该 Loss 会推动：

$$
\operatorname{odds}_\theta(y_w\mid x)
>
\operatorname{odds}_\theta(y_l\mid x)
$$

也就是让当前模型更倾向于 Chosen，而不是 Rejected。

ORPO 的梯度还包含一个随当前 Odds Ratio 变化的权重：如果模型当前反而更倾向 Rejected，则 Preference Penalty 更强；当 Chosen 已明显占优时，该项更新逐渐减弱。原论文把它解释为一种动态的、较弱的 Rejected Penalty。参考：[ORPO](https://arxiv.org/abs/2403.07691)。

### 4. 最终目标：SFT + Preference 在同一步训练

ORPO 最终写成：

$$
\boxed{
\mathcal L_{\mathrm{ORPO}}
=
\mathbb E_{(x,y_w,y_l)}
\left[
\mathcal L_{\mathrm{SFT}}
+
\lambda\mathcal L_{\mathrm{OR}}
\right]
}
$$

其中：

- $\mathcal L_{\mathrm{SFT}}$：提供强的 Chosen / Domain Adaptation Signal，直接学习“应该生成什么”；
- $\mathcal L_{\mathrm{OR}}$：提供 Chosen-vs-Rejected 的相对区分信号，学习“哪些相似行为应该避免”；
- $\lambda$：控制 SFT 与 Preference Discrimination 的相对强度。

因此一条 Preference Pair 同时被用于两类监督：

> **$y_w$ 提供正向 SFT Signal；$(y_w,y_l)$ 提供 Relative Preference Signal。**

这也是 ORPO 与 SimPO 最关键的差别：SimPO 主要重构 Preference-only Objective；ORPO 则把 **Instruction / Domain Adaptation 与 Preference Alignment 合并成一个 Objective**。参考：[ORPO](https://arxiv.org/abs/2403.07691)。

---

## ORPO 的核心 Trade-off 是什么？

ORPO 的设计优势和代价来自同一个决定：**把 Chosen 当作 SFT Target，同时把 Chosen / Rejected 当作 Preference Pair。**

### 1. 单阶段、Reference-free，换来更强的 Chosen 依赖

相比经典“$\text{SFT}\rightarrow\text{DPO}$”，ORPO 可以在同一个目标里完成 Domain / Instruction Adaptation 与 Preference Alignment，并且不需要额外 Reference Model，因此训练 Pipeline 更简单、显存与计算成本更低。原论文将其明确定位为无需额外 preference-alignment stage 与 Reference Model 的 Monolithic 方法。参考：[ORPO](https://arxiv.org/abs/2403.07691)。

但代价是：ORPO 不只是学习

$$
y_w\succ y_l
$$

还通过 $\mathcal L_{\mathrm{SFT}}$ **直接模仿 $y_w$**。

如果 Chosen 是“很好 vs 很差”中的好答案，这种强正向学习很有价值；但如果是“差 vs 更差”，ORPO 仍会把那个只是相对较好的 Chosen 当成 Demonstration 来提高 likelihood。

因此可以概括为：

> **DPO / IPO / SimPO 更强调 Relative Preference；ORPO 在 Relative Preference 之外，再显式加入 Chosen 的 Absolute Imitation Signal。**

这能减少只改善 Pair-wise Margin、却不提高 Chosen likelihood 的问题，但也使 ORPO 对 Chosen Response 的绝对质量和数据清洗更加敏感。

### 2. SFT Anchor 换掉了 Reference / KL Anchor

DPO / IPO 通过 $\pi_{\mathrm{ref}}$ 表达“不要离原策略太远”；ORPO 不再使用 Reference Model，而是依靠 SFT 项持续把模型拉向 Chosen Data Distribution。

这使训练更轻量，但两种 Anchor 的含义并不等价：

- Reference / KL Anchor：限制 Policy 相对原模型的整体漂移；
- SFT Anchor：推动 Policy 靠近 Chosen Demonstration Distribution。

所以 ORPO 的 Reference-free 并不意味着“约束不再需要”，而是**把稳定训练和行为锚定更多交给 SFT Data 与 SFT Loss**。

### 3. $\lambda$ 控制“模仿”与“区分”的权衡

ORPO：

$$
\mathcal L
=
\mathcal L_{\mathrm{SFT}}
+
\lambda\mathcal L_{\mathrm{OR}}
$$

当 $\lambda$ 较小时，训练更接近只对 Chosen 做 SFT；当 $\lambda$ 增大时，Chosen / Rejected 的 Preference Separation 获得更强权重。

因此 $\lambda$ 本质上控制：

> **“把 Chosen 学好”与“把 Chosen / Rejected 拉开”之间的 trade-off。**

它并不是 DPO 中 $\beta$ 那种 Reference / KL 强度参数，也不是 SimPO 的 Margin 参数。ORPO 原论文也专门对 $\lambda$ 做了消融，说明该权重是方法的重要训练超参数。参考：[ORPO](https://arxiv.org/abs/2403.07691)。

---

## ORPO 仍然存在哪些缺点？

ORPO 主要解决了 **SFT 与 Preference Alignment 分阶段、Reference Model 开销，以及 SFT 缺乏显式 Rejected Penalty** 的问题，但它没有解决 Preference Learning 的全部困难。

### 1. 对 Chosen 的绝对质量要求更高

这是 ORPO 相比纯 Pair-wise Preference Objective 最需要注意的地方。

因为它显式最小化：

$$
\mathcal L_{\mathrm{SFT}}(y_w)
$$

所以 Chosen 不只是“比 Rejected 好”，还会被直接当成语言建模目标。如果 Pair 中两个 Response 都较差，只是 $y_w$ 相对更好，ORPO 仍会把 $y_w$ 的具体内容、Style 和潜在缺陷一起模仿。

因此 ORPO 很依赖高质量的 Chosen Candidate、数据清洗和 Preference Pair Construction。

### 2. 没有显式 Reference / KL Constraint

ORPO 的 Reference-free 设计降低了成本，但也意味着没有类似：

$$
D_{\mathrm{KL}}
\left(
\pi_\theta\Vert\pi_{\mathrm{ref}}
\right)
$$

这样的显式 Policy Drift 约束。

SFT 项提供了另一种训练 Anchor，但它不能严格替代 Reference Policy 对整体分布漂移的约束。因此训练稳定性、Learning Rate、数据覆盖与 $\lambda$ 选择仍然重要。

### 3. 仍依赖 Pair-wise Preference Label 的正确性

ORPO 的 Preference 部分仍建立在：

$$
(x,y_w,y_l)
$$

之上。如果 Human / AI Judge 把 Preference 标反，Odds-Ratio Loss 会沿错误方向训练；同时 SFT 项还会进一步直接模仿被错误标成 Chosen 的 Response。

因此在 Label Noise 较强时，错误 Chosen 对 ORPO 可能同时污染“模仿”和“排序”两条训练信号。

### 4. $\lambda$ 是全局权衡，不能直接表达每个 Pair 的 Preference Strength

标准 ORPO 用一个全局 $\lambda$ 控制 Odds-Ratio Penalty。现实中有些 Pair 只是轻微偏好，有些则是“正确 vs 明显错误”，但普通 Binary Preference Pair 并没有直接提供这种细粒度强度。

因此固定 $\lambda$ 解决的是整体 SFT / Preference 权重，而不是对每个样本自适应地表达“这个 Pair 应该拉多开”。

### 5. Average Log-Likelihood 不能消除所有长度与 Style Bias

ORPO 使用长度归一化 Average Log-Likelihood，减少了总 Sequence Log Probability 随长度累加的尺度问题，但 Preference Dataset 本身仍可能偏好更长、更正式、更自信或特定格式的回答。

因此 Length Normalization 不能自动解决 Judge Bias、Style Bias 或 Sycophancy 等数据层偏差。

### 6. 经典 ORPO 仍然是 Offline Preference Optimization

原始 ORPO 使用固定 Pair-wise Preference Dataset，并没有自动让当前 Policy 重新生成候选、收集新 Preference、再更新模型。

随着 Policy 变化，仍可能出现 Distribution Shift，新模型产生的 Failure Mode 与 Hard Negative 也可能没有被旧数据覆盖。持续更新这类问题仍需要 Online / Iterative Preference Learning。参考：[Human Alignment of Large Language Models through Online Preference Optimisation](https://arxiv.org/abs/2403.08635)。

### 7. Reference-free、Monolithic 也不等于不会 Preference Overoptimization

ORPO 仍然优化的是由 Preference Pair 与 SFT Demonstration 共同定义的 Proxy Objective。如果 Chosen / Rejected 的构造、Judge 或数据分布与真正目标存在偏差，模型仍可能学习表面 Style、数据偏见，甚至出现更一般的 [[LLM/后训练/Reward Hacking/Reward Hacking|Reward Hacking / Specification Gaming]] 问题。

综合来看，ORPO 可以压缩成：

> **在 Chosen 上做 SFT，用强正向信号学习期望分布；同时用 Odds-Ratio Loss 对 Rejected 施加较弱的相对惩罚，从而把 Instruction / Domain Adaptation 与 Preference Alignment 合并成一个 Reference-free 的训练阶段。**

它的核心 trade-off 也来自这里：**训练更简单、Chosen likelihood 有明确正向监督，但模型因此更依赖 Chosen 的绝对质量，并失去显式 Reference / KL Anchor。**

---

## CPO 的基本原理是什么？

这里的 CPO 指 **Contrastive Preference Optimization**。它最初用于机器翻译，但目标函数本身是对 DPO 的一种 Reference-free 近似，因此也可以推广到一般的 Chosen / Rejected Preference Data。参考：[Contrastive Preference Optimization](https://arxiv.org/abs/2401.08417)。

### 1. 从 DPO 的 Reference Model 开销出发

DPO 的 Preference Logit 包含：

$$
\beta
\left[
\log\frac{\pi_\theta(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}
-
\log\frac{\pi_\theta(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}
\right]
$$

因此需要额外保存并 Forward Frozen Reference Model。CPO 希望把 Reference Model 去掉，但它不是简单把 $\pi_{\mathrm{ref}}$ 从公式中删除。

CPO 先把 Reference Policy 设成 Uniform Prior $U$。由于对同一 Prompt 的 Chosen / Rejected，Uniform Reference 对两者提供相同常数，因此在差分中抵消，Preference Term 变成：

$$
\boxed{
\mathcal L_{\mathrm{prefer}}
=
-
\mathbb E_{(x,y_w,y_l)\sim\mathcal D}
\left[
\log\sigma
\left(
\beta
\left[
\log\pi_\theta(y_w\mid x)
-
\log\pi_\theta(y_l\mid x)
\right]
\right)
\right]
}
$$

也就是直接要求当前 Policy 的 Chosen Log-Likelihood 高于 Rejected。参考：[CPO，Sec. 3.2](https://arxiv.org/abs/2401.08417)。

### 2. Uniform Reference 是 DPO 的 Surrogate，而不是严格等价替换

CPO 论文给出一个重要理论说明：如果把理想 Reference Policy 设为真正符合 Preferred Data Distribution 的 $\pi_w$，那么在论文条件下，使用 Uniform Reference 得到的目标可以作为相应 DPO Loss 的 Upper-bound Surrogate。也就是说，CPO 通过最小化这个更容易计算的上界来近似原本理想的 Reference-based Preference Objective。

因此更准确的理解不是“Reference Model 没有用”，而是：

> **CPO 用一个可直接训练的 Uniform-reference surrogate 替代了不可获得的理想 Preferred Policy Reference。**

这个理论关系依赖论文关于理想 Preferred Policy $\pi_w$ 的假设，不能把 CPO 与经典 DPO 视为无条件严格等价。参考：[CPO，Theorem 1](https://arxiv.org/abs/2401.08417)。

### 3. 仅做 Contrastive Preference 仍不能保证 Chosen 自身概率足够高

如果只优化：

$$
\log\pi_\theta(y_w\mid x)
-
\log\pi_\theta(y_l\mid x)
$$

Preference Margin 可以通过提高 Chosen，也可以通过更快地压低 Rejected 来改善。因此“Chosen 相对更优”并不自动保证 Policy 真正靠近 Preferred Data Distribution。

CPO 因此再加入 **Behavior Cloning（BC）Regularizer**。论文从约束：

$$
\mathbb E_{(x,y_w)\sim\mathcal D}
\left[
D_{\mathrm{KL}}
\left(
\pi_w(y_w\mid x)
\Vert
\pi_\theta(y_w\mid x)
\right)
\right]
<\epsilon
$$

出发，最终把它化成对 Preferred Response 的 NLL / SFT Term：

$$
\boxed{
\mathcal L_{\mathrm{NLL}}
=
-
\mathbb E_{(x,y_w)\sim\mathcal D}
\left[
\log\pi_\theta(y_w\mid x)
\right]
}
$$

参考：[CPO，Eq. 4–5](https://arxiv.org/abs/2401.08417)。

### 4. 最终 CPO = Preference Contrast + Preferred Behavior Cloning

原论文的核心目标可以写成：

$$
\boxed{
\mathcal L_{\mathrm{CPO}}
=
\mathcal L_{\mathrm{prefer}}
+
\mathcal L_{\mathrm{NLL}}
}
$$

工程实现也常把 BC / NLL 权重显式写成 $\alpha$：

$$
\mathcal L_{\mathrm{CPO}}
=
\mathcal L_{\mathrm{prefer}}
+
\alpha\mathcal L_{\mathrm{NLL}}
$$

其中原论文对应的基本形式可视为 $\alpha=1$；例如 Hugging Face TRL 的 CPO Trainer 提供 `cpo_alpha` 调整 BC Regularizer 权重。参考：[TRL CPO Trainer](https://huggingface.co/docs/trl/cpo_trainer)。

因此 CPO 可以压缩成：

> **直接用当前 Policy 的 Chosen / Rejected Log-Likelihood 做 Contrastive Preference Learning，再用 Chosen NLL 把 Policy 拉向 Preferred Data Distribution。**

---

## CPO 与 ORPO、SimPO 的设计差异是什么？

CPO、ORPO、SimPO 都可以做到 Reference-free，但“去掉 Reference 之后拿什么来定义偏好、又拿什么来稳定 Chosen”并不一样。

### 1. CPO 与 ORPO：都包含正向 Chosen 学习，但 Preference Score 不同

CPO 的 Preference Term 比较：

$$
\log\pi_\theta(y_w\mid x)
-
\log\pi_\theta(y_l\mid x)
$$

也就是 **Log-Probability Difference**。

ORPO 则比较：

$$
\log\operatorname{odds}_\theta(y_w\mid x)
-
\log\operatorname{odds}_\theta(y_l\mid x)
$$

即 **Log-Odds Difference**。

两者都显式包含 Chosen 的正向学习：CPO 把它解释为 Behavior Cloning Regularizer；ORPO 则从一开始就把 SFT 与 Preference Alignment 合并为 Monolithic Objective。

因此两者虽然都可以概括成“Chosen NLL + Reference-free Preference Contrast”，但理论出发点不同：

- **CPO**：从 DPO 的 Reference 开销出发，用 Uniform-reference Surrogate + BC Regularizer 近似理想 Preference Objective；
- **ORPO**：从 SFT 不能充分区分 Preferred / Rejected 行为出发，用 Odds-Ratio Penalty 把 SFT 与 Preference Alignment 合为一个阶段。

### 2. CPO 与 SimPO：Preference Contrast 接近，但 Anchor 不同

CPO 的 Preference 部分是：

$$
-\log\sigma
\left(
\beta
\left[
\log\pi_\theta(y_w\mid x)
-
\log\pi_\theta(y_l\mid x)
\right]
\right)
$$

SimPO 则把 Score 明确定义为长度归一化的 Average Log Probability，并额外加入 Margin $\gamma$：

$$
-\log\sigma
\left(
\beta
\left[
\frac{1}{|y_w|}\log\pi_\theta(y_w\mid x)
-
\frac{1}{|y_l|}\log\pi_\theta(y_l\mid x)
\right]
-
\gamma
\right)
$$

SimPO 不使用 CPO 的 BC / NLL Regularizer；当前 TRL 文档也明确把 SimPO 描述为一种加入 Reward Margin、支持 Length Normalization、且不使用 BC Regularization 的 CPO-family alternative loss。参考：[TRL CPO Trainer](https://huggingface.co/docs/trl/cpo_trainer)。

因此两者最核心的区别可以概括为：

- **CPO**：用 Chosen NLL / BC 来确保 Policy 靠近 Preferred Distribution；
- **SimPO**：不用 BC，而用 Average Log Probability + Target Margin 来强化 Preference Separation。

### 3. 三者放在同一张设计表中

| 维度 | CPO | ORPO | SimPO |
| --- | --- | --- | --- |
| Reference Model | 不需要 | 不需要 | 不需要 |
| Preference Score | Chosen / Rejected Log Probability Difference | Chosen / Rejected Log-Odds Difference | Average Log-Probability Difference |
| Chosen NLL / SFT | **有，BC Regularizer** | **有，Monolithic SFT 项** | 无 |
| Length Normalization | 原始核心目标未专门加入 | 使用 Average Log-Likelihood | **核心设计** |
| 显式 Margin | 无 | 无 | **有 $\gamma$** |
| 主要设计动机 | Reference-free DPO surrogate + Preferred BC | SFT 与 Preference Alignment 单阶段合并 | Reference-free + Reward-Generation 对齐 + Length Normalization |

所以 CPO、ORPO、SimPO 更适合视为 DPO Design Space 中不同组件的组合，而不是严格的“前代 → 后代”关系。

---

## CPO 的核心 Trade-off 与缺点是什么？

CPO 最核心的交换关系来自它加入的 Behavior Cloning Regularizer：**它能保证 Preferred Response 获得直接正向 likelihood 信号，但也因此更依赖 Chosen 的绝对质量。**

### 1. BC Anchor 能减少纯相对优化问题，但放大错误 Chosen 的伤害

仅有 Pair-wise Contrast 时，Margin 变好并不意味着 Chosen 自身 likelihood 一定提高。CPO 增加：

$$
-\log\pi_\theta(y_w\mid x)
$$

可以直接把 Policy 拉向 Preferred Data Distribution，这是它相比纯 Preference-only Objective 的重要优点。

但如果：

$$
y_w=\text{差},\qquad y_l=\text{更差}
$$

CPO 不仅会学习 $y_w\succ y_l$，还会直接模仿那个“只是相对较好”的 $y_w$。因此错误 Label 或低质量 Chosen 会同时污染 **Contrastive Ranking Signal** 和 **Behavior Cloning Signal**。

### 2. Reference-free 提高效率，但失去显式 Reference / KL Anchor

CPO 不需要 Frozen Reference Model，降低了显存与 Forward 成本；但同时也没有 DPO / IPO 中显式的 Reference-based 行为约束。

BC 项提供的是“靠近 Preferred Data Distribution”的 Anchor，而不是“不要偏离原 Policy 太远”的 Reference / KL Anchor，两者含义不同。因此 Reference-free 不是无代价的简化。

### 3. Uniform-reference Surrogate 有理论假设，不是与 DPO 无条件等价

CPO 的理论解释依赖一个理想 Preferred Policy $\pi_w$，并证明 Uniform-reference Objective 在相应假设下可作为理想 Reference-based DPO Loss 的 Upper-bound Surrogate。

现实训练中真正的 $\pi_w$ 并不可获得，所以这个结果应理解为**近似依据**，而不是证明“任意场景下直接删掉 Reference 都严格等价于 DPO”。参考：[CPO，Theorem 1](https://arxiv.org/abs/2401.08417)。

### 4. 原始 CPO 的 Logistic Preference Term 仍没有 IPO 式有限最优 Margin

CPO 的 Preference Loss：

$$
-\log\sigma
\left(
\beta
\left[
\log\pi_\theta(y_w\mid x)
-
\log\pi_\theta(y_l\mid x)
\right]
\right)
$$

和 DPO 一样，只要 Preference Gap 继续增大，Loss 仍会继续减小，只是梯度逐渐衰减。因此 CPO 没有 IPO 那种：

$$
h^*=\frac{1}{2\beta}
$$

的有限最优点。

### 5. 原始 CPO 没有把 Length Normalization 作为核心修正

原论文的 Preference Term 直接使用完整 Response 的 $\log\pi_\theta(y\mid x)$；不同长度 Response 的 Sequence Log Probability 仍可能存在尺度耦合。

后来的 SimPO 明确把 Average Token Log Probability 与 Length Normalization 纳入核心 Reward 定义。TRL 当前文档也把 Length Normalization 作为 SimPO 相对 CPO 的显式变化之一。参考：[TRL CPO Trainer](https://huggingface.co/docs/trl/cpo_trainer)。

### 6. 仍然是 Offline Pair-wise Preference Optimization

CPO 仍基于固定的 $(x,y_w,y_l)$ 数据。它没有自动解决 Human / AI Judge Bias、Preference Label Noise、Policy 更新后的 Distribution Shift，以及当前 Policy 新产生的 Hard Negative / Failure Mode。

原始机器翻译实验实际上特别强调高质量但“不完美”的 Dis-preferred Translation：这些 Hard Negative 能提供更细粒度的对比信号。说明 CPO 的有效性同样高度依赖 Preference Pair 的构造质量。参考：[CPO，Sec. 3.1](https://arxiv.org/abs/2401.08417)。

### 7. 原论文的主要证据来自机器翻译

CPO 最初是在机器翻译场景提出和验证的。其 Loss 可以推广到 Chat 等一般 Preference Dataset，当前 TRL 也支持这一用途；但“原论文在 MT 上有效”不能直接等价为“在所有 LLM Alignment 场景都优于 DPO / SimPO / ORPO”。参考：[CPO](https://arxiv.org/abs/2401.08417)、[TRL CPO Trainer](https://huggingface.co/docs/trl/cpo_trainer)。

### 8. 仍然存在 Preference Proxy 的一般失效模式

只要 Chosen / Rejected 的标注机制不能完整表达真实目标，CPO 仍可能学习 Length / Style / Judge Bias，或在强优化下出现更一般的 [[LLM/后训练/Reward Hacking/Reward Hacking|Preference Overoptimization / Reward Hacking]]。

综合来看，CPO 可以概括为：

> **用 Uniform-reference Surrogate 把 DPO 的 Reference-dependent Preference Loss 化成当前 Policy 的 Chosen / Rejected Log-Likelihood Contrast，再加入 Preferred Response 的 Behavior Cloning / NLL Regularizer，使模型既“拉开 Winner 与 Loser”，又“真正靠近 Winner”。**

它的核心 trade-off 也来自后半句：**BC 能稳定 Preferred likelihood，却让训练更加依赖 Chosen 的绝对质量；Reference-free 降低了成本，却失去了显式 Reference / KL Anchor。**

---

## KTO 的基本原理是什么？

KTO（Kahneman-Tversky Optimization）与前面的 DPO、IPO、SimPO、ORPO、CPO 最大的区别，是它首先改变了 **Feedback Data 的基本单位**。DPO 等方法通常要求 Pair-wise Preference：

$$
(x,y_w,y_l),\qquad y_w\succ y_l
$$

KTO 只要求单条 Response 的二元反馈：

$$
(x,y,c),\qquad c\in\{\text{desirable},\text{undesirable}\}
$$

因此它天然适合 👍 / 👎、Accept / Reject、Good / Bad 这类现实产品反馈。论文把 KTO 构造为一种 Human-Aware Loss（HALO），其目标不是最大化某个 Preference Pair 的 likelihood，而是基于前景理论（Prospect Theory）的 Reference Point、Gain / Loss 和饱和 Value Function，直接最大化 generation 的主观 Utility。参考：[KTO: Model Alignment as Prospect Theoretic Optimization](https://arxiv.org/abs/2402.01306)。

### 1. KTO 仍然使用 Reference Policy 与隐式 Reward

标准 KTO 并不是 Reference-free。它定义：

$$
\boxed{
r_\theta(x,y)
=
\log\frac{\pi_\theta(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
}
$$

$r_\theta(x,y)$ 表示当前 Policy 相对于 Reference Policy 对某个 Response 的偏移：如果该值增大，说明当前模型相对 Reference 更愿意生成这个 Response。

这和 DPO 的 Policy / Reference Log-Ratio 有相同基础，但 KTO 不再用另一个 Response 的 Reward 作为比较对象。参考：[KTO，Sec. 4.1](https://arxiv.org/abs/2402.01306)。

### 2. 从“Response vs Response”改成“Response vs Reference Point”

DPO 比较：

$$
r_\theta(x,y_w)-r_\theta(x,y_l)
$$

KTO 则定义一个 Policy-level Reference Point：

$$
\boxed{
z_0
=
D_{\mathrm{KL}}
\left(
\pi_\theta(\cdot\mid x)
\Vert
\pi_{\mathrm{ref}}(\cdot\mid x)
\right)
}
$$

由于：

$$
D_{\mathrm{KL}}
\left(
\pi_\theta\Vert\pi_{\mathrm{ref}}
\right)
=
\mathbb E_{y'\sim\pi_\theta}
\left[
\log\frac{\pi_\theta(y'\mid x)}{\pi_{\mathrm{ref}}(y'\mid x)}
\right]
$$

因此 $z_0$ 可以理解为：**当前 Policy 相对 Reference 的平均隐式 Reward / 平均漂移水平。**

KTO 判断一个单独 Response 时，不再问“它是否比另一条 Response 更好”，而是问：

$$
r_\theta(x,y)-z_0
$$

相对于当前 Reference Point 是 Gain 还是 Loss。参考：[KTO，Eq. 8](https://arxiv.org/abs/2402.01306)。

### 3. 用前景理论式 Value Function 处理 Desirable / Undesirable

KTO 用 Logistic Function 替代经典 Kahneman-Tversky Value Function 中数值上更难优化的幂函数，并定义：

$$
v(x,y)
=
\begin{cases}
\lambda_D\sigma\left(\beta[r_\theta(x,y)-z_0]\right),
& y\sim y_{\mathrm{desirable}}\mid x
\\
\lambda_U\sigma\left(\beta[z_0-r_\theta(x,y)]\right),
& y\sim y_{\mathrm{undesirable}}\mid x
\end{cases}
$$

最终：

$$
\boxed{
\mathcal L_{\mathrm{KTO}}
=
\mathbb E_{(x,y)\sim\mathcal D}
\left[
\lambda_y-v(x,y)
\right]
}
$$

其中 $\lambda_y$ 根据样本标签取 $\lambda_D$ 或 $\lambda_U$。参考：[KTO，Eq. 8](https://arxiv.org/abs/2402.01306)。

直观上：

- Desirable：希望 $r_\theta(x,y)>z_0$，即把该 Response 推到 Reference Point 上方；
- Undesirable：希望 $r_\theta(x,y)<z_0$，即把该 Response 推到 Reference Point 下方。

因此 KTO 的核心关系可以压缩为：

> **DPO：Response vs Response；KTO：Response vs KL Reference Point。**

### 4. Sigmoid 饱和对应 Diminishing Sensitivity

KTO 的 Value Function 使用：

$$
\sigma(\beta\Delta)
$$

其中 $\Delta$ 是 Response 相对 Reference Point 的 Gain / Loss。当 $\Delta$ 接近 $0$ 时，Value Function 对变化最敏感；当 Response 已经远离 Reference Point 时，Sigmoid 逐渐饱和，额外改变 Reward 的收益越来越小。

这体现了前景理论中的 **Diminishing Sensitivity**：离 Reference Point 越远，对额外 Gain / Loss 的主观敏感度越低。

这与 IPO 的有限目标 Margin 不同。IPO 在超过目标 Margin 后会主动产生反向梯度把 Margin 拉回；KTO 只是逐渐饱和、让梯度趋近于 $0$，不会把一个“过于 desirable”的样本主动拉回。参考：[KTO，Sec. 4.1](https://arxiv.org/abs/2402.01306)。

### 5. $\lambda_D$、$\lambda_U$ 与 $\beta$ 控制什么？

$\lambda_D$ 与 $\lambda_U$ 分别控制 Desirable / Undesirable 样本的相对权重，因此可以表达 Gain / Loss 的非对称敏感度，也可以用于缓解类别不平衡。

$\beta$ 控制 Value Function 饱和速度：$\beta$ 越大，Sigmoid 越快饱和，Reference Point 附近获得高梯度的区域越窄。KTO 论文把它解释为风险厌恶 / 风险偏好的形状参数，并指出其作用虽然与 DPO 中 $\beta$ 在训练表现上有相似性，但理论来源不同。参考：[KTO，Sec. 4.1–4.2](https://arxiv.org/abs/2402.01306)。

需要注意，KTO 并不规定“Undesirable 永远必须权重更大”。论文允许根据任务和 Desirable / Undesirable 数量选择 $\lambda_D,\lambda_U$，其推荐比例来自具体实验，不应视为普遍规律。

### 6. 实际的 $z_0$ 使用近似估计，并且不对它反向传播

理论上的：

$$
z_0
=
D_{\mathrm{KL}}
\left(
\pi_\theta\Vert\pi_{\mathrm{ref}}
\right)
$$

如果每次都从当前 Policy 采样大量 Response 来精确估计，会非常昂贵。标准 KTO 实际在同一 microbatch 内把 Output 错位，构造 mismatched pairs，再估计共享 Reference Point：

$$
\hat z_0
=
\max\left(
0,
\frac{1}{m}
\sum_{i=1}^{m}
\log
\frac{
\pi_\theta(y_j\mid x_i)
}{
\pi_{\mathrm{ref}}(y_j\mid x_i)
}
\right)
$$

其中 $j=(i\bmod m)+1$。论文明确指出这是一个 **biased but convenient surrogate**；Clamping 进一步增加 upward bias，但可以降低方差。为提高稳定性，KTO **不通过 $z_0$ 反向传播**。该估计通常要求 microbatch size 至少为 $2$。参考：[KTO，KL Estimate](https://arxiv.org/abs/2402.01306)。

---

## KTO 相对 Pair-wise Preference 方法的核心 Trade-off 是什么？

KTO 最大的工程价值来自数据格式：**用更弱但更容易获得的 Binary Feedback，换掉更丰富但更昂贵的 Pair-wise Preference。**

### 1. 数据采集更自然、更便宜，但单条反馈信息更少

DPO / IPO / SimPO / ORPO / CPO 通常需要：

$$
(x,y_w,y_l)
$$

意味着同一 Prompt 下至少要准备两个候选，并由 Human / AI Judge 比较：

$$
y_w\succ y_l
$$

KTO 只要求：

$$
(x,y,\text{desirable/undesirable})
$$

因此实际产品中的 👍 / 👎 可以直接成为训练信号，不必重新组织成 Pair。KTO 原论文的动机之一正是 Binary Feedback 更丰富、更便宜、更快收集。参考：[KTO](https://arxiv.org/abs/2402.01306)。

代价是 Binary Label 不再告诉模型“这个回答相对于哪个具体候选更好”。KTO 因此用 Policy-level KL Reference Point $z_0$ 来替代 Pair-wise Baseline：

$$
\boxed{
\text{Pair-wise baseline}
\rightarrow
\text{Policy-level reference point}
}
$$

这就是 KTO 最核心的结构交换。

### 2. 不要把 Pair-wise Preference 机械拆成两个 Binary Labels

如果真实数据只有：

$$
y_w\succ y_l
$$

并不能推出：

$$
y_w=\text{desirable},\qquad y_l=\text{undesirable}
$$

因为 Pair 可能是“优秀 vs 尚可”，也可能是“差 vs 更差”。

KTO 论文为了与 Preference Dataset 做实验比较，会把 Chosen 视为 Desirable、Rejected 视为 Undesirable，但论文明确称这种转换是 **naive assumption**。因此 KTO 最自然的场景是原始反馈本身就是 Binary，而不是为了使用 KTO 强行把高质量 Pair-wise 信息降维。参考：[KTO，Data](https://arxiv.org/abs/2402.01306)。

### 3. KTO 的弱信号可以靠规模弥补，但不是无条件优于 Pairwise 方法

原论文在其 1B–30B 实验设置中发现，KTO 只用 Desirable / Undesirable Binary Signal 也可以匹配或超过一些 Preference-based 方法，并展示了强类别不平衡下的可用性。论文同时强调：**不存在一种 HALO 在所有场景中普遍最优**，最合适的 Loss 取决于任务需要的 inductive bias。参考：[Model Alignment as Prospect Theoretic Optimization，ICML 2024](https://proceedings.mlr.press/v235/ethayarajh24a.html)。

因此更准确的选择逻辑是：

- 已经天然拥有大量 👍 / 👎、Accept / Reject：KTO 的数据优势很明显；
- 已经拥有高质量、细粒度 Pair-wise Preference：Pair-wise 方法保留了更多相对信息，不能仅因为 KTO 不需要 Pair 就认为一定更合适。

---

## KTO 仍然存在哪些缺点？

KTO 解决的是“反馈是否必须成 Pair”这个问题，但并没有消除 Reference、数据质量和 Offline Alignment 的其他困难。

### 1. 标准 KTO 仍然需要 Reference Model

标准 KTO 同时使用：

$$
r_\theta(x,y)
=
\log\frac{\pi_\theta(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
$$

和：

$$
z_0
=
D_{\mathrm{KL}}
\left(
\pi_\theta\Vert\pi_{\mathrm{ref}}
\right)
$$

所以它不像 SimPO、ORPO、CPO 那样 Reference-free，仍有 Reference Model 的存储与 Forward 成本。KTO 论文也测试过 No-reference Variant，但其标准设计仍保留 Reference Model。参考：[KTO，Sec. 4.3](https://arxiv.org/abs/2402.01306)。

### 2. Reference Point 的估计本身是近似且有额外计算

理论上的 $z_0$ 需要对当前 Policy 分布求期望，精确计算很昂贵。标准实现通过 microbatch 错位 Response 得到 biased surrogate，还需要额外 Forward。Clamping 虽能降低方差，但进一步引入偏差。

因此 KTO 虽然降低了 Feedback Collection 的成本，却引入了一个比普通 Binary Classification 更复杂的 Policy-level Reference Point 估计机制。参考：[KTO，KL Estimate](https://arxiv.org/abs/2402.01306)。

### 3. Binary Feedback 丢失 Pair-wise Relation 的细粒度信息

单个 Label 只表达：

$$
y\in\{D,U\}
$$

并不表达两个具体候选之间谁更好、差多少、在哪个局部维度更好。因此如果数据原本就是高质量 Preference Pair，把它降成两个 Binary Label 可能损失有价值的信息。

### 4. Sigmoid Saturation 是 Regularization，也是潜在局限

KTO 的梯度随着 Response 远离 Reference Point 而趋近于 $0$，这可以避免对已经明显 Desirable / Undesirable 的样本持续强推。

但饱和也意味着：极端区域中的样本获得的训练信号会变弱。这个机制本质上是一种 inductive bias，并不保证对所有任务都最合适。原论文也明确强调不同 HALO 的优劣取决于任务的 inductive bias。参考：[KTO](https://arxiv.org/abs/2402.01306)。

### 5. 对超参数与类别构成仍然敏感

KTO 至少需要处理 $\beta$、$\lambda_D$、$\lambda_U$，而且合适的权重与 Desirable / Undesirable 比例、模型规模、Reference Model 质量和具体任务相关。

论文给出的 $\lambda_D n_D/(\lambda_U n_U)$ 区间等都是实验经验，而不是通用理论定律；对于 Toxicity Prevention 等“避免坏行为”比“产生好行为”更重要的任务，合适的权重方向也可能不同。参考：[KTO，Sec. 4.2](https://arxiv.org/abs/2402.01306)。

### 6. 经典 KTO 仍然是 Offline Alignment

标准 KTO 使用固定的 Binary Feedback Dataset。随着 Policy 改变，旧数据仍可能出现 Distribution Shift，也不能自动覆盖当前 Policy 新产生的 Failure Mode。

因此 Binary Feedback 更容易收集，不等于 KTO 自身已经解决 Online / Iterative Data Collection。

### 7. Binary Label 仍然是 Proxy，仍可能出现一般 Alignment Failure

Desirable / Undesirable 的定义依然来自 Human、AI Judge、规则或业务反馈。Label Noise、Style Bias、Sycophancy、Reward Hacking / Specification Gaming 等问题仍然可能存在。

KTO 改变的是 Feedback Granularity 与 Loss 的 inductive bias，而不是把 Alignment Objective 变成了真实 Utility。可以继续参见 [[LLM/后训练/Reward Hacking/Reward Hacking|Reward Hacking]]。

综合来看，KTO 可以压缩成：

> **KTO 保留 Policy / Reference Log-Ratio 作为隐式 Reward，但用当前 Policy 相对 Reference 的 KL 作为 Reference Point，把单条 Response 判断为相对 Gain 或 Loss，再通过前景理论式的饱和 Value Function 优化 Desirable / Undesirable Binary Feedback。**

它最大的工程价值是：

$$
(x,y_w,y_l)
\rightarrow
(x,y,\text{desirable/undesirable})
$$

但对应的 trade-off 也很明确：**数据更便宜、更自然，却失去了 Pair-wise Relation 的细粒度信息，并仍然需要 Reference Model 与 KL Reference Point。**