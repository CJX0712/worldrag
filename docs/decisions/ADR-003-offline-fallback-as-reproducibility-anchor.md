# ADR-003: 离线兜底实现是"干净环境可复现"的支点

## Status: Accepted (2026-09-24)

## Background

"干净环境一键复现"如果依赖模型下载、外部服务或 API Key，就永远不可证。
同时存在一类高危缺陷：后端静默降级，测试全绿而生产是坏的（假成功）。

## Decision

1. 每个外部依赖（嵌入/向量库/LLM/重排）都有 Protocol + 零依赖离线实现：
   哈希 bigram 嵌入、内存余弦向量库、抽取式 mock LLM、passthrough 重排。
2. 默认配置即全离线，`python verify.py` 无网络无模型全绿；CI 不需要任何模型。
3. 反假成功三件套：生产后端实例暴露 `_error` 并在测试中断言为 None；
   工厂把每次降级记入 degradations 报告并经 `/api/degradations` 暴露；
   评测永远在全新 pipeline/索引上运行（与生产索引双向隔离）。

## Consequences

- 正面：本机 verify 与 GitHub Actions 干净 runner 构成两份独立复现证据
- 正面：降级永远可见，不可能静默
- 负面：离线实现的检索质量弱于生产实现（可接受——它服务的是验证不是质量）

## Related ADRs

ADR-001, ADR-002, ADR-004
