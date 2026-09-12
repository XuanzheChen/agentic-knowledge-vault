# LLM

[[main|返回知识主干]] · [[部署]] · [[对比问题]]

围绕大语言模型的基础机制与阅读疑问整理 Q&A。这里重点记录模型内部的表示、训练与推理机制；与 Agent Runtime、RAG 检索或部署服务相关的问题，通过链接延伸到对应主题。

## 子树

| 子树       | 内容                              |
| -------- | ------------------------------- |
| [[预训练]]  | 大规模通用数据上的基础能力、架构与训练机制           |
| [[推理能力]] | 基础推理能力、CoT 表现形式，以及预训练与后训练中的推理塑造 |
| [[中训练]]  | 继续训练中的定向能力强化                    |
| [[后训练]]  | SFT、偏好优化、强化学习、自训练与蒸馏等行为塑造       |
| [[部署]]   | 模型推理服务的资源、性能、可靠性与成本             |

## 问题目录

- [[LLM#KV Cache 是什么，为什么能加速逐 Token 生成？|KV Cache 是什么，为什么能加速逐 Token 生成？]]
- [[LLM#LLM 的上下文窗口大小由什么决定？计算资源足够时输入 Sequence 可以无限长吗？|LLM 的上下文窗口大小由什么决定？计算资源足够时输入 Sequence 可以无限长吗？]]
- [[LLM#标准 RNN 为什么存在长期依赖问题？|标准 RNN 为什么存在长期依赖问题？]]
- [[LLM#RNN 参数更新明明计算的是 Loss 对参数 θ 的偏导，为什么仍会出现梯度消失或爆炸？|RNN 参数更新明明计算的是 Loss 对参数 θ 的偏导，为什么仍会出现梯度消失或爆炸？]]
- [[LLM#文本中的词或 Token 是怎样变成 Transformer 输入向量的？|文本中的词或 Token 是怎样变成 Transformer 输入向量的？]]
- [[LLM#Q、K、V 到底是什么，Multi-Head Attention 中每个 Head 的 QKV 来自哪里？|Q、K、V 到底是什么，Multi-Head Attention 中每个 Head 的 QKV 来自哪里？]]
- [[LLM#为什么生成式 LLM 常强调 Decoder-only，Encoder 又用在哪里？|为什么生成式 LLM 常强调 Decoder-only，Encoder 又用在哪里？]]

---

## KV Cache 是什么，为什么能加速逐 Token 生成？

### 参考回答（已本地化）

**KV Cache 是在 Transformer 自回归推理过程中，将历史 Token 在 Attention 中已经产生的 Key（K）和 Value（V）张量缓存起来。**

自回归生成第 `t` 个 Token 时，当前 Token 需要关注此前所有 Token。如果每生成一步都重新计算整段历史的 K/V，就会重复做大量相同计算。使用 KV Cache 后，历史位置的 K/V 直接复用，只计算新增 Token 对应的表示，再与缓存中的历史 K/V 做 Attention，因此显著降低逐 Token 解码的重复计算。

需要注意，KV Cache 主要减少的是**同一次生成序列内部**的重复计算；它并不意味着下一次独立 API 请求一定能够复用上一次请求的缓存。

延伸阅读：[[部署#KV Cache 为什么会影响显存、并发和长上下文服务？|KV Cache 为什么会影响显存、并发和长上下文服务？]]；[[对比问题#KV Cache 与 Prompt Cache 有什么区别？|KV Cache 与 Prompt Cache 有什么区别？]]。

---

## LLM 的上下文窗口大小由什么决定？计算资源足够时输入 Sequence 可以无限长吗？

不能简单理解成“只要计算资源足够，Sequence 就可以无限长”。**LLM 的上下文窗口是模型结构、位置编码、训练时见过的序列长度，以及推理系统资源约束共同决定的。**

### 1. Attention 的计算与存储成本会随序列增长

对长度为 $n$ 的输入，标准 Full Attention 需要计算：

$$
\operatorname{Attention}(Q,K,V)
=\operatorname{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$

其中 $QK^T$ 会形成一个 $n\times n$ 的注意力矩阵，因此标准 Attention 的主要计算复杂度随序列长度近似按 $O(n^2)$ 增长。序列从 8K 增长到 16K，Attention 相关计算量不是简单翻倍，而会接近四倍。

自回归推理使用 KV Cache 后，不需要在每一步重新计算历史 Token 的 K/V，但缓存本身仍会随上下文长度近似线性增长。因此长上下文不仅影响单次计算，也直接影响显存、并发与服务成本。参见 [[注意力机制#为什么注意力结构会从 MHA 发展到 GQA，再到 MLA？|注意力机制中的长序列成本]] 和 [[部署#KV Cache 为什么会影响显存、并发和长上下文服务？|KV Cache 的部署约束]]。

### 2. 更本质的限制之一是位置表示

Transformer 的 Attention 本身并不知道 Token 的先后顺序，因此必须注入位置信息。

如果模型使用固定长度的 Learned Absolute Position Embedding，例如只学习了位置 $1\sim4096$ 的向量，那么第 4097 个位置甚至没有对应的已学习位置参数，这会形成很直接的长度上限。

现代 LLM 常使用 RoPE。RoPE 的旋转位置可以从数学上继续计算到训练长度之外，所以它不像固定位置表那样天然具有一个同样硬的边界。但**能够计算更大的位置编号，不等于模型已经学会处理这么远的位置关系**。当模型进入训练阶段没有见过的位置和相对距离时，会出现 positional OOD；Position Interpolation、NTK-aware Scaling、YaRN 等方法，本质上都在尝试缓解这种长上下文外推问题。参见 [[RoPE#RoPE 的现代演进脉络是什么样的？|RoPE 的长上下文扩展]]。

### 3. “能够输入”不等于“模型能够可靠利用”

假设一个模型训练时主要见过最长 8K 的序列，即使推理代码和位置编码允许直接塞入 100K、1M Token，模型也没有因此自动获得稳定的百万 Token 建模能力。长上下文模型通常还需要长序列继续预训练、长上下文微调或专门的数据构造，让模型适应新的长度分布。

因此要区分两个概念：

- **Context Window**：系统允许模型访问的最大 Token 范围。
- **Effective Context**：模型实际上能够稳定检索、关联并用于推理的信息范围。

二者并不相等。一个模型“看得到”很长的上下文，不代表它对所有位置的信息利用能力都同样可靠；超长序列中的远距离检索、多跳关联和信息整合仍可能明显变难。

### 4. 如果计算资源无限，能否无限长？

即使暂时忽略 GPU 显存和算力，也仍不能把一个已经训练好的固定模型视为拥有“无限上下文”。原因在于：

1. 模型的位置表示和架构必须能够定义这些位置；
2. 模型训练时必须学会处理足够长的依赖关系，而不是只在数学上允许输入；
3. 长序列中的有效检索与信息整合能力并不会因为上下文窗口扩大而自动保持不变。

所以更准确地说：

$$
\text{Context Window}
\approx
\text{Architecture / Position Encoding}
+\text{Training Length Distribution}
+\text{Compute and Memory Constraints}
+\text{Serving Constraints}
$$

> **计算资源主要决定“长序列是否算得动”，但不能单独决定“模型是否会正确使用这么长的序列”。上下文窗口描述的是可访问范围，而不是无限可靠的记忆或推理能力。**

参考：[Attention Is All You Need](https://arxiv.org/abs/1706.03762) · [RoFormer](https://arxiv.org/abs/2104.09864) · [Extending Context Window of Large Language Models via Position Interpolation](https://arxiv.org/abs/2306.15595) · [Lost in the Middle](https://arxiv.org/abs/2307.03172)

---

## 标准 RNN 为什么存在长期依赖问题？

### 阅读背景

参考：[Hello-Agents 第三章：大语言模型基础](https://hello-agents.datawhale.cc/#/./chapter3/%E7%AC%AC%E4%B8%89%E7%AB%A0%20%E5%A4%A7%E8%AF%AD%E8%A8%80%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80)

### 参考回答（已本地化）

标准 RNN 的隐藏状态递推可以简化写成：

```text
h_t = f(W_h h_{t-1} + W_x x_t + b)
```

当前状态 `h_t` 依赖 `h_{t-1}`，而 `h_{t-1}` 又依赖更早的状态。因此，如果一个很早的输入要影响很晚的输出，信息和梯度都必须连续经过很多次状态转移。

反向传播通过时间（BPTT）时，会出现一串 Jacobian 的连乘：

```text
∂h_T / ∂h_t
= ∂h_T/∂h_{T-1} · ∂h_{T-1}/∂h_{T-2} · ... · ∂h_{t+1}/∂h_t
```

每一项都与循环权重 `W_h` 和激活函数导数有关。若这些局部导数的尺度长期小于 1，连乘后会快速趋近于 0，形成**梯度消失**；若长期大于 1，则可能指数放大，形成**梯度爆炸**。

因此，“长期依赖问题”不是说 RNN 理论上完全不能保存远处信息，而是说：**随着依赖距离增加，早期状态对后期 Loss 的训练信号越来越难稳定传回，模型很难学会保留真正需要跨很多时间步的信息。**

LSTM 和 GRU 通过门控与更接近加性的信息通路缓解这一问题，使梯度不必完全依赖长链式乘法，但并不意味着所有长程建模问题都会自动消失。

---

## RNN 参数更新明明计算的是 Loss 对参数 θ 的偏导，为什么仍会出现梯度消失或爆炸？

是的，真正用于更新网络参数的量确实是：

```text
∂L / ∂θ
```

长期依赖问题并不与这一点矛盾。关键在于：**`∂L / ∂θ` 本身就是通过计算图的链式法则得到的，而 RNN 的计算图沿时间反复复用同一组参数。**

以循环权重 `W_h` 为例，它会在每一个时间步参与状态更新。最终 Loss 对 `W_h` 的梯度，需要把参数在不同时间步产生的影响累积起来；其中，较早时间步对较晚 Loss 的影响仍然要经过多次隐藏状态之间的链式传播。

可以粗略理解为：

```text
参数 θ 在早期状态产生影响
        ↓
h_t → h_{t+1} → ... → h_T
        ↓
       Loss
```

所以虽然最外层目标是求 `∂L/∂θ`，但这个偏导内部仍包含诸如 `∂h_T/∂h_t` 这样的长链 Jacobian 连乘。梯度消失或爆炸正是在这些中间链路中产生，最后反映到参数梯度上。

换句话说：

> **“更新的是参数梯度”描述的是优化对象；“梯度消失 / 爆炸”描述的是这个参数梯度通过长计算图被求出来时遇到的数值与信息传播问题。**

---

## 文本中的词或 Token 是怎样变成 Transformer 输入向量的？

### 阅读背景

参考：[Hello-Agents 第三章：大语言模型基础](https://hello-agents.datawhale.cc/#/./chapter3/%E7%AC%AC%E4%B8%89%E7%AB%A0%20%E5%A4%A7%E8%AF%AD%E8%A8%80%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80)

### 参考回答（已本地化）

现代 LLM 通常不是“先调用一个独立、训练好的 Embedding 模型，再把向量送入 Transformer”。更典型的路径是：

```text
原始文本
  ↓
Tokenizer
  ↓
Token / Subword
  ↓
Token ID
  ↓
模型内部的 Token Embedding Matrix 查表
  ↓
连续向量表示
  ↓
加入或注入位置信息
  ↓
Transformer Blocks
```

#### 1. Tokenization：先把文本离散化

Tokenizer 使用 BPE、Unigram、SentencePiece 一类方法，把字符串切成词、子词或字符级 Token，再映射成整数 Token ID。模型真正接收的入口不是“汉字”或“单词”本身，而是一串离散 ID。

#### 2. Token Embedding：用模型自己的 Embedding Matrix 查表

模型内部维护一个可训练矩阵：

```text
E ∈ R^(V × d)
```

其中 `V` 是词表大小，`d` 是隐藏维度。一个 Token ID 相当于索引矩阵 `E` 的某一行，得到长度为 `d` 的向量。

这个 Embedding Matrix 通常就是 LLM 参数的一部分，在预训练过程中和 Transformer 其他参数一起学习，而不是额外调用一个类似 RAG Embedding API 的外部模型。有些架构还会让输入 Embedding 与最终输出词表投影共享权重。

因此要区分两种都叫 Embedding 的东西：

- **LLM Token Embedding**：模型内部把 Token ID 映射到隐藏向量，是 Transformer 输入表示的一部分。
- **RAG / Semantic Embedding Model**：把一段文本编码成用于相似度检索的向量，目标是建立文本级语义空间。参见 [[RAG#Embedding 模型应如何选择，选型不匹配会有什么表现？|RAG 中的 Embedding 模型选型]]。

#### 3. 位置信息：让模型知道 Token 的顺序

仅有 Token Embedding 时，同一组 Token 调换顺序后仍只是同一组向量，因此 Transformer 还必须获得位置关系。

原始 Transformer 会把 Positional Encoding 与 Token Embedding 相加；很多现代 Decoder-only LLM 则使用 RoPE 等方式，把位置信息作用到 Attention 中的 Query / Key，而不一定直接给输入向量加一个位置向量。

所以“Token 到 Transformer 输入向量”的核心不是调用独立 Embedding 服务，而是：**Tokenizer 离散化 → 模型内部 Embedding 查表 → 注入位置关系 → 进入 Transformer。**

---

## Q、K、V 到底是什么，Multi-Head Attention 中每个 Head 的 QKV 来自哪里？

### 阅读背景

参考：[Attention Is All You Need](https://arxiv.org/abs/1706.03762)

### 我的疑问

Q、K、V 是否可以理解成输入 Token 或 Hidden State 的线性组合？Multi-Head Attention 中，每个 Head 的 Q、K、V 是否又是所有输入的某种线性组合？

### 参考回答（已本地化）

标准 Self-Attention 中，假设一层输入为：

$$
X \in \mathbb{R}^{n \times d_{\text{model}}}
$$

其中第 $i$ 行 $x_i$ 是第 $i$ 个 Token 在当前层的 Hidden State。Q、K、V 由三个可学习线性投影得到：

$$
Q = XW_Q, \qquad K = XW_K, \qquad V = XW_V
$$

对单个 Token 来说：

$$
q_i = x_iW_Q, \qquad k_i = x_iW_K, \qquad v_i = x_iW_V
$$

因此，**Q/K/V 的确是线性组合，但这里首先组合的是一个 Token 自己 Hidden State 的各个特征维度，而不是把不同 Token 直接线性组合起来。**

真正发生跨 Token 信息混合的是 Attention：

$$
\operatorname{Attention}(Q,K,V)
= \operatorname{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$

对于第 $i$ 个 Token，其输出可以写成：

$$
o_i = \sum_j \alpha_{ij}v_j
$$

其中 $\alpha_{ij}$ 由 $q_i$ 与各个 $k_j$ 的匹配程度决定。也就是说：

```text
x_i
  ↓ 线性投影，只变换当前 Token 的特征
q_i, k_i, v_i
  ↓ Attention，与其他 Token 建立关系
Σ_j α_ij v_j
```

可以据此区分两个过程：

- **QKV Projection：特征维度的变换（feature mixing）**，每个 Token 独立经过线性层。
- **Attention：Token 维度的信息混合（token mixing）**，一个位置根据 Attention 权重聚合其他位置的 Value。

### Multi-Head Attention 中发生了什么？

每个 Head 都接收同一组输入 Hidden States，但拥有自己对应的 Q/K/V 投影参数。概念上可写为：

$$
Q^{(h)} = XW_Q^{(h)}, \qquad
K^{(h)} = XW_K^{(h)}, \qquad
V^{(h)} = XW_V^{(h)}
$$

然后每个 Head 独立计算：

$$
O^{(h)}
= \operatorname{softmax}\left(
\frac{Q^{(h)}{K^{(h)}}^T}{\sqrt{d_h}}
\right)V^{(h)}
$$

最后把各个 Head 的结果拼接并再次投影：

$$
O = \operatorname{Concat}\left(O^{(1)},\ldots,O^{(H)}\right)W_O
$$

因此更准确地说：**每个 Head 都看到了所有输入 Token，但并不是先把所有 Token 混合成自己的 Q/K/V；而是先用该 Head 的投影参数分别表示每个 Token，再由该 Head 的 Attention 在 Token 之间进行信息聚合。** 不同 Head 的投影空间不同，因此可以学习不同类型的关系模式。

还有一个容易混淆的细节：第一层中的 $x_i$ 基本来自当前 Token 的 Embedding 和位置信息；到了更深层，$x_i$ 已经经过前面多层 Attention，本身已经融合了其他 Token 的上下文。因此深层的 $q_i/k_i/v_i$ 虽然在当前层仍只是对 $x_i$ 做线性投影，但它们间接包含了此前上下文的信息。

所以核心关系可以记成：

```text
上一层 Attention：跨 Token 混合上下文
        ↓
当前层 Hidden State x_i
        ↓ W_Q / W_K / W_V
当前层 q_i / k_i / v_i
        ↓ Attention
再次跨 Token 聚合
```

---

## 为什么生成式 LLM 常强调 Decoder-only，Encoder 又用在哪里？

### 阅读背景

参考：[Hello-Agents 第三章：大语言模型基础](https://hello-agents.datawhale.cc/#/./chapter3/%E7%AC%AC%E4%B8%89%E7%AB%A0%20%E5%A4%A7%E8%AF%AD%E8%A8%80%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80)

### 参考回答（已本地化）

“Decoder-only” 的说法来自原始 Transformer 的 Encoder–Decoder 架构，但现代 GPT 类模型并不是简单把原始 Transformer 的 Decoder 原封不动拿出来使用。

原始 Transformer 可以先区分三种典型结构：

| 架构 | Attention 特点 | 典型用途 / 模型 |
| --- | --- | --- |
| **Encoder-only** | 输入内部通常可以双向互相关注 | BERT 一类表示学习、理解、分类、抽取 |
| **Decoder-only** | 使用 Causal Mask，只允许当前位置关注过去 Token | GPT 类自回归生成式 LLM |
| **Encoder–Decoder** | Encoder 双向编码输入；Decoder 自回归生成，并通过 Cross-Attention 读取 Encoder 表示 | T5、BART、机器翻译等 Seq2Seq 任务 |

### Encoder 做什么

Encoder 的核心目标是把整段输入编码成上下文化表示。由于它通常可以同时看到一个 Token 左右两侧的信息，因此特别适合“理解一个已经完整给出的输入”，例如分类、匹配、抽取和句子表示。

BERT 就是典型 Encoder-only 模型：它关注如何得到高质量上下文表示，而不是从左到右持续生成后续文本。

### Decoder-only 为什么适合生成式 LLM

生成任务天然符合自回归分解：

```text
P(x_1, x_2, ..., x_n)
= Π P(x_t | x_<t)
```

也就是每一步根据此前 Token 预测下一个 Token。Causal Self-Attention 正好对应这一约束，因此同一套架构可以统一处理“Prompt + 已生成内容 → 下一个 Token”。

对于聊天、代码生成、工具调用等开放式生成任务，不再需要先把输入编码成一套独立的 Encoder 表示，再由 Decoder 解码；Prompt 本身就可以作为同一个自回归序列的前缀。这让训练目标与推理流程非常统一，也是 Decoder-only 成为现代通用生成式 LLM 主流架构的重要原因之一。

### 现代 Decoder-only 与原始 Transformer Decoder 的区别

原始 Transformer Decoder 既有：

1. Masked Self-Attention；
2. 对 Encoder 输出的 Cross-Attention。

但 GPT 类 Decoder-only 模型没有独立 Encoder，所以通常也没有这层面向 Encoder 输出的 Cross-Attention。它保留的是**因果自注意力 + 前馈网络等 Decoder 风格核心结构**。

因此“强调 Decoder-only”主要是在说明模型采用**单栈、因果、自回归生成**路线；Encoder 并没有消失，而是在 BERT 类表示模型以及 T5 / BART 等 Encoder–Decoder 模型中承担另一种角色。

---

相关主题：[[Agent]] · [[RAG]] · [[部署]] · [[对比问题]]