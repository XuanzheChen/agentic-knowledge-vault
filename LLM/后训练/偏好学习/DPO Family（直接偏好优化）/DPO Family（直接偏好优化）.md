# DPO Family（直接偏好优化）

[[LLM/后训练/偏好学习/偏好学习|返回上级：偏好学习]] · [[main|返回知识主干]]

围绕 DPO（Direct Preference Optimization）及其后续变体整理直接偏好优化方法。当前重点记录 DPO、IPO 与 SimPO 的数学原理、改进关系和仍然存在的局限，后续再逐步扩展 ORPO、KTO 等方法。

## 问题目录

- [[DPO Family（直接偏好优化）#DPO 的数学原理是什么？|DPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#DPO 存在哪些主要缺点？|DPO 存在哪些主要缺点？]]
- [[DPO Family（直接偏好优化）#IPO 的数学原理是什么？|IPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#IPO 相对 DPO 做了哪些改进？|IPO 相对 DPO 做了哪些改进？]]
- [[DPO Family（直接偏好优化）#IPO 仍然存在哪些不足？|IPO 仍然存在哪些不足？]]
- [[DPO Family（直接偏好优化）#SimPO 的数学原理是什么？|SimPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#SimPO 相对 IPO 做了哪些改进？|SimPO 相对 IPO 做了哪些改进？]]
- [[DPO Family（直接偏好优化）#SimPO 仍然存在哪些缺点？|SimPO 仍然存在哪些缺点？]]

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