# DHPO

[[LLM/后训练/RL-based Post-training/RL-based Post-training|返回上级：RL-based Post-training]] · [[main|返回知识主干]]

围绕 Dynamic Hybrid Policy Optimization（DHPO）如何融合 GRPO 的 Token-level Importance Ratio 与 GSPO 的 Sequence-level Importance Ratio，以及其动态混合与 Branch-specific Clipping 整理 Q&A。

## 问题目录

- [[DHPO#DHPO 是什么，它为什么要混合 GRPO 与 GSPO？|DHPO 是什么，它为什么要混合 GRPO 与 GSPO？]]
- [[DHPO#DHPO 如何混合 Token-level 与 Sequence-level Importance Ratio？|DHPO 如何混合 Token-level 与 Sequence-level Importance Ratio？]]
- [[DHPO#DHPO 的 Averaged Mixing 与 Entropy-guided Mixing 有什么区别？|DHPO 的 Averaged Mixing 与 Entropy-guided Mixing 有什么区别？]]
- [[DHPO#为什么 Entropy 可以用来动态决定更相信 Token 还是 Sequence？|为什么 Entropy 可以用来动态决定更相信 Token 还是 Sequence？]]
- [[DHPO#为什么 DHPO 需要 Branch-specific Clipping？|为什么 DHPO 需要 Branch-specific Clipping？]]
- [[DHPO#DHPO 与 GSPO-token 的区别是什么？|DHPO 与 GSPO-token 的区别是什么？]]
- [[DHPO#如何用 Advantage Granularity × Importance Correction Granularity 统一理解 GRPO、GSPO、GSPO-token 与 DHPO？|如何用 Advantage Granularity × Importance Correction Granularity 统一理解 GRPO、GSPO、GSPO-token 与 DHPO？]]
- [[DHPO#应该如何理解 DHPO 当前的成熟度？|应该如何理解 DHPO 当前的成熟度？]]

---

## DHPO 是什么，它为什么要混合 GRPO 与 GSPO？

DHPO（Dynamic Hybrid Policy Optimization）是 2026 年提出的一种 RLVR Policy Optimization 方法，目标是在同一个 surrogate objective 中融合 GRPO 与 GSPO 的互补优势。参考：[Orchestrating Tokens and Sequences: Dynamic Hybrid Policy Optimization for RLVR](https://arxiv.org/abs/2601.05607)。

GRPO 使用 Token-level Importance Ratio：

- 局部 Policy Shift 信息更细；
- 但方差高、容易受单 Token likelihood noise 影响。

GSPO 使用 Sequence-level Importance Ratio：

- 与 Sequence-level Reward 更一致；
- 训练更稳定；
- 但会牺牲局部 Token-level Policy Shift 信息。

DHPO 因此不固定选择其中一个粒度，而是尝试在：

$$
\boxed{
\text{Fine-grained Token Information}
\leftrightarrow
\text{Sequence-level Stability}
}
$$

之间进行混合。

---

## DHPO 如何混合 Token-level 与 Sequence-level Importance Ratio？

设 GRPO 风格的 Token-level Ratio 为：

$$
r_{i,t}
$$

GSPO 风格的 Sequence-level Correction 为：

$$
s_i
$$

DHPO 构造混合 Importance Weight：

$$
\boxed{
m_{i,t}
=
w_{i,t}r_{i,t}
+
(1-w_{i,t})s_i
}
$$

其中：

$$
w_{i,t}\in[0,1]
$$

因此：

- 当 $w_{i,t}=1$ 时，更接近 GRPO；
- 当 $w_{i,t}=0$ 时，更接近 GSPO；
- 当 $0<w_{i,t}<1$ 时，在 Token 与 Sequence 两种粒度之间插值。

DHPO 主要修改的是 **Importance Correction 的粒度**，而不是像 GSPO-token 那样主要修改 Advantage Granularity。参考：[DHPO](https://arxiv.org/abs/2601.05607)。

---

## DHPO 的 Averaged Mixing 与 Entropy-guided Mixing 有什么区别？

DHPO 讨论两种主要混合方式。

### Averaged Mixing

最简单的方式令：

$$
w_{i,t}=0.5
$$

于是：

$$
m_{i,t}
=
\frac{1}{2}r_{i,t}
+
\frac{1}{2}s_i
$$

这种方式不额外判断当前位置应该更相信 Token 还是 Sequence，而是固定融合两种信息。

### Entropy-guided Mixing

另一种方式根据当前 Token 的 Policy Entropy 动态生成 $w_{i,t}$。

高 Entropy 表示模型对当前位置较不确定，混合权重更偏向 Token-level Ratio；低 Entropy 表示模型更确定，权重则更多偏向 Sequence-level Ratio。

因此可以把两种方式理解为：

> **Averaged Mixing：固定折中。**

> **Entropy-guided Mixing：根据当前位置的不确定性动态折中。**

参考：[DHPO](https://arxiv.org/abs/2601.05607)。

---

## 为什么 Entropy 可以用来动态决定更相信 Token 还是 Sequence？

Token Entropy：

$$
H_{i,t}
=
-
\sum_{v}
\pi_\theta(v\mid s_t)
\log\pi_\theta(v\mid s_t)
$$

反映当前 Policy 在这一位置的局部不确定性。

当 Entropy 较高时，模型仍处于较强探索状态，局部 Token-level Policy Shift 包含较多有价值的信息，因此 DHPO 更偏向使用 $r_{i,t}$。

当 Entropy 较低时，模型对局部选择已经较确定，继续依赖高方差 Token Ratio 的收益降低，此时更偏向 Sequence-level $s_i$ 可以获得更稳定的更新。

可以将其直觉概括为：

$$
\boxed{
\text{高不确定性}
\rightarrow
\text{更多 Token-level 信息}
}
$$

$$
\boxed{
\text{低不确定性}
\rightarrow
\text{更多 Sequence-level 稳定性}
}
$$

参考：[DHPO](https://arxiv.org/abs/2601.05607)。

---

## 为什么 DHPO 需要 Branch-specific Clipping？

Token-level Ratio 与 Sequence-level Ratio 的数值分布和方差并不相同，因此不能简单地先混合，再使用完全相同的 Trust Region。

DHPO 先分别对两条分支进行 Clipping：

$$
\tilde r_{i,t}
=
\operatorname{clip}
\left(
r_{i,t},
1-\epsilon_{token}^{-},
1+\epsilon_{token}^{+}
\right)
$$

以及：

$$
\tilde s_i
=
\operatorname{clip}
\left(
s_i,
1-\epsilon_{seq}^{-},
1+\epsilon_{seq}^{+}
\right)
$$

然后再混合：

$$
\boxed{
\tilde m_{i,t}
=
w_{i,t}\tilde r_{i,t}
+
(1-w_{i,t})\tilde s_i
}
$$

这样可以避免 Token branch 或 Sequence branch 的异常 Ratio 在混合前主导整体更新。

其核心认识是：

> **Token-level Trust Region 与 Sequence-level Trust Region 约束的是不同随机变量，因此应该分别控制。**

参考：[DHPO](https://arxiv.org/abs/2601.05607)。

---

## DHPO 与 GSPO-token 的区别是什么？

两者都试图避免“只选 Token 或只选 Sequence”的过度简化，但修改的是两个不同轴。

GSPO-token 主要解决：

> **Advantage / Credit Assignment 应该细到什么粒度？**

它保留 Sequence-level Importance Correction，但允许：

$$
\hat A_{i,t}
$$

真正随 Token 变化。

DHPO 主要解决：

> **Importance Correction 应该使用 Token、Sequence，还是两者混合？**

它构造：

$$
m_{i,t}
=
w_{i,t}r_{i,t}
+
(1-w_{i,t})s_i
$$

但其主要设计仍使用 Sequence-level Group Advantage。

因此：

| 方法 | Importance Correction | Advantage |
| --- | --- | --- |
| **GRPO** | Token-level | Sequence / Group |
| **GSPO** | Sequence-level | Sequence / Group |
| **GSPO-token** | Sequence-level | Token-level |
| **DHPO** | Token + Sequence Hybrid | Sequence / Group |

理论上，Hybrid Importance Correction 与 Token-level Advantage 仍可以进一步组合，但这不是当前 DHPO 的核心定义。

---

## 如何用 Advantage Granularity × Importance Correction Granularity 统一理解 GRPO、GSPO、GSPO-token 与 DHPO？

现代 RLVR 可以至少沿两个相对独立的轴理解。

### 轴一：Advantage / Credit Assignment Granularity

回答：

> **Reward 最终应该细分到整条 Sequence，还是不同 Token / Step？**

从：

$$
\hat A_i
$$

到：

$$
\hat A_{i,t}
$$

GSPO-token 主要在这一轴上继续推进。

### 轴二：Importance Correction Granularity

回答：

> **新旧 Policy 的变化应该在 Token、Sequence，还是混合粒度上被约束？**

包括：

- Token-level Ratio：GRPO；
- Sequence-level Ratio：GSPO；
- Hybrid Ratio：DHPO。

因此可以形成：

| Advantage | Token Ratio | Hybrid Ratio | Sequence Ratio |
| --- | --- | --- | --- |
| **Sequence / Group** | GRPO | DHPO | GSPO |
| **Token / Step** | 可继续研究 | 可继续研究 | GSPO-token |

这个二维视角比把算法理解为简单的线性“升级链”更稳定，因为很多现代方法实际上只是在 RL Training Recipe 中替换一个相对独立的组件。

---

## 应该如何理解 DHPO 当前的成熟度？

截至 2026 年，DHPO 是一项较新的研究工作。论文在 Qwen3 Dense 与 MoE 模型及多个数学 Reasoning Benchmark 上报告了相对 GRPO / GSPO 的提升，同时提出 Averaged Mixing、Entropy-guided Mixing 与 Branch-specific Clipping。参考：[DHPO](https://arxiv.org/abs/2601.05607)。

但它目前更适合被看作：

> **有实验支持的现代研究方向，而不是已经长期验证的标准训练 Recipe。**

因此在知识结构中，应重点保留它提出的“Token × Sequence Hybrid Importance Correction”思想，而不要把当前具体 Mixing Rule 视为已经定型的最终答案。

---

相关主题：[[LLM/后训练/RL-based Post-training/RL-based Post-training|RL-based Post-training]] · [[LLM/后训练/RL-based Post-training/GRPO/GRPO|GRPO]] · [[LLM/后训练/RL-based Post-training/GSPO/GSPO|GSPO]] · [[LLM/后训练/RL-based Post-training/DAPO/DAPO|DAPO]]
