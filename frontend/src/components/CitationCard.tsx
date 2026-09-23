import type { Citation } from "../types";

export default function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="citation-card">
      <span className="citation-card__n">{citation.n}</span>
      <div>
        <div className="citation-card__meta">
          {citation.doc_id} / {citation.chunk_id} · {citation.source} · score {citation.score.toFixed(4)}
        </div>
        <div className="citation-card__snippet">{citation.snippet}…</div>
      </div>
    </div>
  );
}
