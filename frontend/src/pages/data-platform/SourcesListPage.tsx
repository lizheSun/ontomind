import { PageHeader, GlassPanel } from '../../components/common';

export default function SourcesListPage() {
  return (
    <div>
      <PageHeader
        title="数据平台 · 数据源"
        subtitle="连接、探查、并对话你的数据资产"
      />
      <GlassPanel>
        <div
          style={{
            padding: 48,
            textAlign: 'center',
            color: 'var(--text-secondary, #8895b4)',
          }}
        >
          该页面将在后续任务（T21-T24）完成。
        </div>
      </GlassPanel>
    </div>
  );
}
