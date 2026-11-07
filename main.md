# AI 知识 Q&A

从底层概念出发，记录原理、工程取舍与个人思考。`main.md` 是知识森林的主干入口；具体知识沿 Tree 逐级展开，Q&A 作为各 Tree 中的叶子，通过双向链接横向连接相关问题。

## 知识主干

| Tree | 内容 |
| --- | --- |
| [LLM](LLM/LLM.md) | 大语言模型基础机制，以及预训练、中训练、后训练、模型架构与推理部署 |
| [Agent](Agent/Agent.md) | Agent 状态与执行循环，并延伸到框架、通信、Context、Memory、RAG 与评估 |
| [agentic-sdlc-contract-runtime](agentic-sdlc-contract-runtime/agentic-sdlc-contract-runtime.md) | PSC 契约驱动研发运行时的实际架构、调度、验收与持久化恢复 |
| [RSI](RSI/RSI.md) | 递归式自我改进、自动化 AI R&D 闭环，以及 AI 参与改进后继系统的机制与边界 |
| [对比问题](对比问题/对比问题.md) | 难以可靠归入单一 Tree 的跨概念区别、联系与方案选择 |

## LLM

- [LLM](LLM/LLM.md)
  - [预训练](LLM/预训练/预训练.md)
    - [预训练数据](LLM/预训练/预训练数据/预训练数据.md)
    - [训练目标](LLM/预训练/训练目标/训练目标.md)
    - [激活函数与 FFN](LLM/预训练/激活函数与FFN/激活函数与FFN.md)
    - [归一化](LLM/预训练/归一化/归一化.md)
    - [MoE](LLM/预训练/MoE/MoE.md)
    - [RoPE](LLM/预训练/RoPE/RoPE.md)
    - [注意力机制](LLM/预训练/注意力机制/注意力机制.md)
    - [残差连接](LLM/预训练/残差连接/残差连接.md)
  - [推理能力](LLM/推理能力/推理能力.md)
  - [中训练](LLM/中训练/中训练.md)
  - [后训练](LLM/后训练/后训练.md)
    - [SFT](LLM/后训练/SFT/SFT.md)
    - [偏好学习](LLM/后训练/偏好学习/偏好学习.md)
    - [RL-based Post-training](LLM/后训练/RL-based Post-training/RL-based Post-training.md)
    - [Reward Hacking](LLM/后训练/Reward Hacking/Reward Hacking.md)
    - [参数高效微调（PEFT）](LLM/后训练/参数高效微调（PEFT）/参数高效微调（PEFT）.md)
  - [部署](LLM/部署/部署.md)

## Agent

- [Agent](Agent/Agent.md)
  - [Harness](Agent/Harness/Harness.md)
  - [Agent 框架](Agent/Agent框架/Agent框架.md)
  - [通信协议](Agent/通信协议/通信协议.md)
  - [Context](Agent/Context/context.md)
    - [Memory](Agent/Context/Memory/Memory.md)
    - [RAG](Agent/Context/RAG/RAG.md)
  - [评估](Agent/评估/评估.md)

## agentic-sdlc-contract-runtime

- [PSC 运行时架构](agentic-sdlc-contract-runtime/agentic-sdlc-contract-runtime.md)

## RSI

- [RSI](RSI/RSI.md)

## 待继续思考的问题

- [[RAG#RAG 解决什么问题，与幻觉有什么关系？|RAG 解决什么问题，与幻觉有什么关系？]]（待补充）
- [[对比问题#Memory 与 RAG 的作用和增强策略有什么区别？|Memory 与 RAG 的作用和增强策略有什么区别？]]（待补充）