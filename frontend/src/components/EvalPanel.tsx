import { useState } from "react";
import { api } from "../api";
import type { EvalResponse } from "../types";
import { ChartIcon } from "./icons";

const METRIC_LABELS: Array<[keyof EvalResponse["metrics"], string]> = [
  ["recall_at_k", "Recall@k"],
  ["mrr", "MRR"],
  ["keyword_hit_rate", "关键词命中率"],
  ["queries", "评测问题数"],
  ["chunks", "索引块数"],
];

export default function EvalPanel() {
  const [result, setResult] = useState<EvalResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      setResult(await api.evaluate());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel__header">
        <span>离线评测</span>
        <button className="btn btn--ghost" onClick={run} disabled={running}>
          <ChartIcon size={16} />
          {running ? "评测中…" : "运行评测"}
        </button>
      </div>
      <div className="panel__body">
        {error && <div className="chat-turn chat-turn--error">{error}</div>}
        {!result && !error && (
          <div className="empty-hint">点击"运行评测"，在独立索引上计算检索与生成质量指标</div>
        )}
        {result && (
          <>
            <div className="metric-grid">
              {METRIC_LABELS.map(([key, label]) => (
                <div className="metric-card" key={key}>
                  <div className="metric-card__value">{result.metrics[key]}</div>
                  <div className="metric-card__label">{label}</div>
                </div>
              ))}
            </div>
            <table className="eval-table">
              <thead>
                <tr>
                  <th>问题</th>
                  <th>命中</th>
                  <th>排名</th>
                  <th>关键词</th>
                </tr>
              </thead>
              <tbody>
                {result.per_query.map((row) => (
                  <tr key={row.query}>
                    <td>{row.query}</td>
                    <td>
                      <span className={`status-dot ${row.hit ? "status-dot--ok" : "status-dot--bad"}`} />
                      {row.hit ? "命中" : "未命中"}
                    </td>
                    <td>{row.rank ?? "-"}</td>
                    <td>{row.keyword_hit ? "通过" : "缺失"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </section>
  );
}
