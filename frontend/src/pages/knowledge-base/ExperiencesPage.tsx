import { PageHeader, GlassPanel } from '../../components/common';

export default function ExperiencesPage() {
  return (
    <div>
      <PageHeader
        title="业务经验库"
        subtitle="一线业务经验沉淀"
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
