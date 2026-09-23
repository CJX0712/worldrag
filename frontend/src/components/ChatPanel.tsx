import { useState } from "react";
import { api } from "../api";
import type { ChatTurn } from "../types";
import CitationCard from "./CitationCard";
import { SendIcon } from "./icons";

const SUGGESTED = [
  "年度套餐购买后多少天内可以全额退款？",
  "免费版API每分钟可以请求多少次？",
  "私有化部署最低需要多少内存？",
];

export default function ChatPanel({ onError }: { onError: (msg: string) => void }) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setInput("");
    setTurns((prev) => [...prev, { role: "user", text: q }]);
    try {
      const resp = await api.query(q);
      setTurns((prev) => [
        ...prev,
        { role: "assistant", text: resp.answer, citations: resp.citations },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setTurns((prev) => [...prev, { role: "assistant", text: msg, error: true }]);
      onError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel__header">
        <span>知识库问答</span>
      </div>
      <div className="panel__body">
        {turns.length === 0 ? (
          <div className="empty-hint">
            <p>先在下方输入问题，或选择一个示例问题：</p>
            {SUGGESTED.map((s) => (
              <p key={s}>
                <button className="btn btn--ghost" onClick={() => ask(s)}>
                  {s}
                </button>
              </p>
            ))}
          </div>
        ) : (
          <div className="chat-log">
            {turns.map((turn, i) => (
              <div
                key={i}
                className={`chat-turn chat-turn--${turn.role}${turn.error ? " chat-turn--error" : ""}`}
              >
                {turn.text}
                {turn.citations && turn.citations.length > 0 && (
                  <div className="citation-list">
                    {turn.citations.map((c) => (
                      <CitationCard key={c.chunk_id} citation={c} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <div className="chat-input-row">
          <input
            value={input}
            placeholder="输入你的问题，回车发送"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void ask(input);
            }}
            disabled={busy}
          />
          <button className="btn" onClick={() => void ask(input)} disabled={busy || !input.trim()}>
            <SendIcon size={16} />
            {busy ? "生成中…" : "发送"}
          </button>
        </div>
      </div>
    </section>
  );
}
