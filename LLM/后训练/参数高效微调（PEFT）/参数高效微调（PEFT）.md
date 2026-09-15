# 参数高效微调（PEFT）

[[后训练|返回上级：后训练]] · [[main|返回知识主干]]

参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）通过冻结大部分基础模型参数，只训练少量新增或选定参数，在尽量保留模型能力的同时显著降低训练显存、存储和多任务适配成本。

## 问题目录

- [[参数高效微调（PEFT）#LoRA 是什么？|LoRA 是什么？]]
- [[参数高效微调（PEFT）#LoRA 增加的可训练低秩增量具体是什么？|LoRA 增加的可训练低秩增量具体是什么？]]
- [[参数高效微调（PEFT）#为什么 LoRA 的参数增量可以用低秩矩阵表示？|为什么 LoRA 的参数增量可以用低秩矩阵表示？]]
- [[参数高效微调（PEFT）#LoRA Adapter 是如何实现的？|LoRA Adapter 是如何实现的？]]
- [[参数高效微调（PEFT）#QLoRA 是什么？|QLoRA 是什么？]]

---

## LoRA 是什么？

LoRA（Low-Rank Adaptation）是一种典型的 PEFT 方法。它冻结原始权重矩阵 $W$，不直接更新整块参数，而是在目标线性层旁加入一个可训练的低秩增量：

> $W' = W + \Delta W,\quad \Delta W = BA$

其中中间秩 $r$ 远小于原权重矩阵的输入、输出维度，因此实际训练参数量显著减少。训练完成后，LoRA Adapter 可以单独保存，也可以与基础模型权重合并用于推理。

LoRA 的核心价值是：**以较小的可训练参数和显存开销完成模型适配，而不必对整个基础模型做 Full Fine-tuning。**

---

## LoRA 增加的可训练低秩增量具体是什么？

对于原线性层 $y = Wx$，LoRA 冻结 $W$，额外学习一个与 $W$ 同形状的权重修正 $\Delta W$：

> $W' = W + \Delta W,\quad \Delta W = BA$

若 $W \in \mathbb{R}^{d_{out}\times d_{in}}$，则通常令：

> $A \in \mathbb{R}^{r\times d_{in}},\quad B \in \mathbb{R}^{d_{out}\times r}$

其中 $r \ll d_{in}, d_{out}$。因此并不直接训练一个完整的 $d_{out}\times d_{in}$ 增量矩阵，而是只训练两个小矩阵 $A$ 和 $B$。

前向计算可写为：

> $y = Wx + sBAx$

其中 $s$ 通常是由 `lora_alpha` 和 rank 决定的缩放系数。$BA$ 就是 LoRA 学到的“原权重应该怎样变化”。

---

## 为什么 LoRA 的参数增量可以用低秩矩阵表示？

LoRA 的核心假设是：**针对一个具体下游任务，真正有效的参数更新通常不需要在整个高维参数空间中自由变化，而主要集中在较低维的子空间中。**

因此，即使原权重 $W$ 很大，其任务相关更新 $\Delta W$ 也可以用较低 rank 的矩阵近似：

> $\Delta W \approx BA$

这相当于只学习少数关键的参数变化方向，而不是为原矩阵的每个元素都提供独立自由度。

低秩近似是否足够取决于任务和 rank $r$：rank 越大，更新自由度越高，同时训练参数量和显存开销也会增加。

---

## LoRA Adapter 是如何实现的？

工程上，$A$ 和 $B$ 通常就实现为两个无 Bias 的小型线性层。例如原层输入、输出维度均为 4096，rank $r=8$ 时，可以理解为：

> **4096 → 8 → 4096**

也就是先通过 $A$ 将输入投影到低维适配空间，再通过 $B$ 投影回原输出维度，并将该结果作为增量加到原线性层输出上：

> $y = Wx + sB(Ax)$

实际框架通常会把已有 `Linear` 包装成带 LoRA 分支的模块：

- 原 `base_layer` 保持冻结；
- `lora_A`、`lora_B` 为可训练参数；
- 可选加入 LoRA Dropout 与 Scaling；
- 训练时优化器只更新 LoRA 参数。

LoRA 通常会注入 Attention 的 `q_proj`、`k_proj`、`v_proj`、`o_proj` 或 FFN 等目标线性层。一个完整的 **LoRA Adapter** 并不是单独的一个网络，而是模型中所有目标层上的 LoRA A/B 参数集合。

常见初始化会令 $A$ 随机初始化、$B$ 初始化为 0，使初始时 $BA=0$，因此刚插入 Adapter 时模型行为保持不变。

训练完成后，可以继续以 **Base Model + Adapter** 的形式加载，也可以计算：

> $W_{merged} = W + sBA$

把 LoRA 更新直接合并回原权重，用普通线性层进行推理。

---

## QLoRA 是什么？

QLoRA（Quantized LoRA）是在 LoRA 基础上进一步降低训练显存的方法。它将冻结的基础模型以低比特形式量化保存和参与前向 / 反向计算，同时仍训练 LoRA Adapter。

典型形式可以理解为：

> **Quantized Frozen Base Model + Trainable LoRA Adapter**

QLoRA 主要节省的是基础模型权重带来的显存占用，使更大的模型可以在有限硬件上进行参数高效微调。它并不意味着 LoRA Adapter 本身必须以低比特方式训练，也不改变所使用的训练目标。

> **LoRA 通过减少可训练参数降低微调成本；QLoRA 在此基础上再通过量化冻结的基础模型进一步降低显存需求。**

---

相关主题：[[后训练]] · [[SFT]] · [[对比问题#SFT 与 Full Fine-tuning、LoRA、QLoRA 是什么关系？|SFT 与 Full Fine-tuning、LoRA、QLoRA 是什么关系？]]
