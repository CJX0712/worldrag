# WorldRAG

端到端混合检索 RAG 知识库问答系统。双路召回（BM25 + 向量）→ RRF 融合 → 可选交叉编码器重排 → LLM 生成 → 引用溯源，全链路可离线验证、可量化评测、可在干净环境一键复现。

作者：晨星 · 协议：MIT

## 特性

- **混合检索**：CJK 单字+双字 BM25（零依赖 tokenizer）与稠密向量检索双路召回，RRF 融合
- **重排护栏**：交叉编码器分数按权重融入 RRF 排序，不单独决定最终顺序（ADR-002）
- **生产/离线双模**：每个外部依赖都是 Protocol + 可注入实现；离线兜底（哈希嵌入 / 内存余弦 / 抽取式 mock LLM）让 `verify` 在无网络、无 Key、无模型下全绿
- **可量化评测**：独立索引评测 recall@k / MRR / 关键词命中率，评测与生产索引严格隔离
- **API + CLI + React 控制台**：FastAPI 契约（OpenAPI）、命令行、Vite+React 前端
- **CI 实证**：GitHub Actions 干净 runner 跑同一套 `verify`，证明与开发机无关

## 快速开始（5 分钟，零模型零联网）

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # Linux/macOS
pip install -r requirements-dev.txt

python verify.py          # pytest + emoji 门禁 + E2E 冒烟，期望全绿
```

启动 API + 内置前端：

```bash
# 前端（可选，先构建一次）
cd frontend && npm ci && npm run build && cd ..

# 启动服务（离线模式，无需任何模型）
set PYTHONPATH=src
python -m uvicorn worldrag.api.app:app --port 8000
# 打开 http://localhost:8000
```

## 生产模式（Ollama 本地模型）

```bash
# 安装并启动 Ollama，拉取模型
ollama pull bge-m3
ollama pull qwen2.5:1.5b-instruct
ollama serve

# Windows
set WORLDRAG_EMBED_BACKEND=ollama
set WORLDRAG_VECTOR_BACKEND=faiss
set WORLDRAG_LLM_BACKEND=ollama
set PYTHONPATH=src
python -m uvicorn worldrag.api.app:app --port 8000
```

本机实测（bge-m3 + faiss + qwen2.5:1.5b，CPU）：**recall@k=1.0 / MRR=1.0 / 关键词命中率=1.0（8/8 查询）**，零后端降级，8 条查询端到端 68s。

可选 ONNX 交叉编码器重排（ModelScope 下载，无需 HuggingFace）：

```bash
python scripts/download_models.py
set WORLDRAG_RERANK_BACKEND=onnx
```

## CLI

```bash
set PYTHONPATH=src
python -m worldrag.cli ingest data/samples          # 摄取目录（txt/md/pdf）
python -m worldrag.cli query "退款审核要多久？" --corpus data/samples
python -m worldrag.cli evaluate                     # 离线评测（独立索引）
python -m worldrag.cli serve --port 8000
```

## API

| Method | Path | 说明 |
|--------|------|------|
| GET | /api/health | 健康检查 + 活跃后端清单 |
| POST | /api/ingest | 摄取文本或文件路径（txt/md/pdf） |
| POST | /api/query | 检索问答，返回答案 + 引用 |
| POST | /api/evaluate | 在独立索引上跑评测指标 |
| GET | /api/degradations | 后端降级报告（应为空） |

完整契约见 `docs/openapi.yaml`。

## 配置（环境变量）

| 变量 | 默认 | 说明 |
|------|------|------|
| WORLDRAG_EMBED_BACKEND | hash | hash / ollama / fastembed |
| WORLDRAG_VECTOR_BACKEND | memory | memory / faiss |
| WORLDRAG_LLM_BACKEND | mock | mock / ollama |
| WORLDRAG_RERANK_BACKEND | none | none / onnx |
| WORLDRAG_RERANK_WEIGHT | 0.4 | 重排分对最终序的影响权重上限 |
| WORLDRAG_OLLAMA_EMBED_MODEL | bge-m3 | Ollama 嵌入模型 |
| WORLDRAG_OLLAMA_LLM_MODEL | qwen2.5:1.5b-instruct | Ollama 生成模型 |
| WORLDRAG_OLLAMA_NUM_THREAD | 4 | CPU 推理线程（2-4 为最优，瓶颈在内存带宽） |
| WORLDRAG_CHUNK_SIZE / _OVERLAP | 500 / 60 | 分块参数 |

## 文档

- `ARCHITECTURE.md` — 模块划分与调用关系
- `docs/SPEC.md` — 规格契约（范围/API/验收标准）
- `docs/decisions/` — ADR 架构决策记录
- `scripts/run_prod_eval.py` — 生产路径自包含评测（自动拉起 Ollama）

## 复现保证

- `requirements.lock.txt` 由干净 venv 实际安装后 freeze 生成（Linux/Windows 均可装，已剔除 Windows-only 包）
- 前端 `package-lock.json` + `npm ci`
- GitHub Actions：后端 `python verify.py`（pytest + 门禁 + E2E）与前端 `npm ci && npm run build` 双流水线
