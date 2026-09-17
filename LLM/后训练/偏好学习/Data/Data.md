# Data

[[LLM/后训练/偏好学习/偏好学习|返回上级：偏好学习]] · [[main|返回知识主干]]

围绕偏好学习中的 Prompt 选择、Candidate 生成、Pair 构造、Hard-negative Mining、Active Data Collection、标注质量与在线数据迭代整理 Q&A。

## 问题目录

- [[Data#偏好数据构造的整体流程是什么，为什么不能只随机配对？|偏好数据构造的整体流程是什么，为什么不能只随机配对？]]
- [[Data#Hard-negative Mining 是什么，如何构造 Hard Preference Pair？|Hard-negative Mining 是什么，如何构造 Hard Preference Pair？]]
- [[Data#偏好 Pair 的难度应该如何控制，为什么不是越 Hard 越好？|偏好 Pair 的难度应该如何控制，为什么不是越 Hard 越好？]]
- [[Data#Uncertainty Sampling 是什么，如何区分真正有价值的不确定性？|Uncertainty Sampling 是什么，如何区分真正有价值的不确定性？]]
- [[Data#Active Data Collection 是什么，常用 Acquisition 方法有哪些？|Active Data Collection 是什么，常用 Acquisition 方法有哪些？]]
- [[Data#Candidate Pool 与 Preference Pair 通常如何构造？|Candidate Pool 与 Preference Pair 通常如何构造？]]
- [[Data#Preference Annotation 如何降低标签噪声与评价偏差？|Preference Annotation 如何降低标签噪声与评价偏差？]]
- [[Data#Online Preference Data Flywheel 是如何运转的？|Online Preference Data Flywheel 是如何运转的？]]

---

## 偏好数据构造的整体流程是什么，为什么不能只随机配对？

偏好学习最终常使用形如 $(x,y_w,y_l)$ 的数据，但一个 Preference Pair 在进入训练之前，实际上经历了多层选择：

> **Prompt Selection → Candidate Generation → Pair Selection → Preference Labeling → Filtering / Weighting / Balancing**

因此“偏好数据构造”不只是给两个回答标出 Chosen / Rejected，而至少包含三个选择问题：

1. **哪些 Prompt 值得进入偏好数据集？** 要覆盖真实使用分布、当前模型薄弱能力以及重要边界场景。
2. **一个 Prompt 下应该生成哪些 Candidate？** Candidate 的质量跨度、来源模型和采样策略会决定后续能构造出什么样的 Pair。
3. **多个 Candidate 中，哪两个最值得比较？** 同样正确的 Preference Label，其训练价值可能完全不同。

例如同一 Prompt 下有四个回答，其真实质量大致为：

$$
0.95,\quad 0.90,\quad 0.45,\quad 0.10
$$

把 $0.95$ 与 $0.10$ 配成 Pair 很容易得到可靠标签，但它主要告诉模型“明显好的回答优于明显坏的回答”；而比较 $0.95$ 与 $0.90$，可能暴露更细粒度的事实错误、推理缺陷、指令遵循差异或风格边界。

因此偏好数据的价值不能只看 Label 是否正确，还要考虑：

- **Informativeness**：这条比较是否能提供当前模型尚未掌握的决策边界？
- **Reliability**：标注者能否稳定判断哪一个更好？
- **Coverage / Diversity**：数据是否覆盖不同能力、任务和失败模式？
- **Policy Relevance**：这些 Candidate 是否仍代表当前 Policy 会产生的输出？

Active Preference Optimization 的研究将 RLHF 中“应当查询哪些 Prompt / Generation Pair”直接建模为有预算约束的数据选择问题，而不是默认均匀随机采样。参考：[Active Preference Optimization for Sample Efficient RLHF](https://arxiv.org/abs/2402.10500)。

> **偏好数据构造的核心不是尽可能多地产生 Chosen / Rejected，而是在有限标注预算下持续获得对当前 Policy 最有信息量、标签足够可靠并覆盖真实分布的比较。**

---

## Hard-negative Mining 是什么，如何构造 Hard Preference Pair？

Hard-negative Mining 的目标是寻找：**质量较高、外观看起来很像正确答案，但仍存在关键缺陷的 Rejected Response。**

如果已经有一个较好的 Chosen $y_w$，并有 Reward Model、Verifier 或 Judge 给 Candidate 打分 $s(x,y)$，一种最直接的 Hard-negative Mining 是在明确不满足目标的 Candidate 中选择得分最高者：

$$
y_l
=
\arg\max_{y\in\mathcal Y_{\mathrm{negative}}} s(x,y)
$$

这样得到的 $y_l$ 不再是“完全错误”的 Easy Negative，而是靠近高质量区域、容易与 $y_w$ 混淆的负样本。

典型 Hard Negative 包括：

- **Reasoning**：整条 CoT 大部分正确，只在某个较深步骤出现隐蔽的逻辑、代数或数值错误。
- **Code**：主逻辑正确，但漏掉一个边界条件、异常处理或状态更新。
- **Instruction Following**：回答内容正确，但遗漏一个用户明确要求的约束。
- **Tool / Agent**：最终结果看似合理，但中间调用了错误工具、使用了不允许的资源或依赖偶然环境状态。

Hard-negative 的训练价值来自它更接近当前模型真正的决策边界：模型不能只学到“明显垃圾输出要拒绝”，而需要学习**哪个细节使一个近似正确的 Response 仍然不够好**。

Hard Negative 也可以主动生成，而不是只从已有 Candidate 中挖掘。例如：

- 从正确 CoT 中替换一个推理步骤；
- 从正确代码中删除一个边界条件；
- 对高质量回答注入一个细粒度事实错误；
- 让当前 Policy 对同一个 Prompt 多次采样，再用 Verifier 从错误答案中选最接近正确者。

已有工作使用 Verifier 识别“near-correct yet structurally flawed”的数学解答并构造 Hard Negative，用于加强 DPO 的训练信号。参考：[Hard Negative Sample-Augmented DPO Post-Training for Small Language Models](https://arxiv.org/abs/2512.19728)。

但 Hard-negative Mining 并不意味着“分数越接近越好”，因为极小差距可能意味着 Pair 本身没有稳定优劣。这个问题需要与 Pair Difficulty 和 Uncertainty 分开处理。

---

## 偏好 Pair 的难度应该如何控制，为什么不是越 Hard 越好？

如果两个 Candidate 的质量分数分别是 $s_w$ 与 $s_l$，可以用 Margin：

$$
\Delta = s_w-s_l
$$

粗略描述 Pair Difficulty。通常：

- $\Delta$ 很大：**Easy Pair**，标签稳定，但对决策边界提供的信息有限；
- $\Delta$ 适中：**Hard but Learnable Pair**，两个答案接近，但仍有可解释、可重复的优劣关系；
- $\Delta\approx0$：可能是极难 Pair，也可能只是**Ambiguous / Noisy Pair**。

因此必须区分：

> **Hard = 难分，但仍然可分；Ambiguous = 评价标准本身不足以稳定决定谁更好。**

例如一个回答更简洁，另一个更详细，如果 Rubric 没有说明应该优先 Conciseness 还是 Completeness，那么强迫标注成 $A\succ B$ 很可能只是制造标签噪声。

实际数据构造可以采用一个 Difficulty Window，而不是单纯选最小 Margin：

$$
\Delta_{\min}
<
\Delta
<
\Delta_{\max}
$$

同时保留一定比例的 Easy / Medium / Hard Pair，使训练既有稳定的大方向监督，又能逐渐学习细粒度边界。

另一种思路是保留 Pair 的相对质量差，而不把所有数据压成同样权重的二元标签。例如 Margin Matching Preference Optimization 使用 Pair 的 Quality Margin 构造 Soft Target Probability，使“明显优于”和“略微优于”产生不同监督强度。参考：[Margin Matching Preference Optimization](https://arxiv.org/abs/2410.03145)。

较新的 Difficulty-aware 研究也指出，小 Margin Pair 并不等价于“无价值噪声”；它们是否有用与优化目标有关。MixDPO 因此按照 Pair Difficulty 从 Easy 到 Hard 构造 Curriculum，并对困难 Pair 使用不同训练方式。参考：[Small-Margin Preferences Still Matter—If You Train Them Right](https://arxiv.org/abs/2602.00954)。

> **Preference Data 的目标不是无限提高 Difficulty，而是找到“足够难以提供新信息、又足够清楚以获得可靠标签”的区域。**

---

## Uncertainty Sampling 是什么，如何区分真正有价值的不确定性？

Hard-negative Mining 从**样本本身有多难**出发；Uncertainty Sampling 则从**当前模型对哪些数据最没有把握**出发。

假设 Preference Model 输出：

$$
p_\phi(y_1\succ y_2\mid x)
$$

如果 $p\approx0.99$，当前模型已经非常确定；如果 $p\approx0.5$，模型对两个 Candidate 的优劣判断最不确定。因此可以优先请求这类 Pair 的 Human / AI Label。

最常见的选择指标包括：

### Entropy Sampling

$$
H(p)
=
-p\log p-(1-p)\log(1-p)
$$

选择 $H(p)$ 最大的 Pair，其最大值出现在 $p=0.5$ 附近。

### Margin Sampling

如果直接使用 Preference Probability，可选择：

$$
\arg\min |p-0.5|
$$

如果模型输出两个 Reward Score，也可以用：

$$
\arg\min
|r(x,y_1)-r(x,y_2)|
$$

但“模型不确定”有两种完全不同的来源：

- **Epistemic Uncertainty**：答案原则上可以确定，只是当前模型还没学会。例如人类标注高度一致，但 RM 仍然犹豫。这类数据通常很值得补充。
- **Aleatoric Uncertainty**：任务或评价标准本身就存在天然歧义。例如两个回答各自在不同维度更优，不同标注者长期都可能意见不一。继续增加类似标签未必能消除这种不确定性。

因此不能简单执行“Top-$K$ 最接近 $0.5$ 的 Pair 全部送标”。一个高质量 Active Learning 系统需要尽量寻找**模型可以通过新增监督消除的不确定性**，而不是不断收集本身就没有稳定答案的 Pair。

BAL-PM（Bayesian Active Learner for Preference Modeling）显式关注 Preference Model 的 Epistemic Uncertainty，并指出只按不确定性选择容易获得大量相似、冗余样本，因此还同时考虑 Prompt Feature Space 中的分布覆盖。参考：[Deep Bayesian Active Learning for Preference Modeling in Large Language Models](https://arxiv.org/abs/2406.10023)。

---

## Active Data Collection 是什么，常用 Acquisition 方法有哪些？

Active Data Collection 把“偏好数据从哪里来”变成一个持续决策问题：**在标注预算有限时，下一批最值得采集和标注的数据是什么？**

它可以主动选择的不只是 Pair，而是整个数据链路：

$$
\text{Prompt}
\rightarrow
\text{Candidate}
\rightarrow
\text{Pair}
\rightarrow
\text{Label}
$$

也就是说可以分别决定：

- 哪些 Prompt 值得继续采集；
- 每个 Prompt 是否需要更多 Candidate；
- 哪一组 Candidate 最值得组成 Pair；
- 哪些 Pair 值得使用昂贵 Human Label，哪些可以交给 AI Judge / Verifier。

常见 Acquisition 思想包括：

| 方法 | 核心思想 |
| --- | --- |
| **Random Sampling** | 随机选择，作为最基本 Baseline |
| **Least Confidence / Entropy Sampling** | 选择当前模型最没有把握的数据 |
| **Margin Sampling** | 选择 Preference Margin 较小的数据 |
| **Query-by-Committee** | 多个 RM / Judge 对同一 Pair 判断分歧越大，越值得标注 |
| **BALD / Bayesian Active Learning** | 选择预期能最大程度降低模型参数不确定性的样本 |
| **Clustering / Core-set / K-center** | 优先保证 Feature Space 的代表性与覆盖率 |
| **Uncertainty + Diversity** | 同时考虑“难”与“不重复”，避免 Top-$K$ 全来自同一狭窄区域 |
| **UCB / Bandit-style Acquisition** | 在当前高价值区域与高不确定区域之间平衡 Exploitation 和 Exploration |
| **Optimal Design** | 从参数估计角度选择最有信息量的数据，例如 D-optimal Design |

这些方法不一定互斥。一个实际 Acquisition Score 可以抽象成：

$$
A(z)
=
\alpha U(z)
+
\beta D(z)
+
\gamma V(z)
$$

其中 $U$ 表示 Uncertainty，$D$ 表示 Diversity / Coverage，$V$ 表示预计训练价值。

几种在 LLM Preference Learning 中较有代表性的路线包括：

- **APO（Active Preference Optimization）**：把 RLHF 表述为 Contextual Preference Bandit，主动查询更重要的 Preference Data，而不是均匀随机采样。参考：[Active Preference Optimization for Sample Efficient RLHF](https://arxiv.org/abs/2402.10500)。
- **APPO / ADPO**：把 Active Query 分别与 PPO / DPO 结合；ADPO 的实验显示，在减少大量 Human Preference Query 的情况下仍可接近标准 DPO 的效果。参考：[Reinforcement Learning from Human Feedback with Active Queries](https://arxiv.org/abs/2402.09401)。
- **BAL-PM**：结合 Bayesian Epistemic Uncertainty 与 Prompt Feature-space Diversity，减少冗余标注。参考：[Deep Bayesian Active Learning for Preference Modeling in Large Language Models](https://arxiv.org/abs/2406.10023)。
- **Active Learning for DPO**：对 DPO 的局部表示进行线性化，再使用 D-optimal Design 选择更有信息量的 Preference Feedback，可用于在线查询或离线子集选择。参考：[Active Learning for Direct Preference Optimization](https://arxiv.org/abs/2503.01076)。

> **Hard-negative Mining 和 Uncertainty Sampling 都可以视为 Active Data Collection 中的 Acquisition Strategy；Active Data Collection 是更上层的数据闭环。**

---

## Candidate Pool 与 Preference Pair 通常如何构造？

Active Selection 的前提是先有一个足够好的 Candidate Pool。如果 Candidate 本身过于单一，即使 Pair Selection 很聪明，也无法得到高价值偏好数据。

常见 Candidate 生成方式包括：

1. **当前 Policy 多次采样**：对同一个 Prompt 使用不同 Random Seed、Temperature 或 Top-$p$ 生成多个 Candidate。优点是最贴近当前 Policy Distribution。
2. **混合不同 Checkpoint**：例如 SFT Model、旧版 Preference Model、Current Policy 一起生成，使 Candidate 覆盖不同能力阶段。
3. **混合不同强弱模型**：Target Model、Teacher Model、Strong Model 分别生成，扩大质量跨度。
4. **Error Injection / Perturbation**：从高质量答案主动注入局部错误，构造结构化 Hard Negative，例如替换一个 CoT Step、删除一个代码边界条件。

如果一个 Prompt 有 $K$ 个 Candidate，则理论上可以构造：

$$
\binom K2
$$

个 Pair。但全量比较通常既昂贵又冗余，因此常用的 Pair Construction 包括：

- **Best-vs-Worst**：标签最稳定，适合提供基础方向监督，但通常偏 Easy。
- **Best-vs-Near-Best**：典型 Hard Pair，更适合细粒度行为边界。
- **Adjacent Pair**：先对 Candidate 排序，再比较相邻等级，例如 $(y_1,y_2)$、$(y_2,y_3)$。
- **Margin-based Pair**：只选择 Score Gap 落在指定区间的 Candidate。
- **Uncertainty / Disagreement Pair**：优先比较当前 RM 或多个 Judge 最难判断的 Candidate。

因此一个更完整的 Preference Pair Mining Pipeline 可以写成：

> **生成 $K$ 个 Candidate → 去重 / 基础过滤 → Verifier / RM / Judge 打分 → 构造 Easy / Medium / Hard Candidate Pair → 对高价值 Pair 请求更可靠标注。**

实际训练数据通常不应全部由 Hard Pair 构成。比较稳健的做法是混合：

$$
D
=
D_{\mathrm{easy}}
+
D_{\mathrm{hard}}
+
D_{\mathrm{uncertain}}
+
D_{\mathrm{coverage}}
$$

使数据同时具备稳定监督、边界信息和任务覆盖率。

---

## Preference Annotation 如何降低标签噪声与评价偏差？

即使 Pair Selection 很好，如果 Label 本身不可靠，Active Mining 反而会把标注错误放大。因此偏好数据构造还必须把 **Annotation Quality** 当作独立环节。

首先，不应该在所有情况下都强迫标注者进行 $A/B$ 二选一。对于高难度 Pair，更合理的 Label Space 可以包含：

- A better
- B better
- Tie / Equally good
- Both bad
- Cannot determine / Need more context

这样可以避免把天然 Ambiguous Pair 人为转成错误的强偏好。

其次，要控制评价器的系统性 Bias：

- **Position Bias**：Candidate 放在 A 还是 B 可能影响 Human / AI Judge 的判断，因此可以交换顺序重复评价并做一致性检查。
- **Length / Style Bias**：Judge 可能把更长、更正式或更多分点误当成更高质量，需要明确 Rubric 并做 Length-controlled Evaluation。
- **Dimension Conflict**：Correctness、Helpfulness、Safety、Conciseness 等目标可能冲突，应明确优先级，而不是让标注者凭模糊“喜欢程度”决定。

RLAIF 的工作在 AI Preference Labeling 中专门通过交换两个 Candidate 的顺序并聚合两次判断来缓解 Position Bias。参考：[RLAIF: Scaling Reinforcement Learning from Human Feedback with AI Feedback](https://arxiv.org/abs/2309.00267)。

对于关键数据，还可以采用：

- 多 Human / Multi-Judge 重复标注；
- Judge Agreement / Inter-annotator Agreement 过滤；
- Verifier 与 Judge 交叉校验；
- 对高不确定 Pair 升级到更强 Judge 或人工专家；
- 保留 Soft Preference / Confidence，而不是只保存二元标签。

因此高质量偏好数据不是简单的 $(x,y_w,y_l)$ 三元组，而更接近：

$$
(x,y_1,y_2,\text{preference},\text{confidence},\text{criteria},\text{provenance})
$$

这些附加信息有助于后续做 Sample Weighting、质量审计和重新标注。

---

## Online Preference Data Flywheel 是如何运转的？

离线偏好数据使用固定 Dataset，但 Policy 在训练后会不断变化。旧数据主要描述旧 Policy 的错误模式，因此随着模型能力提升，会逐渐出现 **Distribution Shift / Data Staleness**。

在线或迭代式 Preference Data Collection 则让数据跟随当前 Policy 更新：

> **Current Policy → 生成新 Candidate → Hard / Uncertain / Diverse Pair Mining → Human / AI / Verifier 标注 → 更新 Preference Dataset → 训练 RM / Policy → New Policy**

可写成：

$$
\pi_t
\rightarrow
D_t
\rightarrow
\text{Acquire / Label}
\rightarrow
\text{Update}
\rightarrow
\pi_{t+1}
$$

这种数据飞轮有几个重要作用：

- Candidate 更贴近当前 Policy 真正会生成的分布；
- Hard Negative 会随着模型能力增强自动变难；
- 新的 Failure Mode 可以快速进入训练数据；
- Annotation Budget 可以集中到当前模型最需要反馈的区域，而不是重复标注已经学会的 Easy Pair。

Online Preference Optimisation 的工作明确研究了让两个 Candidate 从 Online Policy 生成并由 Preference Model 标注，再持续更新 Policy 的训练方式。参考：[Human Alignment of Large Language Models through Online Preference Optimisation](https://arxiv.org/abs/2403.08635)。

不过 Online 不等于“所有新数据都直接加入训练”。持续迭代还需要 Dedup、质量过滤、Difficulty / Domain Balancing，以及保留一定历史数据防止模型只追逐最新 Failure Mode。

相关概念：[[LLM/后训练/偏好学习/偏好学习#为什么现代后训练越来越重视在线偏好学习？|为什么现代后训练越来越重视在线偏好学习？]]。

---

相关主题：[[LLM/后训练/偏好学习/偏好学习|偏好学习]] · [[LLM/后训练/偏好学习/Reward Model（RM）/Reward Model（RM）|Reward Model（RM）]] · [[LLM/后训练/偏好学习/DPO Family（直接偏好优化）/DPO Family（直接偏好优化）|DPO Family（直接偏好优化）]]