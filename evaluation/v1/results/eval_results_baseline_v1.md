# Workspace Eval Baseline v1
Based on post-v0.1.0 development version
具体eval cases内容详见evaluation/eval_cases.json

## Results

### Conversation Context
5/5

全部顺利通过，表现符合预期

### RAG
5/5
Initial result：3/5

一开始R02、03未通过，使用test_rag_local脚本文件retrieval查看数据流并定位问题根源，发现RAG的相关度分数阈值筛选逻辑不合适，改为当最高分小于阈值时，取最高分的chunk以供参考，随后RAG的eval cases全部通过，表现符合预期

### Instruction Following
5/5

全部顺利通过，表现符合预期


## Current Baseline

Conversation Context: 5 / 5

RAG:                  5 / 5

Instruction Following:5 / 5

Total:               15 / 15

## Known Limitations

- 当前Eval数据集规模较小，主要用于基础能力验证与Regression Test。
- RAG低相似度结果仍存在错误证据进入Context的潜在风险。
- 当前结果不足以证明不同模型之间的整体优劣