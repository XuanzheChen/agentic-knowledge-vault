from pathlib import Path
import re

ROOT = Path('.')
PRE = ROOT / 'LLM' / '预训练' / '预训练.md'
text = PRE.read_text(encoding='utf-8')

PAT = re.compile(r'\n---\n\n## (.*?)\n(.*?)(?=\n---\n\n## |\Z)', re.S)
sections = {m.group(1): '## ' + m.group(1) + '\n' + m.group(2).rstrip() for m in PAT.finditer(text)}

groups = {
    '预训练数据': [
        '现代 LLM 预训练的数据是什么样的？',
        '预训练数据为什么要做安全过滤？',
        '预训练数据为什么要做分类？',
    ],
    '训练目标': [
        '主流的大模型预训练算法有什么？',
        '现代 LLM 预训练常见的辅助目标有哪些？',
        'MTP 怎么做？',
        'FIM 在训练时，将前缀和后缀作为上下文输入，会打上标注吗？实现的是什么样的能力？',
    ],
    '激活函数与FFN': [
        'ReLU、GELU 与 SwiGLU 在数学上有什么区别？',
        '如何理解 Gated MLP？SwiGLU 与 GEGLU 是什么关系？',
    ],
    '归一化': [
        'LayerNorm 与 RMSNorm 有什么区别？为什么现代 LLM 大量采用 RMSNorm？',
        '为什么现代 LLM 普遍从 Post-Norm 转向 Pre-Norm？',
        'QK-Norm 是什么？它为什么能提高训练稳定性？',
    ],
    'MoE': [
        'MoE 怎么做？',
        'Auxiliary-Loss-Free 的 Bias 是怎么帮助 specialization？',
    ],
}
attention_heads = [
    'MHA 的基本原理是什么？',
    'GQA 如何在 MHA 上降低 KV Cache？',
    'MLA 的基本原理是什么？',
    '为什么注意力结构会从 MHA 发展到 GQA，再到 MLA？',
    'MLA 中的低秩降维是怎么做的？降维之后又是怎么恢复的？',
    '为什么 MLA 里的 RoPE 要换成 Decoupled RoPE？',
]
residual_heads = ['Kimi K3 的残差结构与传统残差有什么不同？它起什么作用？']
remaining = [
    '什么是预训练？',
    '现代 LLM 预训练的模型架构是什么样的？',
    '现代 LLM 的预训练系统是什么样的？',
]
required = remaining + attention_heads + residual_heads + sum(groups.values(), [])
missing = [h for h in required if h not in sections]
if missing:
    raise RuntimeError(f'预训练中缺少预期标题: {missing}')

intros = {
    '预训练数据': '围绕预训练语料的组成、清洗、过滤、分类与数据配比整理 Q&A。',
    '训练目标': '围绕预训练的语言建模目标，以及 MTP、FIM 等辅助训练目标整理 Q&A。',
    '激活函数与FFN': '围绕 Transformer FFN 中的激活函数、门控 MLP 与 SwiGLU / GEGLU 等结构整理 Q&A。',
    '归一化': '围绕 LayerNorm、RMSNorm、Pre-Norm / Post-Norm 与 QK-Norm 等归一化机制整理 Q&A。',
    'MoE': '围绕 Mixture of Experts 的路由、专家 specialization 与负载均衡机制整理 Q&A。',
}

def make_leaf_tree(title, heads):
    q = '\n'.join(f'- [[{title}#{h}|{h}]]' for h in heads)
    body = '\n\n---\n\n'.join(sections[h] for h in heads)
    out = f'# {title}\n\n[[预训练|返回上级：预训练]] · [[main|返回知识主干]]\n\n{intros[title]}\n\n## 问题目录\n\n{q}\n\n---\n\n{body}\n'
    return out.replace('../../assets/', '../../../assets/')

for title, heads in groups.items():
    d = ROOT / 'LLM' / '预训练' / title
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{title}.md').write_text(make_leaf_tree(title, heads), encoding='utf-8')

# Move and enrich Attention.
old_att = ROOT / 'LLM' / '注意力机制' / '注意力机制.md'
att = old_att.read_text(encoding='utf-8')
att_sections = {m.group(1): '## ' + m.group(1) + '\n' + m.group(2).rstrip() for m in PAT.finditer(att)}
att_existing = list(att_sections)
new_att_dir = ROOT / 'LLM' / '预训练' / '注意力机制'
new_att_dir.mkdir(parents=True, exist_ok=True)
old_att.unlink()
(ROOT / 'LLM' / '注意力机制').rmdir()
att_heads = attention_heads + att_existing
att_q = '\n'.join(f'- [[注意力机制#{h}|{h}]]' for h in att_heads)
att_body = '\n\n---\n\n'.join([sections[h] for h in attention_heads] + [att_sections[h] for h in att_existing])
new_att = f'''# 注意力机制

[[预训练|返回上级：预训练]] · [[main|返回知识主干]] · [[残差连接]]

围绕现代 LLM 中 Attention / Linear Attention 的核心机制与演进整理。MHA、GQA、MLA 与 KDA 等注意力结构统一归档在这里。

## 问题目录

{att_q}

---

{att_body}
'''.replace('../../assets/', '../../../assets/')
(new_att_dir / '注意力机制.md').write_text(new_att, encoding='utf-8')

# Move and enrich Residual.
old_res = ROOT / 'LLM' / '残差连接' / '残差连接.md'
res = old_res.read_text(encoding='utf-8')
res_sections = {m.group(1): '## ' + m.group(1) + '\n' + m.group(2).rstrip() for m in PAT.finditer(res)}
res_existing = list(res_sections)
new_res_dir = ROOT / 'LLM' / '预训练' / '残差连接'
new_res_dir.mkdir(parents=True, exist_ok=True)
old_res.unlink()
(ROOT / 'LLM' / '残差连接').rmdir()
res_heads = residual_heads + res_existing
res_q = '\n'.join(f'- [[残差连接#{h}|{h}]]' for h in res_heads)
res_body = '\n\n---\n\n'.join([sections[h] for h in residual_heads] + [res_sections[h] for h in res_existing])
new_res = f'''# 残差连接

[[预训练|返回上级：预训练]] · [[main|返回知识主干]] · [[注意力机制]]

围绕现代 LLM 中 residual stream 的信息传播、Hyper-Connections、mHC、Qwen Gated Residual 与 Kimi AttnRes 整理。

## 问题目录

{res_q}

---

{res_body}
'''.replace('../../assets/', '../../../assets/')
(new_res_dir / '残差连接.md').write_text(new_res, encoding='utf-8')

# Parent pretraining keeps overview leaves and direct-child navigation only.
child_rows = [
    ('预训练数据', '预训练语料的组成、过滤、分类与数据配比'),
    ('训练目标', 'NTP 及 MTP、FIM 等辅助训练目标'),
    ('激活函数与FFN', '激活函数、Gated MLP、SwiGLU / GEGLU'),
    ('归一化', 'LayerNorm、RMSNorm、Pre-Norm 与 QK-Norm'),
    ('MoE', '专家路由、specialization 与负载均衡'),
    ('RoPE', '旋转位置编码、长上下文扩展与频谱设计'),
    ('注意力机制', 'MHA、GQA、MLA、KDA 等注意力结构'),
    ('残差连接', 'Residual、HC、mHC、Gated Residual 与 AttnRes'),
]
table = '\n'.join(f'| [[{n}]] | {d} |' for n, d in child_rows)
q = '\n'.join(f'- [[预训练#{h}|{h}]]' for h in remaining)
body = '\n\n---\n\n'.join(sections[h] for h in remaining)
PRE.write_text(f'''# 预训练

[[LLM|返回上级：LLM]] · [[main|返回知识主干]]

围绕大语言模型预训练阶段的目标、数据、模型结构与训练系统整理 Q&A；具体机制按稳定概念簇下沉到子树。

## 子树

| 子树 | 内容 |
| --- | --- |
{table}

## 问题目录

{q}

---

{body}
''', encoding='utf-8')

# Fix the Agent -> Context ambiguity and all other bare Context links.
for p in ROOT.rglob('*.md'):
    s = p.read_text(encoding='utf-8')
    s = s.replace('[[context|', '[[Agent/Context/context|')
    s = s.replace('[[context#', '[[Agent/Context/context#')
    p.write_text(s, encoding='utf-8')

# LLM now has only its direct children.
llm = ROOT / 'LLM' / 'LLM.md'
l = llm.read_text(encoding='utf-8')
l = re.sub(r'\| \[\[注意力机制\]\] \|.*?\n', '', l)
l = re.sub(r'\| \[\[残差连接\]\] \|.*?\n', '', l)
llm.write_text(l, encoding='utf-8')

# Main hierarchy mirrors the new physical tree.
main = ROOT / 'main.md'
m = main.read_text(encoding='utf-8')
old = '''  - [预训练](LLM/预训练/预训练.md)\n    - [RoPE](LLM/预训练/RoPE/RoPE.md)\n  - [中训练](LLM/中训练/中训练.md)\n  - [后训练](LLM/后训练/后训练.md)\n    - [微调](LLM/后训练/微调/微调.md)\n  - [注意力机制](LLM/注意力机制/注意力机制.md)\n  - [残差连接](LLM/残差连接/残差连接.md)\n  - [部署](LLM/部署/部署.md)'''
new = '''  - [预训练](LLM/预训练/预训练.md)\n    - [预训练数据](LLM/预训练/预训练数据/预训练数据.md)\n    - [训练目标](LLM/预训练/训练目标/训练目标.md)\n    - [激活函数与 FFN](LLM/预训练/激活函数与FFN/激活函数与FFN.md)\n    - [归一化](LLM/预训练/归一化/归一化.md)\n    - [MoE](LLM/预训练/MoE/MoE.md)\n    - [RoPE](LLM/预训练/RoPE/RoPE.md)\n    - [注意力机制](LLM/预训练/注意力机制/注意力机制.md)\n    - [残差连接](LLM/预训练/残差连接/残差连接.md)\n  - [中训练](LLM/中训练/中训练.md)\n  - [后训练](LLM/后训练/后训练.md)\n    - [微调](LLM/后训练/微调/微调.md)\n  - [部署](LLM/部署/部署.md)'''
if old not in m:
    raise RuntimeError('main.md 中未找到旧 LLM 层级')
main.write_text(m.replace(old, new), encoding='utf-8')

# Rewrite cross-links for leaves moved from pretraining.
target = {}
for subtree, hs in groups.items():
    for h in hs:
        target[h] = subtree
for h in attention_heads:
    target[h] = '注意力机制'
for h in residual_heads:
    target[h] = '残差连接'
for p in ROOT.rglob('*.md'):
    s = p.read_text(encoding='utf-8')
    for h, t in target.items():
        s = s.replace(f'[[预训练#{h}|', f'[[{t}#{h}|')
        s = s.replace(f'[[预训练#{h}]]', f'[[{t}#{h}]]')
    p.write_text(s, encoding='utf-8')

# Prevent the Context bug from recurring.
ag = ROOT / 'AGENTS.md'
a = ag.read_text(encoding='utf-8')
anchor = '- 每个 Tree 的 Markdown 顶部都必须提供向上导航。一级 Tree 的直接上级就是 `main.md`，因此只保留一个“返回知识主干”链接；二级及更深 Tree 必须同时提供“返回上级 Tree”和“返回知识主干”两个入口。可以在其后保留少量有阅读价值的横向关联链接，但不能替代这两个向上入口。\n'
rule = '- Tree 的结构导航应使用能够唯一定位目标的链接；当目录名与文件名相近、存在大小写差异或裸文件名可能产生歧义时，使用从 vault 根目录出发的明确路径，不依赖 Obsidian 的模糊解析。\n'
if rule not in a:
    if anchor not in a:
        raise RuntimeError('AGENTS.md 中未找到导航规则锚点')
    a = a.replace(anchor, anchor + rule, 1)
ag.write_text(a, encoding='utf-8')

# Invariants.
assert not (ROOT / 'LLM' / '注意力机制').exists()
assert not (ROOT / 'LLM' / '残差连接').exists()
assert (ROOT / 'LLM' / '预训练' / '注意力机制' / '注意力机制.md').exists()
assert (ROOT / 'LLM' / '预训练' / '残差连接' / '残差连接.md').exists()
all_md = '\n'.join(p.read_text(encoding='utf-8') for p in ROOT.rglob('*.md'))
assert '[[context|' not in all_md and '[[context#' not in all_md
for h in target:
    assert f'[[预训练#{h}' not in all_md, h

# Remove migration-only files before commit.
(ROOT / '.github' / 'workflows' / 'rewrite-main-backlinks.yml').unlink(missing_ok=True)
(ROOT / '.github' / 'migrate_pretraining.py').unlink(missing_ok=True)
