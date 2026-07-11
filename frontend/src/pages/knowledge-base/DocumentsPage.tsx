import { PageHeader, GlassPanel } from '../../components/common';

export default function DocumentsPage() {
  return (
    <div>
      <PageHeader
        title="文档库"
        subtitle="制度 · SOP · 方案与手册"
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
