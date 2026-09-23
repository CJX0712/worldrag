# ADR-001: Ollama 作为生产嵌入与生成后端

## Status: Accepted (2026-09-24)

## Background

目标环境为 Windows + CPU，HuggingFace 不可达，llama-cpp-python 无官方 win 轮子。
需要零编译、免模型下载（模型已在本地）的生产级嵌入与生成方案。

## Decision

嵌入用 Ollama `bge-m3`（/api/embed），生成用 Ollama `qwen2.5:1.5b-instruct`（/api/chat），
均通过本地 HTTP 调用。HTTP 客户端必须 `trust_env=False`，避免本机 SOCKS/HTTP 代理
把 localhost 流量转发导致连接重置（实测 WinError 10054）。

## Consequences

- 正面：零编译安装；模型本地已有；中英文嵌入质量一流（bge-m3）
- 正面：CPU 推理线程锁定 4（num_thread），避开内存带宽瓶颈
- 负面：依赖 Ollama 进程存活 → 通过 degradation 报告 + 离线兜底对冲
- 实测：生产路径评测 recall@k=1.0 / MRR=1.0（8/8），零降级

## Related ADRs

ADR-003（离线兜底是复现支点）
