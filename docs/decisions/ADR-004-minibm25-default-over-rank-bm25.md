# ADR-004: 默认采用内置非负 idf BM25，rank_bm25 仅作基准选项

## Status: Accepted (2026-09-24)

## Background

开发中实测：rank_bm25 0.2.2 的 BM25Okapi 在小语料上 idf 为负，
其 epsilon 地板规则（negative idf := epsilon * average_idf）会扭曲排序。
复现：2 文档索引查询"六十次"，得分 [-0.366, -0.349]——正确文档垫底，
且全部被"score > 0"过滤，返回空结果。

## Decision

默认引擎为内置 Robertson & Zaragoza (2009) 实现，idf 取
`ln(1 + (N-n+0.5)/(n+0.5))`，恒非负，小语料排序正确。
rank_bm25 保留为可选（WORLDRAG_BM25_ENGINE=rank_bm25），仅建议在大语料
基准对比时使用。该决策由 tests/test_bm25.py 固化。

## Consequences

- 正面：小语料（MVP 常见场景）排序正确、零分结果不泄漏
- 正面：少一个行为不可控的依赖路径
- 负面：内置实现未做大规模性能优化（MVP 规模无影响）

## Related ADRs

ADR-003
