import { useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Empty, Input, Segmented, Space, Tag, Typography } from 'antd';
import {
  ArrowRightOutlined,
  ClockCircleOutlined,
  CompassOutlined,
  RobotOutlined,
  RocketOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { GlassPanel, PageHeader, TagPill } from '../../components/common';
import {
  DIFFICULTY_LABELS,
  getTemplateLibraryEntries,
} from '../../presets/agentLoopers';
import type {
  OnboardingDifficulty,
  TemplateKind,
  TemplateLibraryEntry,
} from '../../presets/agentLoopers';

const { Text } = Typography;

type KindFilter = 'all' | TemplateKind;
type DifficultyFilter = 'all' | OnboardingDifficulty;

const KIND_LABEL: Record<TemplateKind, string> = {
  agent: 'Agent 预设',
  sop: 'SOP 模板',
};

const KIND_ROUTE: Record<TemplateKind, (key: string) => string> = {
  agent: (key) => `/resources/agent-looper/new?preset=${encodeURIComponent(key)}`,
  sop: (key) => `/sops/new?template=${encodeURIComponent(key)}`,
};

const DIFFICULTY_TONE: Record<
  OnboardingDifficulty,
  'emerald' | 'blue' | 'amber' | 'rose' | 'purple' | 'cyan'
> = {
  beginner: 'emerald',
  intermediate: 'blue',
  advanced: 'amber',
};

const KIND_TONE: Record<TemplateKind, 'purple' | 'cyan'> = {
  agent: 'purple',
  sop: 'cyan',
};

const cardStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  height: '100%',
};

const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
  gap: 16,
};

const onboardingBannerStyle: CSSProperties = {
  background:
    'linear-gradient(135deg, rgba(96,165,250,0.14) 0%, rgba(167,139,250,0.14) 100%)',
  border: '1px solid rgba(96,165,250,0.30)',
  borderRadius: 16,
  padding: 20,
  marginBottom: 20,
};

const zeroCurveStepStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 10,
  fontSize: 13,
  color: '#c9d3e2',
  lineHeight: 1.6,
};

interface TemplateCardProps {
  entry: TemplateLibraryEntry;
  onUse: (entry: TemplateLibraryEntry) => void;
}

function TemplateCard({ entry, onUse }: TemplateCardProps) {
  const { onboarding } = entry;
  return (
    <GlassPanel padded hover style={cardStyle}>
      <Space size={8} wrap>
        <TagPill color={KIND_TONE[entry.kind]}>{KIND_LABEL[entry.kind]}</TagPill>
        <TagPill color={DIFFICULTY_TONE[onboarding.difficulty]}>
          {DIFFICULTY_LABELS[onboarding.difficulty]}
        </TagPill>
        {onboarding.timeToValue && (
          <span style={{ color: '#8895b4', fontSize: 12 }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {onboarding.timeToValue}
          </span>
        )}
      </Space>

      <div>
        <div
          style={{
            fontSize: 16,
            fontWeight: 600,
            color: '#e8eef5',
            marginBottom: 4,
          }}
        >
          {entry.name}
        </div>
        <Text style={{ color: '#b6c1d3', fontSize: 13, lineHeight: 1.5 }}>
          {onboarding.pitch || entry.description}
        </Text>
      </div>

      {onboarding.quickStart.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <Text style={{ color: '#8895b4', fontSize: 12 }}>快速上手：</Text>
          {onboarding.quickStart.slice(0, 3).map((step, idx) => (
            <div key={idx} style={zeroCurveStepStyle}>
              <span
                style={{
                  minWidth: 20,
                  height: 20,
                  borderRadius: '50%',
                  background: 'rgba(96,165,250,0.14)',
                  color: '#60a5fa',
                  fontSize: 11,
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {idx + 1}
              </span>
              <span>{step}</span>
            </div>
          ))}
        </div>
      )}

      {onboarding.tags.length > 0 && (
        <Space size={4} wrap>
          {onboarding.tags.map((tag) => (
            <Tag
              key={tag}
              style={{
                background: 'rgba(148,163,184,0.10)',
                border: '1px solid rgba(148,163,184,0.22)',
                color: '#c9d3e2',
                fontSize: 11,
              }}
            >
              {tag}
            </Tag>
          ))}
        </Space>
      )}

      <div style={{ marginTop: 'auto', paddingTop: 8 }}>
        <Button
          type="primary"
          block
          icon={<ArrowRightOutlined />}
          onClick={() => onUse(entry)}
        >
          使用此模板
        </Button>
      </div>
    </GlassPanel>
  );
}

export default function TemplateLibrary() {
  const navigate = useNavigate();
  const [kindFilter, setKindFilter] = useState<KindFilter>('all');
  const [difficulty, setDifficulty] = useState<DifficultyFilter>('all');
  const [category, setCategory] = useState<string>('all');
  const [query, setQuery] = useState('');

  const allEntries = useMemo(() => getTemplateLibraryEntries(), []);

  const categories = useMemo(() => {
    const set = new Set<string>();
    allEntries.forEach((e) => set.add(e.onboarding.category));
    return ['all', ...Array.from(set).sort()];
  }, [allEntries]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return allEntries.filter((e) => {
      if (kindFilter !== 'all' && e.kind !== kindFilter) return false;
      if (difficulty !== 'all' && e.onboarding.difficulty !== difficulty) return false;
      if (category !== 'all' && e.onboarding.category !== category) return false;
      if (!q) return true;
      const haystack = [
        e.name,
        e.description,
        e.onboarding.pitch,
        e.onboarding.category,
        ...e.onboarding.tags,
        ...e.onboarding.quickStart,
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [allEntries, kindFilter, difficulty, category, query]);

  const beginnerEntries = useMemo(
    () => allEntries.filter((e) => e.onboarding.difficulty === 'beginner'),
    [allEntries],
  );

  const handleUse = (entry: TemplateLibraryEntry) => {
    navigate(KIND_ROUTE[entry.kind](entry.key));
  };

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader
        title="模板库"
        subtitle="预置 Agent 与 SOP 模板，一键复用；beginner 模板零学习曲线，配置即用。"
      />

      <div style={onboardingBannerStyle}>
        <Space align="start" size={16} style={{ width: '100%' }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              background: 'rgba(167,139,250,0.20)',
              color: '#a78bfa',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
            }}
          >
            <RocketOutlined />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 15,
                fontWeight: 600,
                color: '#e8eef5',
                marginBottom: 6,
              }}
            >
              <ThunderboltOutlined style={{ marginRight: 6, color: '#facc15' }} />
              零学习曲线 onboarding
            </div>
            <Text style={{ color: '#b6c1d3', fontSize: 13, lineHeight: 1.6 }}>
              标为「零学习曲线」的模板可以直接点「使用此模板」→ 选一个模型 →
              保存，全程 3 步以内即可跑起来。目前平台共有{' '}
              <b style={{ color: '#60a5fa' }}>{beginnerEntries.length}</b>{' '}
              个 beginner 模板，覆盖数据分析、知识库入库、数据源接入等常见起点。
            </Text>
          </div>
        </Space>
      </div>

      <GlassPanel padded style={{ marginBottom: 16 }}>
        <Space size={12} wrap style={{ width: '100%' }}>
          <Input
            allowClear
            placeholder="搜索模板名 / 关键词 / 标签"
            prefix={<SearchOutlined style={{ color: '#8895b4' }} />}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ width: 260 }}
          />
          <Segmented<KindFilter>
            value={kindFilter}
            onChange={(v) => setKindFilter(v)}
            options={[
              { label: '全部', value: 'all' },
              {
                label: (
                  <span>
                    <RobotOutlined /> Agent
                  </span>
                ),
                value: 'agent',
              },
              {
                label: (
                  <span>
                    <CompassOutlined /> SOP
                  </span>
                ),
                value: 'sop',
              },
            ]}
          />
          <Segmented<DifficultyFilter>
            value={difficulty}
            onChange={(v) => setDifficulty(v)}
            options={[
              { label: '全部难度', value: 'all' },
              { label: DIFFICULTY_LABELS.beginner, value: 'beginner' },
              { label: DIFFICULTY_LABELS.intermediate, value: 'intermediate' },
              { label: DIFFICULTY_LABELS.advanced, value: 'advanced' },
            ]}
          />
          <Segmented<string>
            value={category}
            onChange={(v) => setCategory(v)}
            options={categories.map((c) => ({
              label: c === 'all' ? '全部分类' : c,
              value: c,
            }))}
          />
          <Text style={{ color: '#8895b4', fontSize: 12 }}>
            共 {filtered.length} / {allEntries.length} 个模板
          </Text>
        </Space>
      </GlassPanel>

      {filtered.length === 0 ? (
        <GlassPanel padded>
          <Empty description="没有匹配的模板 —— 试试清空搜索或换个分类" />
        </GlassPanel>
      ) : (
        <div style={gridStyle}>
          {filtered.map((entry) => (
            <TemplateCard
              key={`${entry.kind}:${entry.key}`}
              entry={entry}
              onUse={handleUse}
            />
          ))}
        </div>
      )}
    </div>
  );
}
