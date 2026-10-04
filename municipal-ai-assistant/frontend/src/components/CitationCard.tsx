import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText } from 'lucide-react';
import type { Citation } from '../api';

interface Props {
  citations: Citation[];
}

export default function CitationCard({ citations }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="citations">
      {citations.map((c, i) => (
        <div key={i} className="citation-card">
          <div
            className="citation-header"
            onClick={() => setExpanded(expanded === i ? null : i)}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <FileText size={12} />
              {c.source_file} · S.&nbsp;{c.page}
              <span
                className={`badge ${
                  c.relevance_score >= 0.7
                    ? 'badge-green'
                    : c.relevance_score >= 0.5
                    ? 'badge-blue'
                    : 'badge-yellow'
                }`}
                style={{ marginLeft: 4 }}
              >
                {Math.round(c.relevance_score * 100)}%
              </span>
            </span>
            {expanded === i ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </div>
          {expanded === i && (
            <div className="citation-body">„{c.excerpt.substring(0, 400)}{c.excerpt.length > 400 ? '…' : ''}"</div>
          )}
        </div>
      ))}
    </div>
  );
}
