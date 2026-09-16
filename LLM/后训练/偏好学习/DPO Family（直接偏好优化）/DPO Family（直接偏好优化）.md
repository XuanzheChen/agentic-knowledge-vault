# DPO Family（直接偏好优化）

[[LLM/后训练/偏好学习/偏好学习|返回上级：偏好学习]] · [[main|返回知识主干]]

围绕 DPO（Direct Preference Optimization）及其后续变体整理直接偏好优化方法。当前记录 DPO 与 IPO 的核心原理、改进关系和局限，后续再逐步扩展 SimPO、ORPO、KTO 等方法。

## 问题目录

- [[DPO Family（直接偏好优化）#DPO 的数学原理是什么？|DPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#DPO 存在哪些主要缺点？|DPO 存在哪些主要缺点？]]
- [[DPO Family（直接偏好优化）#IPO 的数学原理是什么？|IPO 的数学原理是什么？]]
- [[DPO Family（直接偏好优化）#IPO 相对 DPO 做了哪些改进？|IPO 相对 DPO 做了哪些改进？]]
- [[DPO Family（直接偏好优化）#IPO 仍然存在哪些不足？|IPO 仍然存在哪些不足？]]

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

其中 **β（beta）** 控制“追求更高 Reward”和“保持接近 Reference Policy”之间的权衡。

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

将前面的 Reward 重参数化代入后，$\beta\log Z(x)$ 在 Reward 差中抵消：

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

---

## IPO 的数学原理是什么？

IPO（Identity Preference Optimization）来自更一般的 $\Psi$PO 理论框架。它关注的是 DPO 仍然保留的一层假设：**把 Pair-wise Preference 解释成某个 Point-wise Scalar Reward 的差，再通过 Bradley-Terry / Logistic Link 建模偏好概率。** $\Psi$PO 希望直接从 Pair-wise Preference 出发，避免必须先假设存在这样一个潜在标量 Reward。参考：[A General Theoretical Paradigm to Understand Learning from Human Preferences](https://arxiv.org/abs/2310.12036)。

### 1. 从 Preference Probability 本身出发

记真实偏好概率为：

$$
p^*(y\succ y'\mid x)
$$

它表示在 Prompt $x$ 下，Response $y$ 胜过 $y'$ 的概率。$\Psi$PO 的一般目标可以理解为：直接利用 Pair-wise Preference 的某种变换 $\Psi(p^*)$ 来优化 Policy，同时继续用 KL Regularization 限制 Policy 偏离 Reference Policy。

IPO 选择最简单的 Identity Mapping：

$$
\Psi(p)=p
$$

因此“Identity Preference Optimization”中的 Identity 指的是：**直接使用 Preference Probability 本身，而不是像 DPO 那样先经过 Logistic / Logit 形式映射为潜在 Reward Difference。**

对于一个回答 $y$，可以定义它相对某个比较分布 $\mu$ 的平均偏好胜率：

$$
p^*(y\succ\mu)
=
\mathbb{E}_{y'\sim\mu}
\left[p^*(y\succ y')\right]
$$

由于它本身是概率，因此有：

$$
0\le p^*(y\succ\mu)\le 1
$$

这与 DPO 中经过 Logit / Reward 重参数化后可能无界增长的隐式 Reward 有本质区别。

### 2. 用 Policy / Reference Log-Ratio 表示相对 Preference

定义 Policy 相对于 Reference Policy 的成对 Log-Ratio Difference：

$$
h_\pi(y,y')
=
\log\frac{\pi(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
-
\log\frac{\pi(y'\mid x)}{\pi_{\mathrm{ref}}(y'\mid x)}
$$

IPO 的 Population Objective 可以导出一个有限的最优条件：

$$
h_\pi(y,y')
=
\frac{1}{\tau}
\left[
p^*(y\succ\mu)-p^*(y'\succ\mu)
\right]
$$

其中 $\tau$ 是 KL Regularization 系数。由于右侧由偏好概率之差构成，它不会像 DPO 中由 Logit 产生的 Reward Difference 那样趋向无穷。

### 3. 实际训练时得到平方误差形式

现实数据并不会直接给出完整的 $p^*(y\succ\mu)$，通常只有采样得到的 Preference Pair $(x,y_w,y_l)$。利用 Pair-wise Preference 数据的对称性，IPO 可以得到可直接优化的 Sampled Loss：

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

其中：

$$
h_\theta(y_w,y_l)
=
\log\frac{\pi_\theta(y_w\mid x)}{\pi_{\mathrm{ref}}(y_w\mid x)}
-
\log\frac{\pi_\theta(y_l\mid x)}{\pi_{\mathrm{ref}}(y_l\mid x)}
$$

许多工程实现把论文中的 $\tau$ 记为 **β（beta）**，此时目标 Margin 写成：

$$
\boxed{
h_\theta^*=\frac{1}{2\beta}
}
$$

Hugging Face TRL 也明确说明：IPO Loss 中的 **β（beta）** 对应原论文中的 $\tau$。参考：[TRL DPO Trainer](https://huggingface.co/docs/trl/main/trainer)。

### 4. 为什么平方 Loss 很关键？

DPO 对相同 Margin $h$ 的目标为：

$$
\mathcal L_{\mathrm{DPO}}
=-\log\sigma(\beta h)
$$

只要 $h$ 仍然有限，Loss 就会继续通过减小而鼓励：

$$
h\rightarrow +\infty
$$

IPO 则是：

$$
\mathcal L_{\mathrm{IPO}}
=
\left(h-\frac{1}{2\beta}\right)^2
$$

因此存在有限最优点：

$$
h^*=\frac{1}{2\beta}
$$

其梯度为：

$$
\frac{\partial \mathcal L_{\mathrm{IPO}}}{\partial h}
=
2\left(h-\frac{1}{2\beta}\right)
$$

所以：

- 当 $h<\frac{1}{2\beta}$ 时，IPO 推动 Margin 增大；
- 当 $h=\frac{1}{2\beta}$ 时，该 Pair 的梯度为 $0$；
- 当 $h>\frac{1}{2\beta}$ 时，IPO 会反向把过大的 Margin 拉回来。

这说明 IPO 不是简单地“让 Winner 越来越赢”，而是让 Policy / Reference Log-Ratio Difference 靠近一个**有限的目标 Margin**。

---

## IPO 相对 DPO 做了哪些改进？

IPO 的主要改进并不是单纯“把 Sigmoid 换成平方 Loss”，而是重新审视 DPO 如何把 Pair-wise Preference 转化为优化目标。

### 1. 减少对 Point-wise Scalar Reward 假设的依赖

DPO 虽然没有显式训练 Reward Model，但仍利用 Bradley-Terry 模型，把 Pair-wise Preference 解释成潜在 Scalar Reward Difference。IPO 所属的 $\Psi$PO 框架直接把 Pair-wise Preference Probability 当作基本对象，不要求先假设所有偏好都能够由一个全局 Point-wise Reward 完整表示。

这对真实 Human / AI Preference 很重要，因为现实偏好可能包含噪声、多目标冲突甚至非传递关系，并不一定严格服从单一标量 Reward 的排序。参考：[A General Theoretical Paradigm to Understand Learning from Human Preferences](https://arxiv.org/abs/2310.12036)。

### 2. 把无界 Preference Margin 改成有限目标 Margin

DPO 的 Logistic Loss 对一个固定的 Chosen / Rejected Pair 没有有限的最优 Margin：理论上会持续推动 $h$ 增大，只是梯度逐渐变小。

IPO 改为：

$$
h^*=\frac{1}{2\beta}
$$

因此 Preference Signal 只要求 Chosen 相对 Rejected 达到一个适当优势，而不是无限拉大两者差距。这能降低 Near-deterministic Preference 下的过拟合风险，并让 KL Regularization 的约束更明确地保留下来。

### 3. 对“偏好只说明谁更好”这一信息量更保守

一条数据 $(y_w,y_l)$ 只说明：

$$
y_w\succ y_l
$$

它并没有直接说明：

$$
y_w\gg y_l
$$

IPO 的有限 Margin 更符合这种信息边界：已经把 Winner 与 Loser 区分到目标程度后，不再继续要求二者越来越远。

### 4. 仍保留 DPO 的直接训练优势

IPO 仍然可以直接使用固定 Pair-wise Preference Dataset 训练 Policy，不需要先训练一个独立 Reward Model，也不需要像 PPO / GRPO 一样依赖训练中的 Rollout、Advantage Estimation 和 Policy Gradient。

因此它保留了 DPO 在工程上的主要优点，同时修改了 Preference Objective 的统计与正则化行为。

可以把两者最核心的差异压缩成：

| 维度 | DPO | IPO |
| --- | --- | --- |
| Preference 建模 | Bradley-Terry / Logistic，隐式 Point-wise Reward | $\Psi$PO 中直接处理 Pair-wise Preference，$\Psi(p)=p$ |
| Loss | $-\log\sigma(\beta h)$ | $(h-1/(2\beta))^2$ |
| 最优 Margin | $h\rightarrow+\infty$ | $h=1/(2\beta)$ |
| Margin 过大时 | 仍继续鼓励增大，只是梯度趋小 | 主动把 Margin 拉回目标值 |
| 独立 Reward Model | 不需要 | 不需要 |
| Reference Policy | 需要 | 仍需要 |

---

## IPO 仍然存在哪些不足？

IPO 主要修正的是 **DPO 的 Preference / Reward 建模与无界 Margin 问题**，并没有同时解决 DPO Family 的所有局限。

### 1. 仍然需要 Reference Policy

IPO 的核心量仍然是：

$$
\log\frac{\pi_\theta(y\mid x)}{\pi_{\mathrm{ref}}(y\mid x)}
$$

因此训练仍需要 Reference Model 的 Log Probability。它没有解决经典 DPO 的额外显存、存储与 Forward 计算开销。

后续 SimPO 等方法会进一步追问：**既然目标是直接 Preference Optimization，Reference Model 是否一定必要？**

### 2. 固定目标 Margin 由单个超参数控制

IPO 对采样 Pair 使用：

$$
h^*=\frac{1}{2\beta}
$$

这提供了稳定的有限最优点，但也意味着目标 Margin 很依赖 **β（beta）** 的选择。

不同 Pair 的真实 Preference Strength 可能差异很大：某些只是“略好”，另一些可能是“明显错误 vs 完全正确”。标准 IPO 的 Sampled Loss 并不会直接从单次 Binary Pair 标签中恢复这种细粒度强度，因此 **β（beta）** 的选择会影响整体 Regularization 与区分强度。

### 3. 仍依赖 Pair-wise Preference 数据质量

IPO 不再要求把 Preference 完全解释成 Point-wise Reward，但实际训练依然使用 $(x,y_w,y_l)$ Pair。如果 Preference Label 本身错误、Judge 有系统性偏差，或者训练 Pair 缺乏代表性，IPO 仍会学习错误关系。

有限 Margin 可以缓解“对单个 Pair 过度放大”的问题，但不能自动判断一个 Preference Label 是否正确。

### 4. 核心理论没有自动解决长度偏置

IPO 修改的是 Preference Objective 和 Margin 行为，并不是专门为 Sequence Length Bias 设计的。若 $h_\theta$ 基于完整 Response 的 Sequence Log Probability，长度仍可能影响 Score 的尺度。

一些工程实现可以采用 Length Normalization，但这属于额外实现选择，不是 IPO 理论本身最主要的解决点。后续 SimPO 会把长度归一化直接纳入隐式 Reward 设计。

### 5. 经典 IPO 仍然是 Offline Preference Optimization

与经典 DPO 一样，IPO 通常从固定 Preference Dataset 学习：

> **旧 Policy 产生候选 → 构造 Preference Pair → 固定数据训练 Policy**

因此随着 Policy 更新，仍然可能出现 Preference Dataset 与当前 Policy 输出分布不一致的问题。IPO 解决了 Loss 的正则化与 Preference 建模问题，但没有自动解决 Distribution Shift、Hard Negative 更新或新 Failure Mode 覆盖问题。

$\Psi$PO / IPO 后续也可以扩展为 Online 形式，但这是训练 Pipeline 的进一步变化，而不是经典 IPO Sampled Loss 本身已经解决的问题。参考：[A General Theoretical Paradigm to Understand Learning from Human Preferences](https://arxiv.org/abs/2310.12036)。

### 6. 仍然主要提供相对偏好，而不是绝对质量保证

如果：

$$
y_w\succ y_l
$$

但 $y_w$ 和 $y_l$ 本身都很差，IPO 仍然主要学习两者之间的相对关系。有限 Margin 并不会自动告诉模型“Chosen 是否已经达到足够高的绝对质量”。

因此 IPO 仍然需要高质量候选生成、SFT、Verifier、Absolute Evaluation 或其他 Reward Signal 配合。

综合来看，IPO 可以被理解为对 DPO 的第一类重要理论修正：**把“Preference Margin 越大越好”改为“Preference Margin 达到有限目标即可”，并从直接 Pair-wise Preference 的角度重新建立优化目标。** 但它仍然保留 Reference Model、Pair-wise 数据、Offline Distribution Shift 和相对质量学习等问题，这些正是后续 SimPO、KTO、Online Preference Optimization 等方法继续修改的方向。