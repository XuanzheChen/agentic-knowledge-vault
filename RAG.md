# RAG

[[index|返回知识索引]] · [[Memory]]

围绕检索增强生成中的知识组织、Embedding、Chunk 切分、检索架构与工程框架整理 Q&A。

## 问题目录

- [[RAG#RAG 解决什么问题，与幻觉有什么关系？|RAG 解决什么问题，与幻觉有什么关系？]]（待补充）
- [[RAG#RAG 如何组织原始数据、元数据与检索索引？|RAG 如何组织原始数据、元数据与检索索引？]]
- [[RAG#Embedding 模型应如何选择，选型不匹配会有什么表现？|Embedding 模型应如何选择，选型不匹配会有什么表现？]]
- [[RAG#Chunk 切分为什么要兼顾结构、语义完整性和长度？|Chunk 切分为什么要兼顾结构、语义完整性和长度？]]
- [[RAG#HelloAgents 提到的 MQE 与 HyDE 分别在解决什么检索问题？|HelloAgents 提到的 MQE 与 HyDE 分别在解决什么检索问题？]]
- [[RAG#LlamaIndex、Haystack 与 RAGFlow 分别处在 RAG 工程的什么层级？|LlamaIndex、Haystack 与 RAGFlow 分别处在 RAG 工程的什么层级？]]
- [[RAG#GraphRAG 是什么，它为什么不是普通 Vector RAG 的简单升级版？|GraphRAG 是什么，它为什么不是普通 Vector RAG 的简单升级版？]]
- [[RAG#一个完整的工程化 RAG Pipeline 是什么样的？|一个完整的工程化 RAG Pipeline 是什么样的？]]
- [[RAG#Hybrid Retrieve → Rerank RAG 为什么可以作为稳健的工程 Baseline？|Hybrid Retrieve → Rerank RAG 为什么可以作为稳健的工程 Baseline？]]
- [[RAG#Bi-Encoder 为什么适合做 Dense Retrieval？|Bi-Encoder 为什么适合做 Dense Retrieval？]]
- [[RAG#RRF 如何融合多个 Retriever 的结果？|RRF 如何融合多个 Retriever 的结果？]]
- [[RAG#Reranker 为什么需要 Cross-Encoder，LLM Reranker 与 Late Interaction 又有什么取舍？|Reranker 为什么需要 Cross-Encoder，LLM Reranker 与 Late Interaction 又有什么取舍？]]
- [[RAG#Hierarchical / Parent-Child RAG 在解决什么问题？|Hierarchical / Parent-Child RAG 在解决什么问题？]]
- [[RAG#Agentic RAG 与固定 RAG Pipeline 有什么区别？|Agentic RAG 与固定 RAG Pipeline 有什么区别？]]

---

## RAG 解决什么问题，与幻觉有什么关系？

### 思路

从 RAG 的基本定义出发，延伸到大模型的幻觉问题，最后讨论 Harness 中的检索。

> 待补充：RAG 如何为对话系统提供可追溯的外部知识、降低知识缺失导致的幻觉，以及它与长期记忆、工具检索的边界。

---

## RAG 如何组织原始数据、元数据与检索索引？

RAG 的信息通常不会只把原始文档直接放进数据库，而会先解析、清洗和切块，然后保存不同表示：原始文件放对象存储；文档 ID、来源、页码和权限等元数据放关系数据库；用于检索的 Chunk 建立全文索引或 Embedding 向量索引。查询时先从索引召回最相关的 Chunk，再重排序，将少量高相关内容交给模型。

仅把原始文档放进数据库，并不等于建立了适合 RAG 的检索结构。除了按 ID、字段或精确条件查询，还需要考虑用户问题与原文在字面上不一致的情况，并支持语义检索。若直接以整篇文档为单位，粒度太粗，相关信息会被其他内容稀释，也无法把所有文档都送进模型。

RAG 的核心是把知识加工为合适的检索单元和索引。工程上文本、元数据和向量可以位于同一个物理数据库，但逻辑上仍应区分原始数据、Chunk、元数据和检索索引。实际系统通常结合关键词检索与向量检索，并通过重排序提高召回率与准确率。

---

## Embedding 模型应如何选择，选型不匹配会有什么表现？

选择 Embedding 模型时，先看其是否匹配业务场景。Embedding 将输入文本表示为向量，可用于 RAG、聚类、分类、跨语言匹配或文本相似度任务。若场景是 RAG，主要关注检索 Benchmark 的综合表现；还应关注：

- **语言匹配**：语料存在多语言时，考察跨语言检索能力。
- **领域适配**：通用模型未必能充分表达专业术语。
- **长度与粒度**：模型支持的文本长度是否匹配 Chunk 粒度。
- **输入规范**：部分模型要求为 Query 和 Document 添加不同前缀或任务说明；未按训练规范输入会显著降低性能。

有条件时，应使用真实业务语料测试候选模型。

选错模型最典型的现象是：**答案明明在知识库中，Top-K 却根本召不回来**；或者召回内容表面相关，但真正能回答问题的 Chunk 排名很靠后。进一步还可能表现为专业术语检索差、中文表现正常但中英跨语言召回差、短文本正常而长文本效果明显下降。后续生成模型再强，也无法弥补错误的输入上下文。

---

## Chunk 切分为什么要兼顾结构、语义完整性和长度？

### 切分目标与策略

Chunking 的目标不是机械切出固定长度，而是构造适合 Embedding 检索、同时尽可能语义完整的信息单元。固定长度切分常常不够，因为 Token 边界与语义边界无关，容易从中间切断一句话、段落、实验结论，甚至表格与解释；不同文本的信息密度也不同，相同长度不代表相同语义粒度。

可以采用“**结构优先、语义完整、长度约束**”的策略：论文优先按 Section、Subsection、Paragraph 等天然结构划分；段落过长时再按句子递归拆分；多个短段落属于同一主题时可以合并。必要时加入少量 Overlap，避免关键信息落在边界处；但 Overlap 不能过大，否则会带来大量重复召回。

Chunk 大小本身存在权衡：Chunk 太小，检索精准但上下文易缺失；Chunk 太大，上下文完整但 Embedding 容易混合多个主题。因此可以将检索粒度和生成粒度分开：先用小 Chunk 召回，命中后扩展到所属父段落或小节，再将较完整上下文交给模型。

Chunk Size 应因业务而定。无法开展实验时，可参照相近业务和文档类型的经验值；有真实业务数据时，应比较不同切分策略的召回率、排序效果和最终问答准确率。

> **固定长度只能保证大小一致；好的 Chunking 要尽量保证语义完整。**

### 固定长度切分的局限

单纯增大 Chunk Size 会让语义变得模糊，真正有价值的信息被稀释；即使加入 Overlap，也难以彻底避免连续语义被切碎。相同大小的 Chunk 仍可能具有不一致的语义粒度，需要检索的内容也可能刚好被截断。

若完全按固定 Token 数量粗暴切分，表格、图像等也会被分开。即便形式上不把它们切开，表格、图像仍需要与对应原文保持关联；若切分后无法互相联系，就会造成语义模糊和信息丢失。

---

## HelloAgents 提到的 MQE 与 HyDE 分别在解决什么检索问题？

这里仅保留 HelloAgents 第 8 章中有启发性的高级检索策略，不整理其完整 RAGTool 实现。

参考：[HelloAgents 第八章：记忆与检索](https://hello-agents.datawhale.cc/#/./chapter8/%E7%AC%AC%E5%85%AB%E7%AB%A0%20%E8%AE%B0%E5%BF%86%E4%B8%8E%E6%A3%80%E7%B4%A2)

### Multi-Query Expansion（MQE）：从不同表达角度扩大召回

用户的一个 Query 往往只是某种措辞，而知识库可能用完全不同的表述描述同一个概念。MQE 先让 LLM 将原 Query 改写成多个语义相近但表达不同的 Query，再分别检索并合并结果：

```text
Original Query
   ├─ Query 1 → Retrieval
   ├─ Query 2 → Retrieval
   └─ Query 3 → Retrieval
              ↓
        Merge + Dedup
```

它的核心目标是提高 **Recall**：降低“答案存在，但由于 Query 和文档措辞不同而没有被召回”的概率。

代价是额外的 LLM 调用和多次 Retrieval，会增加延迟、Token 成本以及 Query Drift 风险，因此不一定适合每一个简单问题。

### HyDE：用“像答案的文档”缩小 Query 与 Document 的语义形态差异

HyDE（Hypothetical Document Embeddings）先让 LLM 针对问题生成一段假想答案，再对这段假想文档做 Embedding，用它去检索真实知识库：

```text
Question
   ↓
Hypothetical Answer / Document
   ↓
Embedding
   ↓
Retrieve Real Documents
```

它利用的是一个直觉：知识库里的 Chunk 通常是“陈述答案的文档”，而用户输入通常是“提问”。假想答案在语言形态上更像真实文档，因此有时比直接 Embedding Question 更容易落到正确的向量区域。

HyDE 同样主要服务于 Recall，但假想答案如果方向偏离，也可能把检索带向错误区域。

> **MQE 是“多换几种问法去找”，HyDE 是“先假装有一个答案，再拿这个答案去找真正的文档”。两者都属于 Query-side Retrieval Enhancement，而不是精排。**

---

## LlamaIndex、Haystack 与 RAGFlow 分别处在 RAG 工程的什么层级？

截至 2026 年，这三个开源项目都可以用于 RAG，但它们并不处在完全相同的抽象层。

| 项目 | 更接近什么 | 核心特点 | 适合场景 |
| --- | --- | --- | --- |
| **LlamaIndex** | RAG / Data Framework | 数据、Node、Index、Retriever、Postprocessor、Response Synthesizer 等抽象非常丰富 | 学习和组合各种 RAG 策略、构建高度可定制的数据应用 |
| **Haystack** | Component / Pipeline Framework | 通过显式 Pipeline 连接 Converter、Splitter、Retriever、Ranker、Prompt Builder、Generator | 需要清晰、可测试的数据流和工程 Pipeline |
| **RAGFlow** | End-to-End RAG System | 文档解析、Chunk、Index、Hybrid Retrieval、Rerank、知识库、Agent、UI 和 API 集成度高 | 企业知识库、PDF / 文档问答、希望快速得到完整系统 |

### LlamaIndex：RAG 原语和检索策略最丰富

LlamaIndex 当前文档把 RAG 明确拆成 Loading / Ingestion、Indexing、Storing、Querying 等阶段，并进一步提供 Document / Node、Retriever、Node Postprocessor、Response Synthesizer、Router、Property Graph 等模块。它还包含 BM25、Ensemble / Fusion、Auto-Merging、Recursive Retriever 等大量 Retrieval 组件。

它最值得学习的抽象之一是 **Node**：一个文档可以产生多个 Node，Node 可以携带 metadata 和父子 / 文档引用，因此比单纯“平铺 Chunk”更适合 Hierarchical、Recursive、Parent-Child 等检索结构。

**优点**：策略丰富、组件多、适合实验和高度定制；能够从简单 Vector RAG 渐进扩展到 Hybrid、Hierarchical、Graph 和 Agentic RAG。

**局限**：概念与抽象很多，容易出现“会调 API，但没真正理解 Retrieval Pipeline”的情况；已有成熟数据基础设施的团队往往只选用其中部分模块，而不会让整个系统都服从 LlamaIndex 抽象。

参考：[LlamaIndex Framework](https://developers.llamaindex.ai/python/framework/)

### Haystack：显式的数据流 Pipeline

Haystack 以 Components、Pipelines、Document Stores 为核心。典型 Indexing Pipeline 可以写成：

```text
Converter → Cleaner → Splitter → Embedder → DocumentWriter
```

Query Pipeline 则可以是：

```text
Query → Embedder → Retriever → Ranker → PromptBuilder → Generator
```

**优点**：每一个阶段清楚、组件解耦、便于单独测试和替换 Retriever / Ranker / Generator，非常适合工程团队把 RAG 当作数据处理 Pipeline 来治理。

**局限**：当流程越来越依赖动态路由、反复检索和 Agent 自主决策时，固定 Pipeline 会变复杂，需要逐步引入 Router、Loop 或 Agent 机制。

参考：[Haystack Documentation](https://docs.haystack.deepset.ai/docs/intro)

### RAGFlow：完整系统而不是单纯代码框架

RAGFlow 更像已经组装好的 RAG 产品基础设施。它提供可视化 Ingestion Pipeline，当前文档中的典型链路为：

```text
Parser → Chunker → Transformer → Indexer
```

Indexer 支持 Full-text、Embedding 与 Hybrid，其中官方当前把 Hybrid 标为推荐方式；还可以索引处理后的原文、生成的问题或增强后的摘要上下文。近期版本也加入了 Parent-Child Chunking、自动 Metadata 等能力。

**优点**：从文档解析、知识库、检索到 Agent / UI / API 集成度高，企业文档问答可以较快落地。

**局限**：部署和依赖比 Library 型框架明显更重，内部默认方案也更多；如果只想验证一个 Retriever 或做轻量实验，使用整套 RAGFlow 可能属于过度工程化。

参考：[RAGFlow Indexer](https://github.com/infiniflow/ragflow/blob/main/docs/guides/agent/ingestion_pipeline/configure_indexer_component.md) · [Ingestion Pipeline](https://github.com/infiniflow/ragflow/blob/main/docs/guides/agent/ingestion_pipeline/create_ingestion_pipeline.md)

### 如何理解三者

可以粗略看成：

```text
更多自己设计
    ↑
LlamaIndex   —— 提供丰富 RAG 原语
Haystack     —— 提供显式 Pipeline 积木
RAGFlow      —— 提供较完整的 RAG 系统
    ↓
更多开箱即用
```

它们不是严格的优劣关系，而是抽象层和默认能力不同。

---

## GraphRAG 是什么，它为什么不是普通 Vector RAG 的简单升级版？

GraphRAG 这里主要指 Microsoft GraphRAG 代表的 **Knowledge Graph + Community Summary RAG** 路线。它针对的是普通 Top-K Vector RAG 很难解决的一类问题：**需要理解整个数据集结构或跨多个实体关系进行推理的问题。**

例如：

> “这 1 万份文档总体有哪些主要主题？”

普通 Vector Retrieval 很难知道应该从哪些 Chunk 开始，因为 Query 本身没有指向所有主题的关键词。GraphRAG 在 Index 阶段额外做：

```text
Corpus
  ↓
TextUnits
  ↓
Entity / Relationship / Claim Extraction
  ↓
Knowledge Graph
  ↓
Hierarchical Community Detection
  ↓
Community Summaries
```

Microsoft GraphRAG 当前主要提供几种 Query Mode：

- **Local Search**：从与 Query 相关的实体进入图，结合关联实体、关系、Community Report 和原始 Text Unit，适合围绕具体实体的查询。
- **Global Search**：在 Community Reports 上进行 Map-Reduce，适合“整个语料的主要主题、整体趋势是什么”这类 whole-dataset reasoning。
- **DRIFT Search**：在 Local Search 基础上利用 Community 信息扩展查询视野，并生成更细的 follow-up questions。
- **Basic Search**：提供普通 Vector RAG 作为基线。

参考：[GraphRAG Overview](https://microsoft.github.io/graphrag/) · [Query Engine](https://microsoft.github.io/graphrag/query/overview/) · [Global Search](https://microsoft.github.io/graphrag/query/global_search/) · [Local Search](https://microsoft.github.io/graphrag/query/local_search/)

### 优点

- 能显式利用实体与关系，适合 multi-hop / entity-centric reasoning。
- Community Summary 为全局主题和整库问题提供了普通 Vector RAG 缺少的高层表示。
- Graph 和 Text Unit 可以互补：结构信息用于扩展关系，原始文本仍可提供证据。

### 局限

- Indexing 很重：需要实体 / 关系抽取、构图、Community Detection 与 Summary，成本、延迟和实现复杂度显著高于普通 RAG。
- 抽取和 Entity Resolution 错误会污染图结构。
- 对“某个错误码是什么意思”“某段文档写了什么”这类简单问题，普通 Hybrid RAG 往往更直接。

> **GraphRAG 不是“Vector RAG → Hybrid RAG → GraphRAG”这一条必然升级链上的最高级版本。它是一种针对关系密集和全局语料推理问题的数据组织与检索架构。**

---

## 一个完整的工程化 RAG Pipeline 是什么样的？

一个成熟 RAG 最好不要被理解成“Embedding + Vector DB + LLM”，而应分成四层：

> **Ingestion / Indexing → Retrieval → Context Engineering → Grounded Generation**

### 1. Ingestion / Indexing：把原始知识加工成可检索表示

```text
Raw Documents
    ↓
Parser / OCR / Layout Analysis
    ↓
Cleaning / Normalization
    ↓
Chunking / Hierarchy Construction
    ↓
Metadata Extraction
    ↓
Embedding / Sparse Features
    ↓
Dense Index + Sparse Index + Metadata Store
```

这里决定“知识库里究竟存了什么”。如果 PDF 的表格、标题层级、图片说明在解析阶段就已经丢失，后面再好的 Retriever 也无法恢复原始语义。

### 2. Retrieval：尽量找到正确候选

```text
User Query
   ↓
Query Understanding / Rewrite / Expansion
   ↓
Metadata / ACL Filter
   ↓
Dense / Sparse / SQL / Graph / Other Retriever
   ↓
Candidate Pool
```

这一阶段首先追求 **Recall**：正确证据必须进入候选集。

### 3. Context Engineering：从候选中构造真正有用的上下文

```text
Candidate Pool
    ↓
Fusion / Dedup
    ↓
Rerank
    ↓
Parent Expansion / Context Compression
    ↓
Ordering + Token Budget
    ↓
Final Context
```

这里解决的问题不是“有没有找到”，而是“哪些证据最值得让模型看到，以及以什么形式看到”。

### 4. Grounded Generation：让回答受到证据约束

```text
Final Context
    ↓
LLM Generation
    ↓
Citation / Evidence Mapping
    ↓
Grounding / Faithfulness Check
```

因此一个更完整的 RAG mental model 是：

```text
Knowledge
   ↓
Ingestion / Indexing
   ↓
Retrieval
   ↓
Context Engineering
   ↓
Grounded Generation
```

实际框架的各种模块基本都可以问一句：**它是在增强这四层中的哪一层？**

---

## Hybrid Retrieve → Rerank RAG 为什么可以作为稳健的工程 Baseline？

只用 Dense Vector Retrieval 存在一个明显问题：它擅长语义相似，却不一定擅长精确字符串。

例如：

- “神经网络怎样减少泛化误差”与“如何缓解模型过拟合”适合 Dense Retrieval。
- `CUDA_ERROR_700`、函数名、RFC 编号、产品型号、人名等往往更适合 Sparse / Keyword Search。

因此比较稳健的工程结构是：

```text
Query
  ↓
Metadata / ACL Filter
  ↓
┌────────────────────┐
│ Dense Retrieval    │  semantic
│ Sparse / BM25      │  lexical
└────────────────────┘
  ↓
Fusion（如 RRF / weighted fusion）
  ↓
Large Candidate Pool
  ↓
Cross-Encoder / LLM Reranker
  ↓
Top-K Evidence
  ↓
LLM
```

这里要区分两个目标：

- **Retriever 负责 Recall**：快速从大规模知识库中捞出较大的候选集合。
- **Reranker 负责 Precision**：对少量 Candidate 做 Query-Document 的更精细交互，重新判断哪些最相关。

Cross-Encoder 比分别 Embedding Query / Document 更慢，但因为 Candidate 数量已经被 Retriever 限制到几十或几百条，所以可以把昂贵计算放在第二阶段。

> **先用便宜检索尽量不漏，再用昂贵模型精排，这就是 Retrieve → Rerank 的核心工程取舍。**

Hybrid 并不是任何场景都必须使用，但对于同时存在自然语言、专有名词、代码、编号等混合语料的企业知识库，它通常比纯 Dense 更稳健。RAGFlow 当前也直接把 Hybrid（Full-text + Embedding）作为推荐 Index Search 方法；LlamaIndex 则提供 BM25、Ensemble、Fusion 等组合能力。

具体模型和排序机制见 [[RAG#Bi-Encoder 为什么适合做 Dense Retrieval？|Bi-Encoder]]、[[RAG#RRF 如何融合多个 Retriever 的结果？|RRF]] 与 [[RAG#Reranker 为什么需要 Cross-Encoder，LLM Reranker 与 Late Interaction 又有什么取舍？|Reranker]]。

---

## Bi-Encoder 为什么适合做 Dense Retrieval？

RAG 中通常所说的 Dense Embedding Retriever，本质上大多采用 **Bi-Encoder（双编码器，也常称 Dual Encoder / Two-Tower）** 思路：Query 和 Document 分别编码为固定长度向量，再用 cosine similarity、dot product 等向量相似度进行检索。

```text
Query ─────→ Encoder ─────→ Query Vector
                                │
                                │ similarity / ANN
                                ↓
Document ─→ Encoder ─────→ Document Vector
```

这里“Bi”强调的是 **Query 与 Document 独立编码**；两侧是否共享完全相同的参数取决于具体模型设计。由于 Document 的表示不依赖当前 Query，所有文档向量都可以离线预计算并建立 ANN（Approximate Nearest Neighbor）索引。线上只需编码一次 Query，再在大规模向量索引中寻找 Top-K，因此非常适合百万级乃至更大语料的第一阶段召回。

参考：[Sentence Transformers：Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)

### 为什么它适合做 Retriever？

- **Document 可以预计算**：线上不需要重新跑每一篇文档的 Transformer。
- **适合 ANN Index**：Query 与 Document 都是单个固定向量，可以交给向量数据库高效检索。
- **吞吐量高**：一次 Query 可以快速和大规模 Corpus 做近邻搜索。
- **语义召回能力强**：相较纯关键词匹配，更容易找到同义表达、改写和语义相近内容。

### 它为速度牺牲了什么？

Bi-Encoder 的 Query 与 Document 在编码阶段并没有直接进行 Token-level interaction。一个较长 Chunk 最终要被压缩成一个向量，模型必须在这个固定表示中保留对各种潜在 Query 都有用的信息。因此它存在明显的 **single-vector information bottleneck**：

```text
Document 中很多 Token / 事实
          ↓
      一个向量
          ↓
再和 Query Vector 比较
```

这使 Dense Retriever 很适合回答“哪些文档可能相关”，但不一定擅长精确判断“哪个 Chunk 真正能回答这个 Query”。因此工程 RAG 经常让 Bi-Encoder 承担高 Recall 的第一阶段召回，再把几十到几百个候选交给更贵的 Reranker。

> **Bi-Encoder 的核心工程价值不是做到最精确的相关性判断，而是把大规模语义搜索变成可以提前索引、在线快速计算的向量检索问题。**

---

## RRF 如何融合多个 Retriever 的结果？

Hybrid Retrieval 同时使用 BM25、Dense Retriever 等不同检索器时，会遇到一个直接问题：不同 Retriever 的原始 Score 通常不在同一个尺度上。

例如：

```text
BM25：      Doc A = 12.7
Dense：     Doc A = 0.81
```

`12.7` 与 `0.81` 没有自然可比性。可以先对 Score 做归一化再加权，但这会引入 Score Calibration 和权重调参问题。**Reciprocal Rank Fusion（RRF）** 的思路则是不比较原始分数，只比较各文档在每个 Retriever 中的排名。

RRF 的典型公式为：

\[
\operatorname{RRF}(d)=\sum_{r\in R}\frac{1}{k+\operatorname{rank}_r(d)}
\]

其中 `rank_r(d)` 表示文档 `d` 在 Retriever `r` 中的名次，`k` 是平滑常数。Elastic 当前 RRF 实现默认 `rank_constant=60`，但这个默认值属于具体实现，不应当成 RRF 理论的固定常数。

参考：[Elasticsearch：Reciprocal Rank Fusion](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)

例如：

```text
BM25：   A(1)  B(2)  C(3)
Dense：  C(1)  A(2)  D(3)
```

A 与 C 都在两个 Retriever 中得到较好排名，因此累积的 RRF Score 会较高；只在某一个 Retriever 中偶然排名靠前的结果，相对不容易支配最终排序。

### RRF 为什么适合 Hybrid Retrieval？

- **不要求 Score 可比**：BM25、cosine、稀疏神经检索等完全不同的打分尺度可以直接融合。
- **几乎不需要 Score Calibration**：相比线性加权，工程上更容易快速建立稳定 Baseline。
- **利用多检索器共识**：多个 Retriever 都认可的候选通常会被推到更靠前的位置。

### RRF 的局限

RRF 只看到 **Rank**，看不到原始 Score 的差距。例如下面两种情况在 RRF 眼里都只是“第一名、第二名”：

```text
Doc A = 0.99, Doc B = 0.50
Doc A = 0.51, Doc B = 0.50
```

因此它会丢失 Score Magnitude 信息。在拥有稳定业务数据、相关性标签和良好 Score Calibration 时，Weighted Fusion 或 Learning-to-Rank 有可能取得更好效果。

另外，RRF 本身并没有阅读 Query 与 Document 的内容，所以它虽然会重新排列候选，却不属于真正的语义 Reranker。它更准确的定位是：

> **Fusion：把多个 Retriever 的 Ranking 合并成一个统一 Candidate Ranking。**

因此经典结构通常是：

```text
BM25 ────┐
         ├→ RRF → Candidate Pool → Semantic Reranker → Top-K
Dense ───┘
```

Candidate Window 同样重要：如果某个 Retriever 只提供很小的 Top-K，正确文档在 Fusion 前就已经被截断，RRF 也无法恢复它。

---

## Reranker 为什么需要 Cross-Encoder，LLM Reranker 与 Late Interaction 又有什么取舍？

Retriever 的目标是从大规模 Corpus 中快速取得一个高 Recall 的 Candidate Pool；Reranker 则在候选规模已经缩小后，用更昂贵的相关性模型提高 **Precision**。

```text
百万级 Corpus
    ↓ Retriever
Top-50 / Top-100 / Top-200
    ↓ Reranker
Top-5 / Top-10
    ↓
Context Engineering
```

关键边界是：**Reranker 只能重新排序已经召回的 Candidate，无法挽救 Retriever 根本没有召回的文档。** 因此 Candidate Pool 的大小和第一阶段 Recall 是 Reranker 能否发挥价值的前提。

### Cross-Encoder：把 Query 与 Document 放进同一个 Transformer

Cross-Encoder 不像 Bi-Encoder 那样先分别产生可复用 Embedding，而是直接把一个 `(Query, Document)` Pair 同时输入 Transformer：

```text
[Query, Document]
       ↓
   Transformer
       ↓
 relevance score
```

这样 Self-Attention 可以直接建立 Query Token 与 Document Token 之间的交互，因此通常能比单向量相似度做更精细的相关性判断。Sentence Transformers 也把 Cross-Encoder 作为典型的第二阶段 Reranker：先用 Bi-Encoder / Lexical Search 召回候选，再对每个 `(query, candidate)` Pair 打分。

参考：[Sentence Transformers：Cross-Encoder](https://www.sbert.net/docs/cross_encoder/usage/usage.html) · [Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)

这里也要纠正一个容易混淆的术语：**Cross-Encoder 不是“Cross Embedding”模型。** 它通常输出的是 Query-Document 的 relevance score / logit，而不是一个可以单独保存并用于 ANN 的 Document Embedding。

Cross-Encoder 的主要优点是：

- Query 与 Document 可以做细粒度 Token-level interaction，Precision 通常高于单向量 Bi-Encoder。
- 很适合针对特定领域用 `(query, relevant document)` 数据做 Fine-tuning。
- 作为第二阶段只处理几十到几百个 Candidate，能够把高成本计算集中在最有希望的文档上。

主要缺点是：

- Document 表示不能像普通 Dense Embedding 一样脱离 Query 完全预计算。
- 每个 Query 都要重新计算每个 `(Query, Document)` Pair，因此无法经济地直接扫描百万级 Corpus。
- Candidate 数量、Document 长度和模型大小会直接影响在线延迟。

### LLM Reranker：把“相关性判断”交给通用 LLM

LLM Reranker 不一定依赖专门训练的 Cross-Encoder，而是把 Query、候选文档以及任务要求交给通用 LLM，让模型判断相关性或直接给出新的排序。LlamaIndex 等框架提供过 `LLMRerank` 和 RankGPT 一类实现，用较大的初始 Top-K 保持 Recall，再由 LLM 选择真正相关的 Node。

参考：[LlamaIndex：LLM Reranker](https://docs.llamaindex.ai/en/v0.10.20/module_guides/querying/node_postprocessors/node_postprocessors.html) · [RankGPT Reranker](https://docs.llamaindex.ai/en/v0.9.48/examples/node_postprocessor/rankGPT.html)

常见的 LLM Ranking 形式可以分成：

- **Pointwise**：对每个 `(Query, Document)` 独立打分。容易并行，但不同调用之间的分数校准和一致性可能较差。
- **Pairwise**：让模型比较 `Doc A` 与 `Doc B` 哪个更相关。相对判断直观，但 Candidate 较多时比较次数迅速增加。
- **Listwise**：一次给模型多个 Candidate，让它直接输出一个排列或 Top-N。能够利用候选之间的相对关系，但受 Context Window、输入顺序和候选数量限制；Candidate 很多时常需要分批或 sliding window。

LLM Reranker 的优势是能理解更复杂的任务语义，例如“这段证据是否真正回答问题”“是否满足某种业务条件”，并且可以通过 Prompt 快速加入领域规则而不一定需要重新训练专门的 Ranker。代价则是 **Token 成本、延迟、稳定性和可复现性**：候选越长、越多，成本越高；不同模型和 Prompt 也可能产生明显不同的 Ranking。

因此它更适合候选已经较少、单次答案价值高，或者相关性定义难以被普通 Cross-Encoder 覆盖的复杂场景，而不是所有在线 RAG 的默认精排器。

### Late Interaction：在单向量 Bi-Encoder 与 Cross-Encoder 之间折中

ColBERT 代表的 **Late Interaction** 路线不把整个 Query / Document 各自压成一个向量，而是保留 Token-level 的多向量表示。Query 和 Document 仍然可以独立编码，Document 表示可以离线预计算；直到打分阶段，才让两侧 Token 表示做细粒度交互。

ColBERT 经典的 MaxSim 思路可以概括为：对每个 Query Token，找到最相似的 Document Token，再把这些最大相似度累加：

\[
S(q,d)=\sum_i\max_j\operatorname{sim}(q_i,d_j)
\]

```text
Query → q1 q2 q3 ...
                 ↘
                   MaxSim / Late Interaction → score
                 ↗
Doc   → d1 d2 d3 ...
```

参考：[ColBERT](https://arxiv.org/abs/2004.12832) · [ColBERTv2](https://arxiv.org/abs/2112.01488)

它的核心折中是：

- 比单向量 Bi-Encoder 保留更多 Token-level 相关性信息，通常能进行更精细的匹配。
- 又不像 Cross-Encoder 那样必须对每个 Query-Document Pair 重新执行完整联合 Transformer，因此 Document 表示仍然可以提前计算和索引。

代价是一个 Document 不再只有一个向量，而会拥有一组 Token-level Vector，索引体积、存储成本和检索实现复杂度都会明显上升。ColBERTv2 等后续工作通过压缩等方式降低了这一空间成本。

**Late Interaction 并不只能做 Reranker。** ColBERT 既可以对已有 Candidate 做精细排序，也可以借助专门索引直接承担第一阶段 Retrieval。因此更准确的理解是：它是一种介于传统 single-vector Dense Retrieval 和 full Cross-Encoder interaction 之间的 Neural IR 架构。

### 三类精细相关性模型如何选择？

| 方法 | 表示 / 交互方式 | 文档能否预计算 | 典型成本 | 主要优势 | 主要局限 |
| --- | --- | --- | --- | --- | --- |
| **Cross-Encoder** | Query + Document 联合编码 | 不能完整预计算 Pair Score | 中高 | 精度高、成熟、易 Fine-tune | 每个 Pair 都要推理，难以全库扫描 |
| **LLM Reranker** | LLM 按指令 Pointwise / Pairwise / Listwise 判断 | 不能预计算任务相关 Ranking | 很高 | 能理解复杂意图和业务规则，Zero-shot 灵活 | Token / 延迟昂贵，稳定性与排序一致性较难治理 |
| **Late Interaction / ColBERT** | Query / Doc 独立编码为多向量，后续 Token-level 交互 | 可以 | 中等，但索引更重 | 比单向量更细粒度，同时保留较强检索效率 | 多向量索引占空间，基础设施更复杂 |

工程上没有必要把 Reranker 当成“越强越好”。应根据 **Candidate Pool 大小、延迟预算、领域数据、索引规模和最终 Precision 收益** 选择：

> **高吞吐在线问答通常优先使用专门 Cross-Encoder / Rerank Model；复杂且高价值的少量查询可以考虑 LLM Reranker；需要更细粒度召回但又不希望承担 Full Cross-Encoder 成本时，可以考虑 Late Interaction。**

---

## Hierarchical / Parent-Child RAG 在解决什么问题？

它解决的是 Chunking 中一个经典矛盾：

```text
Chunk 小
→ Embedding 主题更集中、搜索更精确
→ 但回答所需上下文可能不完整

Chunk 大
→ 上下文完整
→ 但一个向量混入多个主题，检索精度下降
```

Parent-Child RAG 将“搜索粒度”和“生成粒度”分开：

```text
Document
  ↓
Parent Section
  ├─ Child Chunk 1
  ├─ Child Chunk 2
  └─ Child Chunk 3

Query
  ↓
Search small Child Chunk
  ↓
Hit Child 2
  ↓
Return Child 2's Parent Section
  ↓
LLM
```

可以概括成：

> **小块负责找，大块负责读。**

进一步还可以形成多级 Hierarchy：

```text
Document
  ↓
Chapter
  ↓
Section
  ↓
Paragraph
  ↓
Chunk
```

检索可以从最细粒度开始，根据命中的子节点向 Parent 扩展，或者根据多个相邻 Child 的命中情况自动合并更大的 Parent。LlamaIndex 的 Recursive Retriever、Auto-Merging Retriever，以及 RAGFlow 当前的 Parent-Child Chunking 都体现了这类思路。

### 优点

- 同时兼顾检索精准度和上下文完整性。
- 对论文、手册、法规、技术文档等天然层级明显的资料特别有效。
- 能减少为了避免切断语义而机械增加大 Overlap 的需求。

### 局限

- Ingestion 必须正确保存父子关系和文档层级。
- Parent 太大时仍可能引入无关内容；Parent 太小又失去层级扩展意义。
- 对本身没有明显层级的短文本集合，收益可能有限。

---

## Agentic RAG 与固定 RAG Pipeline 有什么区别？

传统 RAG 的路径由开发者提前写死：

```text
Query → Retrieve → Rerank → Generate
```

Agentic RAG 则把 Retrieval 变成 Agent 可以动态调用和控制的能力：

```text
                       ┌→ Vector DB
                       ├→ BM25
User Query → Agent ────┼→ SQL
                       ├→ Knowledge Graph
                       └→ Web Search
                              ↓
                            Read
                              ↓
                        信息是否足够？
                         /        \
                       no          yes
                       ↓            ↓
                Rewrite / Decompose Answer
                       ↓
                   Retrieve Again
```

Agent 可以决定：

- 当前问题是否需要检索；
- 应该使用哪个数据源 / Retriever；
- 是否要 Query Rewrite、MQE 或问题分解；
- 一轮检索是否足够；
- 是否需要根据第一轮证据生成新的查询；
- 哪些证据值得进一步验证。

因此 Agentic RAG 的本质不是“换了一个更高级 Retriever”，而是：

> **把固定 Retrieval Pipeline 中的一部分控制权交给 Agentic Loop。**

### 优点

- 适合 Research、Multi-hop QA、异构数据源和问题路径无法预先写死的任务。
- 可以按 Query 动态选择 Vector、Keyword、SQL、Graph、Web 等不同工具。
- 可以通过“检索 → 阅读 → 发现缺口 → 再检索”处理需要多轮证据收集的问题。

### 局限

- LLM 调用次数和 Retrieval 次数增加，Token、延迟和费用更高。
- Agent 可能选错 Retriever、错误改写 Query、重复搜索或陷入循环。
- 需要 Runtime 层提供最大迭代次数、工具权限、停止条件、Trace 和评估机制，不能只靠 Prompt 约束。

所以 Agentic RAG 并不会淘汰固定 Pipeline。对于“一个知识库 + 一个明确 Query + 稳定 SLA”的在线问答，固定 **Hybrid Retrieve → Rerank** 往往更简单、便宜、可控；Agentic RAG 更适合检索路径本身需要推理的复杂任务。

相关主题：[[Agent#ReAct 执行循环为什么需要运行时约束？|ReAct 执行循环为什么需要运行时约束？]] · [[Agent框架]]。

---

相关主题：[[Agent]] · [[Memory]] · [[微调]]；方案选择见 [[对比问题#微调、RAG 与规则增强分别适合解决什么问题？|微调、RAG 与规则增强分别适合解决什么问题？]]。