import { useEffect, type ReactNode } from 'react';
import { Input, Segmented } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { PageHeader, GlassPanel, TagPill } from '../../components/common';
import { useKnowledgeBaseStore } from '../../stores/knowledgeBaseStore';
import type { KbLibraryCode } from '../../types/knowledgeBase';

interface KbLibraryLayoutProps {
  libraryCode: KbLibraryCode;
  title: string;
  subtitle: string;
  onSearchChange: (q: string) => void;
  onCreate: () => void;
  filterTags?: string[];
  activeTags?: string[];
  onTagToggle?: (tag: string) => void;
  viewMode?: 'table' | 'card';
  onViewModeChange?: (m: 'table' | 'card') => void;
  children: ReactNode;
}

export default function KbLibraryLayout(props: KbLibraryLayoutProps) {
  const {
    title,
    subtitle,
    onSearchChange,
    onCreate,
    filterTags,
    activeTags,
    onTagToggle,
    viewMode = 'table',
    onViewModeChange,
    children,
  } = props;

  const fetchLibraries = useKnowledgeBaseStore((s) => s.fetchLibraries);
  const libraries = useKnowledgeBaseStore((s) => s.libraries);

  useEffect(() => {
    if (libraries.length === 0) {
      fetchLibraries().catch(() => {});
    }
  }, [libraries.length, fetchLibraries]);

  return (
    <div>
      <PageHeader
        title={title}
        subtitle={subtitle}
        extra={
          <>
            <Input.Search
              placeholder="在本库搜索…"
              allowClear
              onChange={(e) => onSearchChange(e.target.value)}
              style={{ width: 260 }}
            />
            {onViewModeChange && (
              <Segmented
                value={viewMode}
                onChange={(v) => onViewModeChange(v as 'table' | 'card')}
                options={[
                  { label: '列表', value: 'table' },
                  { label: '卡片', value: 'card' },
                ]}
              />
            )}
            <button
              type="button"
              onClick={onCreate}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 8,
                border: '1px solid var(--accent, #3b82f6)',
                background: 'var(--accent, #3b82f6)',
                color: '#fff',
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              <PlusOutlined /> 新建
            </button>
          </>
        }
      />
      {filterTags && filterTags.length > 0 && (
        <GlassPanel padded style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {filterTags.map((tag) => (
              <TagPill
                key={tag}
                color="blue"
                active={activeTags?.includes(tag)}
                onClick={() => onTagToggle?.(tag)}
              >
                {tag}
              </TagPill>
            ))}
          </div>
        </GlassPanel>
      )}
      {children}
    </div>
  );
}
