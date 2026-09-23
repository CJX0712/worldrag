# Spec - WorldRAG v1.0.0

> 生成日期：2026-09-24
> 状态：已确认（唯一交互点已完成）
> 作者：晨星

## 1. 产品定义

- **一句话描述**：端到端混合检索 RAG 知识库问答系统，检索→重排→生成→引用全链路可离线验证、可量化评测。
- **目标用户**：需要在自有文档上构建可信问答能力的开发者与小团队（CPU 可跑）。
- **核心问题**：通用检索方案对中文支持弱、验证依赖外部服务、不可复现。

## 2. MVP 范围（锁定）

| 优先级 | 功能 | 验收标准摘要 |
|--------|------|-------------|
| P0 | 文档摄取（txt/md/pdf） | 多格式解析、确定性分块、多分块路径被测试覆盖 |
| P0 | 混合检索 | BM25 + 向量双路召回，RRF 融合 |
| P0 | 引用溯源 | 每条答案附 chunk 级引用（doc_id/chunk_id/score/snippet） |
| P0 | 离线全链路 | 无网络无模型下 verify 全绿 |
| P0 | 评测模块 | recall@k / MRR / 关键词命中率，独立索引 |
| P0 | REST API | /health /ingest /query /evaluate，OpenAPI 契约 |
| P1 | React 控制台 | 问答 + 引用展示 + 评测仪表盘 |
| P1 | ONNX 重排 | 可选，加权融合不独裁 |
| P1 | Ollama 生产后端 | bge-m3 嵌入 + 本地 LLM 生成 |

## 3. 明确不做（Out-of-Scope）

| 不做的功能 | 原因 | 何时考虑 |
|------------|------|----------|
| 用户认证/多租户 | MVP 单机知识库，认证属部署层 | v2.0 |
| 分布式向量库（Qdrant/Milvus） | 增加部署复杂度，faiss 已覆盖 MVP 规模 | 数据量 > 100 万 chunk |
| GPU 推理 | 目标环境为 CPU | 有 GPU 需求时 |
| 流式输出（SSE） | 契约复杂度，MVP 阶段 ROI 不足 | v1.1 |
| 文档增量更新/删除 API | 需要持久化层设计 | v2.0 |

## 4. 技术架构（锁定，版本锚定）

| 层 | 技术 | 实际版本 | 锁定原因 |
|----|------|----------|----------|
| 语言 | Python | 3.13.12 | 全部依赖有 win_amd64 轮子，零编译 |
| API | FastAPI | 0.141.1 | OpenAPI 自动生成 + pydantic 校验 |
| 向量 | faiss-cpu | 1.15.0 | CPU 上最成熟 ANN，win 轮子可用 |
| 稀疏 | 内置 BM25（可选 rank-bm25 0.2.2） | - | ADR-004：rank_bm25 小语料负 idf 缺陷 |
| 嵌入(生产) | Ollama bge-m3 | ollama 0.34.2 | 本地模型，免 HF 下载 |
| 嵌入(兜底) | 哈希 bigram（自研 20 行） | - | 零依赖离线验证支点 |
| 重排 | onnxruntime 1.30.0 + tokenizers 0.23.2 | 已锁定 | bge-reranker-v2-m3，ModelScope 下载 |
| LLM(生产) | Ollama qwen2.5:1.5b-instruct | - | CPU 可跑，线程锁 4 |
| 前端 | React 18.3 + Vite 5.4 + TS 5.6 | lockfile 锁定 | 工程化控制台 |
| 测试 | pytest 8.4.2 | - | --basetemp 防沙箱假失败 |

## 5. API 端点清单（锁定）

| Method | Path | 功能 | 请求体 | 响应 | 错误流 |
|--------|------|------|--------|------|--------|
| GET | /api/health | 健康+后端清单 | - | {status, chunks, backends} | - |
| POST | /api/ingest | 摄取 | {texts[], paths[]} | {ingested_chunks, total_chunks} | 400 空请求/坏路径 |
| POST | /api/query | 问答 | {query} | {answer, citations, backends} | 409 空库 / 422 空串 / 502 生成失败 |
| POST | /api/evaluate | 评测 | - | {metrics, backends, per_query} | - |
| GET | /api/degradations | 降级报告 | - | {degradations} | - |

契约：`docs/openapi.yaml`。

## 6. 数据模型

无持久化数据库（MVP 内存索引）。核心实体：

| 实体 | 字段 |
|------|------|
| Chunk | doc_id, chunk_id(`{doc}#{seq:04d}`), text, metadata |
| SearchResult | chunk, score, source(vector/bm25/fusion/rerank) |
| Answer | query, answer, citations[], contexts[], backends |

## 7. 页面清单（前端）

| 页面 | 路由 | 核心组件 | 对应 API |
|------|------|----------|----------|
| 控制台（单页） | / | ChatPanel / CitationCard / EvalPanel | /api/query, /api/evaluate, /api/health |

## 8. 设计 Token（锁定）

- 主色：`#4F46E5`（纯色，禁止紫→粉渐变）
- 背景：`#F8FAFC`，表面：`#FFFFFF`，边框：`#E2E8F0`
- 字体：Inter + Noto Sans SC；等宽：JetBrains Mono/Consolas
- 图标：项目内联 SVG 集（1.8px 描边，16/20/24px），禁止 emoji 功能图标
- 全部颜色经 CSS 变量引用，禁止硬编码

## 9. 验收标准（EARS，锁定）

| 编号 | 标准 | 验证 |
|------|------|------|
| AC-01 | When 空库时调用 /query，系统必须返回 409 | test_api / e2e |
| AC-02 | If 摄取请求 texts 与 paths 均空，系统必须返回 400 | test_api / e2e |
| AC-03 | While 摄取超过分块阈值的文档，系统必须产生 >1 个 chunk | test_pipeline |
| AC-04 | When 查询中文问题，系统必须返回含 doc_id 引用的答案 | test_pipeline / e2e |
| AC-05 | While 评测运行，系统必须在全新索引上执行且指标不受外部索引污染影响 | test_evaluate（逐位断言） |
| AC-06 | If 生产后端不可用，系统必须降级且在 degradations 中可见 | factory report |
| AC-07 | When 真实后端（faiss）启用，_error 必须为 None | test_vector |
| AC-08 | 全仓 emoji 门禁扫描必须零违规 | scripts/scan_emoji.py |
| AC-09 | `python verify.py` 在无网络环境必须全绿 | CI + 本机 |
| AC-10 | 生产路径（Ollama+faiss）评测 recall@k 必须 ≥ 0.75 | scripts/run_prod_eval.py（实测 1.0） |

## 10. 边界与约束

- 内存索引，进程重启即清空（MVP 接受）
- 单文档 ≤ 10MB 建议值；chunk 默认 500 字 / 重叠 60 字
- 生产 LLM 需本机 Ollama；无 Ollama 时自动降级 mock 并上报
- 模型文件不进仓库（.gitignore）

## 11. 内嵌已知坑（来自项目记忆）

| 坑 | 根因 | 修法 |
|----|------|------|
| rank_bm25 小语料排序反转 | 负 idf 被 epsilon 地板规则扭曲 | 内置非负 idf BM25 为默认（ADR-004） |
| httpx 访问本地 Ollama 被代理重置 | trust_env 默认 true，走 SOCKS 代理 | Client(trust_env=False) |
| 重排器直接定序压垮中文 top-1 | 英文 reranker 在中文查询上偏弱 | RRF 主导 + 权重融合（ADR-002） |
| pytest 假失败（无汇总行） | 沙箱拦截系统临时目录批量删除 | --basetemp 到仓库内 |
| CPU 推理慢 4 倍 | 默认线程=cpu_count-1，瓶颈在内存带宽 | num_thread 锁 2-4 |
| 评测"假成功" | 复用生产索引/静默降级 | 独立索引 + _error 断言 + degradations 上报 |

## 12. 端到端验证步骤

```bash
pip install -r requirements-dev.txt
python verify.py
# 期望: VERIFY_SUMMARY {"ok": true, ...}
# 生产路径（需本机 Ollama）:
python scripts/run_prod_eval.py
# 期望: recall_at_k >= 0.75, degradations == {}
```

## 13. 变更记录

| 日期 | 变更 | 原因 |
|------|------|------|
| 2026-09-24 | v1.0.0 初始锁定 | - |
