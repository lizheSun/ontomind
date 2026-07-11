import { PageHeader, GlassPanel } from '../../components/common';

export default function CodeReposPage() {
  return (
    <div>
      <PageHeader
        title="代码库"
        subtitle="内外部代码仓库索引"
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
