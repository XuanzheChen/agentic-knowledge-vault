# MoE

[[预训练|返回上级：预训练]] · [[main|返回知识主干]]

围绕 Mixture of Experts 的路由、专家 specialization 与负载均衡机制整理 Q&A。

## 问题目录

- [[MoE#MoE 怎么做？|MoE 怎么做？]]
- [[MoE#Auxiliary-Loss-Free 的 Bias 是怎么帮助 specialization？|Auxiliary-Loss-Free 的 Bias 是怎么帮助 specialization？]]

---

## MoE 怎么做？

**Mixture of Experts（MoE）** 在部分网络层中设置多个 Expert，并用 **Router / Gate** 根据当前 Token 的 Hidden State 计算其与各 Expert 的匹配分数，只激活 Top-K Expert 参与计算。因此模型可以拥有很大的总参数量，同时控制每个 Token 的实际计算量。

训练中的关键问题是 **负载均衡**：若大量 Token 长期集中到少数 Expert，会导致计算负载不均，并影响 Expert 分工。传统方法通常加入 Load-Balancing Auxiliary Loss；DeepSeek-V3 则主要通过动态调整各 Expert 的路由 Bias 来控制流量：过载 Expert 的 Bias 降低，欠载 Expert 的 Bias 提高，从而在不过度干扰主语言建模目标的情况下改善负载分布。

参考：[DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437)

---

## Auxiliary-Loss-Free 的 Bias 是怎么帮助 specialization？

Expert specialization 的基础，是训练过程中不同类型 Token 与不同 Expert 之间逐渐形成稳定的 **affinity（匹配关系）**。但稀疏 Top-K Routing 会放大初始化阶段的微小随机差异：少数 Expert 如果过早获得更多 Token，就会得到更多梯度并继续吸引更多 Token，其他 Expert 则可能长期缺少训练信号，最终形成 routing collapse，而不是有意义的分工。

DeepSeek-V3 的 **Auxiliary-Loss-Free Load Balancing** 会根据整个 Batch 中各 Expert 实际收到的 Token 数动态调整路由 Bias：过载 Expert 降低 Bias，欠载 Expert 提高 Bias。Bias 只影响 Top-K 的选择边界，而实际 Expert 输出的 gating weight 仍由原始 affinity 决定。这样可以抑制少数 Expert 过早垄断流量，让更多 Expert 持续获得训练机会，同时尽量保留模型根据 Token 特征形成不同路由偏好的空间。

这里关键是它主要采用 **Batch-wise Balance**，而不是要求每条 Sequence 内都平均使用所有 Expert。一个代码序列仍可以集中路由到一组 Expert，数学或其他领域也可以集中到另一组 Expert；只要在更大的统计范围内没有少数 Expert 长期吞掉绝大多数流量即可。因此，负载均衡提供的是形成 specialization 的稳定训练条件，而具体分工仍由数据和语言建模目标驱动。

训练条件也会直接影响 specialization：

- **数据多样性**提供足够丰富、可区分的模式，使不同 Expert 有形成分工的基础；Expert 的分工未必对应人类可命名的领域，也可能对应语言、句法或更隐含的表示模式。
- **Data Mixture** 决定各种模式出现的比例。过度偏斜的 mixture 可能使某类 Token 长期主导路由，因此需要合理控制不同领域和语言的数据分布。
- **足够大的路由统计范围**使负载估计更接近整体数据分布。若只依据很小且恰好属于单一领域的 Batch 做均衡，可能把合理的领域 specialization 误判为过载；较大的 Global Batch、Micro-batch 或跨设备统计能降低这种噪声。

> **MoE specialization 来自异质数据与 Token–Expert affinity 的长期学习；Auxiliary-Loss-Free Bias 的作用是防止早期垄断和 Expert 饥饿，让这种分工能够稳定形成，而不是把所有 Expert 强行训练成相同能力。**

参考：[DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437)

---

相关主题：[[LLM]] · [[中训练]] · [[后训练]]
