# Reward Model（RM）

[[LLM/后训练/偏好学习/偏好学习|返回上级：偏好学习]] · [[main|返回知识主干]]

围绕现代 Reward Model 的分类维度、Process Reward Model、多目标与生成式评价、Verifier 以及 Online / Policy-aware Reward Modeling 整理 Q&A。

## 问题目录

- [[Reward Model（RM）#Reward Model 现在的主要分类维度是什么样的？|Reward Model 现在的主要分类维度是什么样的？]]
- [[Reward Model（RM）#PRM 是什么？|PRM 是什么？]]
- [[Reward Model（RM）#PRM 面临着什么困难？|PRM 面临着什么困难？]]
- [[Reward Model（RM）#如何自动生成 PRM 监督信号？|如何自动生成 PRM 监督信号？]]
- [[Reward Model（RM）#多目标 RM 通常考虑哪些目标？|多目标 RM 通常考虑哪些目标？]]
- [[Reward Model（RM）#多目标 RM 如何提供奖励信号，提供什么样的奖励信号？|多目标 RM 如何提供奖励信号，提供什么样的奖励信号？]]
- [[Reward Model（RM）#生成式 RM 是什么？|生成式 RM 是什么？]]
- [[Reward Model（RM）#什么是条件式评分 RM？|什么是条件式评分 RM？]]
- [[Reward Model（RM）#为什么还要有 Verifier / Rule-based Reward，它是如何减少 Reward Hacking 的？|为什么还要有 Verifier / Rule-based Reward，它是如何减少 Reward Hacking 的？]]
- [[Reward Model（RM）#Online / Policy-aware RM 是什么？|Online / Policy-aware RM 是什么？]]
- [[Reward Model（RM）#Online / Policy-aware RM 如何在后训练中与 LLM 共同迭代？|Online / Policy-aware RM 如何在后训练中与 LLM 共同迭代？]]

---

## Reward Model 现在的主要分类维度是什么样的？

现代 Reward Model 不适合按 ORM、PRM、Generative RM、Multi-objective RM 直接排成一组互斥类别，因为这些概念描述的是**不同维度**，可以组合在同一个评价器中。更适合从以下几个正交维度理解：

| 分类维度 | 核心问题 | 典型形式 |
| --- | --- | --- |
| **评价粒度（Granularity）** | 在哪里给奖励？ | Outcome-level、Process / Step-level、Trajectory-level |
| **输出 / 建模形式（Output Form）** | 如何做评价？ | Scalar / Pair-wise Discriminative RM、Generative / Reasoning RM |
| **目标组织方式（Objective）** | 评价一个目标还是多个目标？ | Single-objective、Multi-objective / Multi-head、Criteria / Rubric-conditioned |
| **生命周期（Lifecycle）** | RM 是否随 Policy 分布更新？ | Offline / Static RM、Online / Policy-aware RM |

另外还要区分 **Reward Model** 与更广义的 **Reward System**。Learned RM 是通过数据学习出的评价模型；Verifier、规则、单元测试和环境反馈也能输出 Reward，但严格来说不一定属于 Reward Model。

因此一个现代 RM 完全可以同时是：**Process-level + Multi-objective + Generative + Online**。这比把 ORM、PRM、GenRM 当成同一层级的方法名更准确。Reward Model 的研究也越来越从“单一标量偏好代理”扩展到数据、建模形式、粒度和使用方式等多个维度。参考：[A Comprehensive Survey of Reward Models](https://arxiv.org/abs/2504.12328)、[A Survey on Progress in LLM Alignment from the Perspective of Reward Design](https://arxiv.org/abs/2505.02666)。

---

## PRM 是什么？

Process Reward Model（PRM）对**产生最终 Outcome 的中间过程**进行评价。与只在完整回答或最终结果上给分的 Outcome Reward Model（ORM）相比，PRM 将监督下沉到中间步骤。

如果一条完整轨迹记为 $\tau$，ORM 更接近：

$$
R = r(\tau)
$$

而 PRM 更接近：

$$
r_t = r(s_t,a_t)
$$

或者在语言模型推理中写成：

$$
r_t = r_\phi(x, y_{\le t})
$$

其中 $y_{\le t}$ 是截至第 $t$ 个中间步骤的轨迹前缀。PRM 的“Process”不是任意长度的 Token Chunk，而应该对应**有语义的中间决策或状态转移**。

在不同任务中，Process Unit 可以不同：

- **Reasoning / CoT**：一个数学推导步骤、一个有明确语义的 reasoning step。OpenAI 的 PRM800K 就对数学解题中的每个中间步骤做正确性监督。参考：[Let's Verify Step by Step](https://arxiv.org/abs/2305.20050)、[OpenAI Process Supervision](https://openai.com/index/improving-mathematical-reasoning-with-process-supervision/)。
- **Code**：可以是代码行、语句块、函数、一次 Patch 或一次“生成—测试—修正”的步骤。已有工作使用 line-level feedback，也有后续工作把 Function 作为 Step。参考：[Process Supervision-Guided Policy Optimization for Code Generation](https://arxiv.org/abs/2410.17621)、[DreamPRM-Code](https://arxiv.org/abs/2512.15000)。
- **Agent 轨迹**：Process 可以是一次 Action、Tool Call，或者一次 $State \rightarrow Action \rightarrow Observation$ 转移。参考：[Process Reward Models for LLM Agents](https://arxiv.org/abs/2502.10325)。

因此，PRM 可以理解为**更细粒度的 Reward Model**，但关键不只是“把 ORM 切碎”，而是要让每个监督单位对应真正有意义的中间决策。

PRM 与 Pair-wise Preference 也不是同一维度：PRM 说的是**监督粒度**，Pair-wise 说的是**监督形式**。一个 PRM 可以使用 Step-level Correct / Incorrect，也可以使用同一中间状态下的 Step A $\succ$ Step B。

---

## PRM 面临着什么困难？

PRM 的困难首先不是模型结构，而是**什么算一个可评价的过程，以及怎样得到可靠的过程标签**。

1. **Process Unit 难定义**：数学 CoT 的推导步骤比较自然，但 Code、开放式 Reasoning 和 Agent 中，一个“Step”可以是 Token、语句、函数、工具调用或更长的子轨迹。粒度过细缺少语义，过粗又退化成 ORM。Code PRM 的研究也指出，代码中缺少天然、稳定的步骤划分。参考：[DreamPRM-Code](https://arxiv.org/abs/2512.15000)。
2. **人工标注昂贵**：逐步判断一条长轨迹的每一步，成本远高于只判断最终答案。PRM800K 依赖大规模 Step-level 人工反馈；后续自动化工作正是为了减少这一成本。参考：[Let's Verify Step by Step](https://arxiv.org/abs/2305.20050)。
3. **局部正确不等于全局好**：某一步逻辑上没有错误，但可能是无效绕路；Agent 的一次搜索最终没被使用，也不一定是不合理探索。因此 Step Reward 与最终 Outcome 之间存在 Credit Assignment 和 Reward Shaping 问题。
4. **自动标签存在噪声**：如果用后续 Rollout 成败反推当前 Step 好坏，错误可能来自后面的决策，而不是当前 Step；Monte Carlo 样本不足时估计也会有较大方差。自动 Process Supervision 研究通常要处理这类标签噪声和搜索成本。参考：[OmegaPRM](https://arxiv.org/abs/2406.06592)。
5. **分布会随 Policy 改变**：PRM 在旧模型轨迹上学到的判断，不一定适用于更强 Policy 产生的新型 reasoning / tool-use 轨迹，因此也存在 Distribution Shift。
6. **Process Reward 仍可能被 Hack**：模型可能学会生成“看起来正确”的中间步骤、格式或解释来骗过 PRM，而没有真正完成任务。特别是在开放式过程监督中，评价器仍然只是目标的代理。

OpenAI 在最初的 Process Supervision 工作中也明确指出，其数学结果是否能够广泛泛化到其他领域仍是开放问题。参考：[Improving Mathematical Reasoning with Process Supervision](https://openai.com/index/improving-mathematical-reasoning-with-process-supervision/)。

---

## 如何自动生成 PRM 监督信号？

自动 PRM 的核心思想是：**不让人逐步标注，而是利用最终可验证 Outcome、Rollout、搜索或更强 Judge，把 Outcome 信息反推到中间状态。** 常见方法包括：

### Monte Carlo Rollout

对轨迹前缀 $s_t$ 或 $y_{\le t}$ 继续采样 $K$ 条后续轨迹，用最终成功率近似当前状态的价值：

$$
\hat{V}(s_t)=\frac{1}{K}\sum_{k=1}^{K}\mathbb{I}(\text{rollout}_k\ \text{success})
$$

如果从某一步出发，大多数后续 Rollout 都能成功，该步骤就获得较高的 Soft Process Score；反之则较低。Math-Shepherd 使用自动构造的 Process-wise Supervision 来训练数学 PRM。参考：[Math-Shepherd](https://arxiv.org/abs/2312.08935)。

### 搜索与错误定位

可以使用 Tree Search / MCTS 扩展某个中间状态，观察不同分支最终是否成功，再据此定位错误步骤。OmegaPRM 使用 Divide-and-Conquer 风格的 MCTS 和错误定位来高效构造大规模 Process 标签。参考：[OmegaPRM](https://arxiv.org/abs/2406.06592)。

### Verifier / Environment 反推

在数学、代码和 Agent 环境中，可以利用最终答案、单元测试、编译器、环境任务成败等客观信号监督中间过程。例如 Code PRM 可以根据后续测试结果形成细粒度代码反馈；AgentPRM 则利用环境 Rollout 计算中间 Reward Target。参考：[Process Supervision-Guided Policy Optimization for Code Generation](https://arxiv.org/abs/2410.17621)、[Process Reward Models for LLM Agents](https://arxiv.org/abs/2502.10325)。

### Teacher / Judge 合成标注

也可以让更强模型对每个 Step 生成 Correct / Incorrect、Critique 或评分，再用这些合成标签训练较小 PRM。这种方式扩展性强，但会继承 Teacher / Judge 的偏差，因此通常需要 Verifier、人工抽检或独立 Eval 作为锚点。

> 自动 PRM 的本质通常是把昂贵的“逐步人工监督”替换成 **Outcome-derived、Search-derived、Verifier-derived 或 Judge-derived Process Signal**。

---

## 多目标 RM 通常考虑哪些目标？

传统 Scalar RM 把“好回答”压缩成一个 Reward，但真实 Assistant 往往同时需要满足多个目标。常见维度包括：

- **Correctness / Factuality**：事实、推理或任务结果是否正确。
- **Instruction Following / Relevance**：是否遵循用户要求、回答当前任务。
- **Helpfulness**：信息是否足够有用、完整。
- **Honesty / Uncertainty**：是否避免无依据断言，并在不确定时正确表达不确定性。
- **Safety / Harmlessness**：是否满足安全、权限和合规边界。
- **Style / Verbosity / Conciseness**：表达风格、长度和可读性是否合适。
- **Tool / Action Correctness**：在 Agent 场景中，工具选择、参数与执行行为是否正确。
- **Efficiency**：对于 Agent 或长轨迹任务，还可以显式考虑步骤数、成本、延迟等目标。

具体目标并不是固定清单，而应由任务决定。ArmoRM 就使用多维绝对评分来建模可解释目标，并举出了 Honesty、Verbosity、Safety 等维度。参考：[Interpretable Preferences via Multi-Objective Reward Modeling and Mixture-of-Experts](https://arxiv.org/abs/2406.12845)。

---

## 多目标 RM 如何提供奖励信号，提供什么样的奖励信号？

多目标 RM 不一定直接输出一个总分，而可以先输出一个 Reward Vector：

$$
\mathbf{r}(x,y)=[r_1,r_2,\ldots,r_K]
$$

其中每一维对应 Correctness、Safety、Helpfulness 等目标。之后再根据训练目的把多维信号转成 Policy 可以使用的 Reward。

常见方式包括：

1. **加权聚合**：

$$
R(x,y)=\sum_{k=1}^{K}w_k r_k(x,y)
$$

不同 $w_k$ 表示不同目标的重要性。

2. **Context-dependent Gating**：根据 Prompt 或任务动态决定各维 Reward 的权重。例如安全敏感请求提高 Safety 权重，代码任务提高 Correctness / Executability 权重。ArmoRM 使用 Gating Network 根据 Context 选择适合的 Reward Objectives。参考：[ArmoRM](https://arxiv.org/abs/2406.12845)。

3. **约束式 Reward**：某些目标不适合被其他维度“补偿”，例如 Safety 低于阈值时直接拒绝或给强惩罚，而不是允许 Helpfulness 高分把它抵消。

4. **保留向量进行多目标优化**：在一些系统中不急着压成单一 Scalar，而是在 Policy Optimization 或 Decoding 阶段显式控制不同目标之间的 Trade-off。多目标 Alignment 研究也探索了按不同目标权重动态组合策略。参考：[Decoding-Time Language Model Alignment with Multiple Objectives](https://arxiv.org/abs/2406.18853)。

因此，多目标 RM 可以提供**每维独立 Reward、聚合后的 Scalar Reward、约束信号或动态条件化 Reward**。关键是不要把复杂的人类目标过早压缩成一个不可解释的固定分数。

---

## 生成式 RM 是什么？

传统 Discriminative RM 通常在一次 Forward Pass 后直接输出 Scalar 或 Preference Score。生成式 Reward Model（Generative RM / Reasoning RM）则让评价模型**先生成自然语言 Critique、Reasoning、Rubric 检查或 Verification，再给出 Verdict / Score / Reward**。

例如：

> Response → 检查事实 → 检查推理步骤 → 指出错误 → 给出最终评分

Critique-out-Loud Reward Model 就先生成 Critique，再基于 Critique 预测 Scalar Reward；这让评价不再全部隐式压在一次前向计算中。参考：[Critique-out-Loud Reward Models](https://arxiv.org/abs/2408.11791)。

生成式 RM 可能更强，主要因为：

- **显式 Reasoning**：复杂评价可以被分解成多个检查步骤，而不是要求 Scalar Head 一次完成所有判断。
- **可利用更多 Inference-time Compute**：可以生成更长 Verification，做 Self-consistency 或多次评价。
- **更容易结合 Rubric / Criteria**：模型可以逐项检查每个标准后再汇总。
- **反馈信息更丰富**：除了 Reward，还能输出“哪里错、为什么错”的 Critique，可进一步用于数据生成、Revision 或 Process Supervision。

ThinkPRM 进一步展示了 Generative、长 CoT 的 Step Verifier 可以在较少 Process 标签下进行逐步验证。参考：[Process Reward Models That Think](https://arxiv.org/abs/2504.16828)。

代价是推理成本更高，而且生成式评价同样可能存在 Judge Bias、错误推理和 Reward Hacking。因此“会解释”不等于“评价一定正确”。

相关对比：[[对比问题#Generative RM 和 LLM-as-a-Judge 是不是一回事？|Generative RM 和 LLM-as-a-Judge 是不是一回事？]]。

---

## 什么是条件式评分 RM？

传统 RM 常写成：

$$
r(x,y)
$$

这隐含了“所有任务共享一套固定的好坏标准”。但不同任务对好回答的定义不同，因此条件式评分 RM 会把评价标准显式作为条件输入：

$$
r(x,y,c)
$$

其中 $c$ 可以是 Criteria、Rubric、用户偏好、任务要求或安全策略。

例如同一回答在“尽量详细”和“必须在 100 字内”两种 Rubric 下，Reward 排序可能相反。条件式评分 RM 的意义是：**把‘什么叫好’从模型内部的隐式平均偏好，变成可显式指定、可切换的评价条件。**

这种条件化可以和其他维度组合：它既可以是 Scalar RM，也可以是 Generative RM；既可以评价 Outcome，也可以评价 Process。近期 Rubric-conditioned 方法进一步探索了由模型生成任务特定 Rubric，再依据 Rubric 给出细粒度评价。参考：[RUBRIC-ARROW](https://arxiv.org/abs/2605.29156)、[Rethinking Reward Supervision: Rubric-Conditioned Self-Distillation](https://arxiv.org/abs/2606.19327)。

---

## 为什么还要有 Verifier / Rule-based Reward，它是如何减少 Reward Hacking 的？

Learned RM 本质上是目标质量的**代理模型（Proxy）**。在数学、代码、结构化任务等可验证场景中，如果已经存在可靠的外部判定，就没有必要把所有评价都交给一个学习式 RM。

典型 Verifier / Rule-based Reward 包括：

- 数学最终答案或符号等价检查；
- Code Unit Test、Compiler、Static Checker；
- 格式与 Schema 校验；
- Agent 环境中的任务是否真正完成；
- 权限、预算、步骤约束等确定性规则。

这些信号与 learned preference 相比通常更接近任务真实 Outcome，因此能减少“模型只学会讨好 RM”的空间。例如代码必须真正通过隐藏测试，数学结果必须满足等价性检查，Policy 很难仅靠语言风格把 Reward 骗高。

但 **Verifier 并不能消灭 Reward Hacking**。只要 Verifier 不完整，模型仍可能利用其盲区。例如只检查表面输出、不检查真正的归纳规则，或者测试覆盖不足，都可能产生 False Positive。2026 年的研究已经展示 RLVR 模型能够系统性 Gaming 不完善的 Verifier。参考：[LLMs Gaming Verifiers: RLVR can Lead to Reward Hacking](https://arxiv.org/abs/2604.15149)。

因此更准确的说法是：

> **Verifier / Rule-based Reward 通过把奖励锚定到可执行、可验证的外部事实，减少 learned RM 的代理误差和主观偏差；但它自身也必须被设计、测试和对抗验证。**

工程上常用 Hidden Tests、多种独立 Verifier、等价性检查、Perturbation / Adversarial Test 等方式降低单一规则被钻漏洞的风险。

---

## Online / Policy-aware RM 是什么？

Offline / Static RM 通常在一批固定 Preference Data 上训练完成后保持不变，而 Policy 会持续更新：

$$
\pi_0 \rightarrow \pi_1 \rightarrow \pi_2 \rightarrow \cdots
$$

当 Policy 逐渐偏离最初的数据分布时，旧 RM 可能开始面对它从未见过的新回答、新推理风格和新型 Failure Mode，从而出现 Distribution Shift，并被 Policy 逐渐找到漏洞。

Online / Policy-aware RM 的核心是：**Reward Model 的训练数据持续来自当前或近期 Policy 的真实输出，使评价器尽量跟上 Policy 的分布变化。**

这里的 Policy-aware 并不一定意味着把 Policy 参数直接输入 RM，而更常见的是：

- 用 Current Policy 生成新的候选 Response / Trajectory；
- 优先收集 RM 不确定、容易混淆或被 Policy 利用的 Hard Cases；
- 再由 Human、AI Judge、Verifier 或其他更可靠信号重新标注；
- 周期性更新 RM。

Online Iterative RLHF 的公开工作就展示了从 Reward Modeling 到在线迭代 Policy Optimization 的完整工作流。参考：[RLHF Workflow: From Reward Modeling to Online RLHF](https://arxiv.org/abs/2405.07863)、[Human Alignment of Large Language Models through Online Preference Optimisation](https://arxiv.org/abs/2403.08635)。

---

## Online / Policy-aware RM 如何在后训练中与 LLM 共同迭代？

一个典型循环可以写成：

> **Policy$_t$ → 生成候选 / 轨迹 → 外部反馈 → 更新 RM$_{t+1}$ → 用新 RM 优化 Policy$_{t+1}$ → 再采样**

更具体地说：

1. 当前 Policy $\pi_t$ 在目标 Prompt 分布上生成多个 Response 或 Agent Trajectory。
2. 使用 Human、AI Judge、Verifier、规则或任务 Outcome 获得新的 Preference / Reward 标签，尤其关注 RM 当前容易判断错的 Hard Negative。
3. 用这些新数据刷新或继续训练 $r_{\phi_t}$，得到更贴近当前 Policy 分布的 $r_{\phi_{t+1}}$。
4. 使用新的 RM 做 PPO / GRPO 等 RL、Best-of-N、Rejection Sampling，或者生成新的 Preference Data，更新 Policy 为 $\pi_{t+1}$。
5. 对新 Policy 独立评估；如果出现新的 Failure Mode，再进入下一轮数据采集与 RM 更新。

可概括为：

$$
\pi_t
\rightarrow D_t
\rightarrow r_{\phi_{t+1}}
\rightarrow \pi_{t+1}
\rightarrow D_{t+1}
\rightarrow \cdots
$$

这里最重要的是**不能让 RM 和 Policy 形成没有外部锚点的自我确认闭环**。如果新数据全部由旧 RM 自己打标签，再用这些标签训练新 RM 与 Policy，原有 Bias 很可能被不断放大。因此 Online RM 通常需要 Human、强 Judge、Verifier、独立 Eval 或其他外部 Grounding 持续校准。

Online / Policy-aware 的价值不只是“数据更新得更快”，而是让 **Policy 与评价器共同面对当前分布上的新问题**，降低固定 RM 被不断优化到失效的风险。参考：[RLHF Workflow: From Reward Modeling to Online RLHF](https://arxiv.org/abs/2405.07863)。

---

相关主题：[[LLM/后训练/偏好学习/偏好学习|偏好学习]] · [[推理能力]] · [[Agent]]