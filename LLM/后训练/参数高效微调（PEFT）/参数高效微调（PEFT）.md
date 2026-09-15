# 参数高效微调（PEFT）

[[后训练|返回上级：后训练]] · [[main|返回知识主干]]

参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）通过冻结大部分基础模型参数，只训练少量新增或选定参数，在尽量保留模型能力的同时显著降低训练显存、存储和多任务适配成本。

## 问题目录

- [[参数高效微调（PEFT）#LoRA 是什么？|LoRA 是什么？]]
- [[参数高效微调（PEFT）#QLoRA 是什么？|QLoRA 是什么？]]

---

## LoRA 是什么？

LoRA（Low-Rank Adaptation）是一种典型的 PEFT 方法。它冻结原始权重矩阵 $W$，不直接更新整块参数，而是在目标线性层旁加入一个可训练的低秩增量：

> $W' = W + \Delta W,\quad \Delta W = BA$

其中 $A$、$B$ 的秩远小于原权重矩阵，因此实际训练参数量显著减少。训练完成后，LoRA Adapter 可以单独保存，也可以与基础模型权重合并用于推理。

LoRA 的核心价值是：**以较小的可训练参数和显存开销完成模型适配，而不必对整个基础模型做 Full Fine-tuning。**

---

## QLoRA 是什么？

QLoRA（Quantized LoRA）是在 LoRA 基础上进一步降低训练显存的方法。它将冻结的基础模型以低比特形式量化保存和参与前向 / 反向计算，同时仍训练 LoRA Adapter。

典型形式可以理解为：

> **Quantized Frozen Base Model + Trainable LoRA Adapter**

QLoRA 主要节省的是基础模型权重带来的显存占用，使更大的模型可以在有限硬件上进行参数高效微调。它并不意味着 LoRA Adapter 本身必须以低比特方式训练，也不改变所使用的训练目标。

> **LoRA 通过减少可训练参数降低微调成本；QLoRA 在此基础上再通过量化冻结的基础模型进一步降低显存需求。**

---

相关主题：[[后训练]] · [[SFT]] · [[对比问题#SFT 与 Full Fine-tuning、LoRA、QLoRA 是什么关系？|SFT 与 Full Fine-tuning、LoRA、QLoRA 是什么关系？]]
