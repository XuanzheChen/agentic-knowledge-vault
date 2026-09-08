# LLM

[[index|返回知识索引]]

围绕大语言模型的基础机制与阅读疑问整理 Q&A。

## 问题目录

- [[LLM#KV Cache 是什么，为什么能加速逐 Token 生成？|KV Cache 是什么，为什么能加速逐 Token 生成？]]
- [[LLM#阅读大语言模型基础后，还有哪些问题需要整理？|阅读大语言模型基础后，还有哪些问题需要整理？]]（待补充）

---

## KV Cache 是什么，为什么能加速逐 Token 生成？

### 参考回答

[ChatGPT 原回答](https://chatgpt.com/share/6a9a7137-7020-83ea-8a03-dd39f1a5d76f)

**KV Cache 是在 Transformer 自回归推理过程中，将历史 Token 在 Attention 中产生的 Key（K）和 Value（V）张量缓存起来。**

生成新 Token 时，只需计算新增 Token 对应的 K/V，并复用历史 Token 已计算的 K/V，避免重复计算历史部分，从而显著提高逐 Token 的生成速度。

延伸阅读：[[部署#KV Cache 为什么会影响显存、并发和长上下文服务？|KV Cache 为什么会影响显存、并发和长上下文服务？]]；[[对比问题#KV Cache 与 Prompt Cache 有什么区别？|KV Cache 与 Prompt Cache 有什么区别？]]。

---

## 阅读大语言模型基础后，还有哪些问题需要整理？

阅读材料：HelloAgent Blog 的大语言模型基础章节。

### 参考资料

- [第三章：大语言模型基础](https://hello-agents.datawhale.cc/)

### 参考对话

- [ChatGPT 原回答](https://chatgpt.com/share/6a8e5bf4-042c-83ec-b097-0d082a3bf303)

> 待补充：阅读后的具体问题、结论或案例。

---

相关主题：[[Agent]] · [[部署]] · [[对比问题]]
