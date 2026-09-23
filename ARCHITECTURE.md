# WorldRAG 系统架构

作者：晨星

## 设计原则

1. **单一职责**：每个模块只做一件事，可独立实例化、独立测试。
2. **依赖倒置**：模块间只依赖 `worldrag.protocols` 中的 Protocol，实现由工厂在运行时注入。
3. **离线可验证**：每个外部依赖都有零依赖兜底实现，验证链路不依赖网络/模型/密钥。
4. **失败不静默**：任何后端降级都记录进 `degradations` 报告并经 API 暴露。

## 模块视图

```
                        ┌─────────────────────────┐
                        │  frontend (React + Vite) │
                        └────────────┬────────────┘
                                     │ HTTP /api
┌─────────────┐  CLI   ┌─────────────▼────────────┐
│ worldrag.cli├───────►│  api.routes / api.app     │  app 只装配，零业务
└──────┬──────┘        └─────────────┬────────────┘
       │                             │ 注入
       │                    ┌────────▼─────────┐
       │                    │ agent.pipeline    │  RAGPipeline：编排
       │                    │ retrieve→rerank→  │
       │                    │ generate→cite     │
       │                    └───┬───┬───┬───┬───┘
       │                        │   │   │   │
       │        ┌───────────────┘   │   │   └──────────────┐
       │        ▼                   ▼   ▼                  ▼
       │  embed.*            vector.*  sparse.bm25    llm.*
       │  hash_embed(兜底)    memory    tokenizer      mock(兜底)
       │  ollama_embed(生产)  faiss_impl              ollama(生产)
       │        │                   │
       │        └───────┬───────────┘
       │                ▼
       │        rerank.fusion (RRF + blend)  ← rerank.base (passthrough / onnx)
       │
       ▼
 ingest.loaders (.txt/.md/.pdf) → ingest.chunker (确定性分块)

 evaluate.runner —— 始终在全新 pipeline 上评测（与生产索引隔离）
```

## 关键调用关系

| 调用方 | 被调方 | 接口 |
|--------|--------|------|
| api.routes / cli | RAGPipeline | `ingest_documents / query` |
| RAGPipeline | Embedder | `embed(texts) -> vectors` |
| RAGPipeline | VectorStore | `add / search(qv, k)` |
| RAGPipeline | SparseIndex | `add / search(query, k)` |
| RAGPipeline | Reranker | `rerank(query, fused, k)` |
| RAGPipeline | LLM | `generate(prompt)` |
| evaluate.runner | factory.build_pipeline | 每次新建实例 |

## 数据流（查询）

1. `embed([query])` → 向量召回 top-10（向量库）
2. `bm25.search(query)` → 词项召回 top-10（CJK 单双字切分）
3. `rrf_fuse` 两路合并，取 top-20 候选
4. Reranker：passthrough（离线）或 ONNX 交叉编码器按 `final = 0.6*norm(RRF) + 0.4*norm(CE)` 重排，取 top-5
5. 组装带编号的上下文 prompt → LLM 生成 → 答案 + `[n]` 引用 + 溯源元数据

## 为什么这样设计（要点）

- **RRF 而非分数加权融合**：BM25 分与余弦相似度量纲不可比，倒数排名免校准。
- **重排不独裁**：交叉编码器若在查询语言上偏弱，直接采信其排序会压掉正确答案（实测中文 top-1 11/12 → 崩盘）。加权融合把影响限制在权重内（ADR-002）。
- **评测独立索引**：复用生产索引会导致"指标全错但程序不报错"（黄金语料被运行期数据稀释）。每次评测新建 pipeline 是硬规则。
- **CPU 线程锁定**：小量化模型在 CPU 上的瓶颈是内存带宽不是算力，线程数 2-4 最优，默认 cpu_count-1 会慢约 4 倍。
