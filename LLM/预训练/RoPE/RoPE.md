# RoPE

所属主题：[[预训练]]

围绕旋转位置编码（Rotary Position Embedding, RoPE）的基本原理、长上下文扩展和频谱设计整理 Q&A。

## 问题目录

- [[RoPE#RoPE 是什么？为什么要设计一个不同于普通 PE 的 RoPE？|RoPE 是什么？为什么要设计一个不同于普通 PE 的 RoPE？]]
- [[RoPE#RoPE 的现代演进脉络是什么样的？|RoPE 的现代演进脉络是什么样的？]]
- [[RoPE#RoPE 为什么要对不同位置的 Token 使用相同的频谱？|RoPE 为什么要对不同位置的 Token 使用相同的频谱？]]

---

## RoPE 是什么？为什么要设计一个不同于普通 PE 的 RoPE？

Transformer 的 Attention 本身不知道 Token 的先后位置，因此需要额外注入位置信息。传统绝对位置编码通常将位置向量直接加到 Token 表示上；**RoPE 则把位置信息编码为对 Query 和 Key 的旋转，使 Attention 的点积天然显式依赖 Token 的相对距离。**

设 Attention Head 维度为 $d$，RoPE 将维度两两组成二维平面，并为第 $j$ 个二维子空间定义角频率：

$$\theta_j=B^{-2j/d}$$

位置 $m$ 的 Query 与位置 $n$ 的 Key 分别旋转：

$$\tilde q_m^{(j)}=R(m\theta_j)q_m^{(j)},\qquad
\tilde k_n^{(j)}=R(n\theta_j)k_n^{(j)}$$

其中：

$$R(\phi)=
\begin{bmatrix}
\cos\phi & -\sin\phi\\
\sin\phi & \cos\phi
\end{bmatrix}$$

由于旋转矩阵满足：

$$R(m\theta_j)^TR(n\theta_j)=R((n-m)\theta_j)$$

因此 Attention 点积变为：

$$\tilde q_m^T\tilde k_n
=q_m^TR((n-m)\theta)k_n$$

绝对位置 $m,n$ 在两者交互时转化成了相对位置 $n-m$。所以 RoPE 的核心价值不是“能够表示位置”本身，而是 **用一种与 Attention 点积结构兼容的方式，把绝对位置编码转化成显式的相对位置关系**。

RoPE 同时使用一组从高频到低频的 $\theta_j$。高频对较小的位置变化更敏感，低频变化更慢、覆盖更长的位置尺度；多个频率共同形成多尺度的位置表示。

> **普通 PE 主要把“我在什么位置”加入 Token 表示；RoPE 则进一步让 Q/K 的匹配天然感知“两个 Token 相距多远”。**

参考：[RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)

---

## RoPE 的现代演进脉络是什么样的？

RoPE 的后续演进主要围绕一个问题：**模型超过训练时的 Context Length 后，会遇到训练阶段没有见过的旋转相位，即 positional OOD；怎样在保留局部位置分辨率的同时把频谱扩展到更长距离？**

原始 RoPE 使用：

$$\theta_j=B^{-2j/d},\qquad \phi_{m,j}=m\theta_j$$

后续方法主要修改位置 $m$、频率 $\theta_j$，或决定哪些层使用 RoPE。

| 方法 | 主要数学变化 | 核心思想 |
|---|---|---|
| **Position Interpolation（PI）** | $m'=m/s$，等价于 $\theta'_j=\theta_j/s$ | 所有频率统一减速，把长位置压回训练过的位置范围 |
| **NTK-aware Scaling** | $B'=B\,s^{d/(d-2)}$，因此 $\theta'_j=\theta_j s^{-2j/(d-2)}$ | 高频少缩放、低频多缩放，避免 PI 同时损伤所有局部分辨率 |
| **Dynamic NTK** | $s\rightarrow s(L_{current})$ | 只有实际序列超过原训练长度时才逐渐增强 Scaling |
| **YaRN** | $\theta'_j=(1-\gamma_j)\theta_j/s+\gamma_j\theta_j$ | 按频段处理：低频完整缩放、高频保持、中频平滑过渡，并补偿 Attention 尺度变化 |
| **Llama 3.1 Scaled RoPE** | 根据 wavelength 对 $\theta_j$ 做分段缩放 | 将 Frequency-aware Scaling 工程化：短波长保持、长波长缩放、中间平滑过渡 |
| **LongRoPE** | $\theta'_j=\theta_j/s_j$ | 不再规定统一解析函数，而是为不同 RoPE 维度搜索独立 Scaling Factor，并考虑不同 Token 区域的非均匀性 |
| **LongRoPE2** | 仍使用 $\theta'_j=\theta_j/s_j$，但结合 practical critical dimension 搜索 | 注意到部分低频维度在原训练窗口内可能从未充分旋转，依据模型真实长距离能力重新搜索频谱 |
| **iRoPE** | 部分 Attention Layer 使用 RoPE，部分 Layer 不使用显式 PE | 从“怎样缩放所有 RoPE”进一步发展为“哪些层需要位置旋转、哪些层可以弱化显式位置约束” |

其中最关键的思想演进可以压缩为：

$$\text{统一缩放}
\rightarrow\text{频率相关缩放}
\rightarrow\text{分频段缩放}
\rightarrow\text{逐维搜索}
\rightarrow\text{依据实际学习状态搜索}
\rightarrow\text{部分层不使用 RoPE}$$

### 为什么会从 PI 继续发展到频率相关 Scaling？

PI 对所有维度统一使用：

$$\theta'_j=\frac{\theta_j}{s}$$

虽然避免了长位置直接进入未见过的相位区域，但也把高频维度的局部位置变化一起压缩。例如相邻 Token 原本的相位差为 $\theta_j$，缩放后只剩 $\theta_j/s$。

NTK-aware、YaRN 与 Llama 3.1 一类方法因此开始区别处理不同频率：**高频主要负责精细局部位置，不宜过度压缩；低频主要负责更长尺度的位置关系，更需要扩展。**

LongRoPE / LongRoPE2 又进一步放弃“所有维度必须遵循同一个人工设计函数”的假设，转向为不同维度搜索更合适的缩放比例。

> **RoPE Scaling 的演进，本质上是在重新安排同一套多尺度位置频谱：既要保持高频的局部分辨率，又要让低频覆盖更长距离，同时减少模型进入未训练位置分布的程度。**

参考：[Position Interpolation](https://arxiv.org/abs/2306.15595) · [YaRN](https://arxiv.org/abs/2309.00071) · [LongRoPE](https://arxiv.org/abs/2402.13753) · [LongRoPE2](https://arxiv.org/abs/2502.20082) · [Llama 4 iRoPE](https://ai.meta.com/blog/llama-4-multimodal-intelligence/)

---

## RoPE 为什么要对不同位置的 Token 使用相同的频谱？

RoPE 中的**高频与低频由维度 $j$ 对应的 $\theta_j$ 决定，而不是由 Token 位置 $m$ 决定**。每一个位置都会使用同一组频率：

$$p(m)=\left[e^{im\theta_0},e^{im\theta_1},\ldots,e^{im\theta_{d/2-1}}\right]$$

不同位置的区别，是同一组频率积累出了不同的相位 $m\theta_j$。因此每个 Token 都同时拥有高频、中频和低频位置分量：高频区分局部细小位置变化，低频提供更长尺度的位置变化。

对所有位置使用相同频谱最重要的原因，是让所有 Token 位于**同一个位置坐标系**中。对于同一个频率 $\theta_j$：

$$R(m\theta_j)^TR(n\theta_j)=R((n-m)\theta_j)$$

所以 Attention 只需要关心相对距离 $n-m$。

如果不同位置使用不同频率 $\theta_j(m)$，则得到：

$$R(m\theta_j(m))^TR(n\theta_j(n))
=R\left(n\theta_j(n)-m\theta_j(m)\right)$$

它一般无法化成只依赖 $n-m$ 的函数。这样相同距离在序列不同区域会具有不同的位置表示，RoPE 原本的相对位置一致性就会被破坏。

因此：

- **频谱相同不等于位置编码相同**：不同位置仍通过不同 phase 区分；
- **每个位置都采样完整频谱**：同一个 Token 同时具有局部和长程位置尺度；
- **共享频谱保证可比较性**：相同相对距离在不同绝对位置具有一致的旋转关系。

> **RoPE 让不同位置共享同一组“尺子”，位置 $m$ 决定每把尺子走到了什么相位；如果每个位置都换一套尺子，就很难再稳定地用相位差表示相对距离。**

参考：[RoFormer](https://arxiv.org/abs/2104.09864)

---

相关主题：[[预训练]]