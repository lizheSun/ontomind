import { useNavigate } from 'react-router-dom';
import { GlassPanel } from '../../../components/common';
import type { KbSearchResult, KbLibraryCode } from '../../../types/knowledgeBase';

interface Props {
  result: KbSearchResult;
  query: string;
}

const LIB_ROUTE: Record<KbLibraryCode, string> = {
  data_asset: '/knowledge-base/data-assets',
  code_repo: '/knowledge-base/code-repos',
  document: '/knowledge-base/documents',
  experience: '/knowledge-base/experiences',
};

function highlight(text: string, q: string) {
  if (!q) return text;
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const parts = text.split(new RegExp(`(${escaped})`, 'gi'));
  return parts.map((p, i) =>
    p.toLowerCase() === q.toLowerCase() ? (
      <mark
        key={i}
        style={{
          background: 'var(--kb-tag-amber, rgba(251,191,36,0.16))',
          color: '#fbbf24',
          padding: '0 2px',
          borderRadius: 3,
        }}
      >
        {p}
      </mark>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}

export default function SearchResultCard({ result, query }: Props) {
  const navigate = useNavigate();
  return (
    <GlassPanel padded hover style={{ cursor: 'pointer' }}>
      <div
        onClick={() =>
          navigate(`${LIB_ROUTE[result.libraryCode]}?highlight=${result.id}`)
        }
      >
        <div
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: 'var(--text-primary, #e8eef5)',
            marginBottom: 6,
          }}
        >
          {highlight(result.title, query)}
        </div>
        {result.snippet && (
          <div
            style={{
              fontSize: 13,
              color: 'var(--text-secondary, #8895b4)',
              lineHeight: 1.5,
            }}
          >
            {highlight(result.snippet, query)}
          </div>
        )}
      </div>
    </GlassPanel>
  );
}
