import { useEffect, useState } from "react";
import { api } from "./api";
import type { Health } from "./types";
import ChatPanel from "./components/ChatPanel";
import EvalPanel from "./components/EvalPanel";
import { DatabaseIcon, LogoIcon } from "./components/icons";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    api
      .health()
      .then((h) => {
        setHealth(h);
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(refresh, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-title">
          <LogoIcon size={24} />
          WorldRAG 控制台
        </div>
        {health && (
          <div className="backend-tags">
            <span className="tag">{health.backends.embed}</span>
            <span className="tag">{health.backends.vector}</span>
            <span className="tag">{health.backends.llm}</span>
            <span className="tag tag--muted">
              <DatabaseIcon size={16} /> {health.chunks} chunks
            </span>
          </div>
        )}
      </header>
      {error && <div className="chat-turn chat-turn--error">API 连接失败：{error}</div>}
      <ChatPanel onError={setError} />
      <EvalPanel />
    </div>
  );
}
