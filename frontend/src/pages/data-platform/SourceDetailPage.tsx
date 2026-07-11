import { PageHeader, GlassPanel } from '../../components/common';

export default function SourceDetailPage() {
  return (
    <div>
      <PageHeader
        title="数据源详情"
        subtitle="SQL 编辑器 · AI 对话 · 执行历史"
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
