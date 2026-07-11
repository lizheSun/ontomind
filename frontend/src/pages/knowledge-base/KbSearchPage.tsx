import { useEffect, useMemo, useState } from 'react';
import { Input, Space, Typography } from 'antd';
import { useSearchParams } from 'react-router-dom';
import {
  DatabaseOutlined,
  GithubOutlined,
  FileTextOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import {
  PageHeader,
  GlassPanel,
  SectionTitle,
  EmptyState,
  TagPill,
} from '../../components/common';
import SearchResultCard from './components/SearchResultCard';
import { knowledgeBaseService } from '../../services/knowledgeBase.service';
import type {
  KbSearchGrouped,
  KbLibraryCode,
  KbSearchResult,
} from '../../types/knowledgeBase';

const { Text } = Typography;

type PillColor = 'blue' | 'purple' | 'cyan' | 'amber';

const LIB_META: Record<
  KbLibraryCode,
  { name: string; icon: React.ReactNode; color: PillColor }
> = {
  data_asset: { name: '数据资产', icon: <DatabaseOutlined />, color: 'blue' },
  code_repo: { name: '代码库', icon: <GithubOutlined />, color: 'purple' },
  document: { name: '文档库', icon: <FileTextOutlined />, color: 'cyan' },
  experience: { name: '业务经验', icon: <BulbOutlined />, color: 'amber' },
};

interface Bucket {
  code: KbLibraryCode;
  items: KbSearchResult[];
}

export default function KbSearchPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const filter = (params.get('lib') as KbLibraryCode | null) ?? null;
  const [inputValue, setInputValue] = useState(q);
  const [grouped, setGrouped] = useState<KbSearchGrouped | null>(null);
  const [loading, setLoading] = useState(false);

  // Sync input → URL param, debounced 300ms
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (inputValue !== q) {
        const next = new URLSearchParams(params);
        if (inputValue) next.set('q', inputValue);
        else next.delete('q');
        setParams(next, { replace: true });
      }
    }, 300);
    return () => window.clearTimeout(t);
  }, [inputValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch grouped results whenever q or filter changes
  useEffect(() => {
    if (!q) {
      setGrouped(null);
      return;
    }
    setLoading(true);
    knowledgeBaseService
      .search(q, filter ?? undefined)
      .then(setGrouped)
      .catch(() => setGrouped(null))
      .finally(() => setLoading(false));
  }, [q, filter]);

  const totalCount = useMemo(() => {
    if (!grouped) return 0;
    return (
      grouped.dataAsset.length +
      grouped.codeRepo.length +
      grouped.document.length +
      grouped.experience.length
    );
  }, [grouped]);

  const toggleFilter = (code: KbLibraryCode | null) => {
    const next = new URLSearchParams(params);
    if (code) next.set('lib', code);
    else next.delete('lib');
    setParams(next, { replace: true });
  };

  const buckets: Bucket[] = grouped
    ? [
        { code: 'data_asset', items: grouped.dataAsset },
        { code: 'code_repo', items: grouped.codeRepo },
        { code: 'document', items: grouped.document },
        { code: 'experience', items: grouped.experience },
      ]
    : [];

  return (
    <div>
      <PageHeader title="知识库搜索" subtitle="跨库聚合检索" />
      <GlassPanel padded style={{ marginBottom: 16 }}>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Input.Search
            size="large"
            allowClear
            placeholder="输入关键词跨库检索…"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onSearch={(v) => setInputValue(v)}
          />
          <Space size={8} wrap>
            <TagPill
              color="blue"
              active={filter === null}
              onClick={() => toggleFilter(null)}
            >
              全部
            </TagPill>
            {(Object.keys(LIB_META) as KbLibraryCode[]).map((code) => (
              <TagPill
                key={code}
                color={LIB_META[code].color}
                active={filter === code}
                onClick={() => toggleFilter(filter === code ? null : code)}
              >
                {LIB_META[code].icon}
                <span style={{ marginLeft: 4 }}>{LIB_META[code].name}</span>
              </TagPill>
            ))}
          </Space>
          {q && (
            <Text
              style={{
                fontSize: 13,
                color: 'var(--text-secondary, #8895b4)',
              }}
            >
              {loading ? '搜索中…' : `共 ${totalCount} 条结果`}
            </Text>
          )}
        </Space>
      </GlassPanel>

      {!q && (
        <EmptyState
          title="输入关键词开始搜索"
          description="跨 4 个知识子库聚合检索"
        />
      )}
      {q && !loading && totalCount === 0 && (
        <EmptyState
          title="未找到匹配结果"
          description="尝试其他关键词或切换子库筛选"
        />
      )}

      {q &&
        buckets.map(
          ({ code, items }) =>
            items.length > 0 && (
              <div key={code} style={{ marginBottom: 24 }}>
                <SectionTitle
                  extra={
                    <Text
                      style={{
                        fontSize: 12,
                        color: 'var(--text-tertiary, #506080)',
                      }}
                    >
                      {items.length}
                    </Text>
                  }
                >
                  <span
                    style={{
                      color: `var(--accent-${LIB_META[code].color === 'blue' ? '' : LIB_META[code].color}, var(--accent, #3b82f6))`,
                    }}
                  >
                    {LIB_META[code].icon}
                  </span>
                  <span style={{ marginLeft: 8 }}>{LIB_META[code].name}</span>
                </SectionTitle>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns:
                      'repeat(auto-fill, minmax(360px, 1fr))',
                    gap: 12,
                  }}
                >
                  {items.map((r) => (
                    <SearchResultCard
                      key={`${code}-${r.id}`}
                      result={r}
                      query={q}
                    />
                  ))}
                </div>
              </div>
            ),
        )}
    </div>
  );
}
