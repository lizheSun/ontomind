import { PageHeader, GlassPanel } from '../../components/common';

export default function KbSearchPage() {
  return (
    <div>
      <PageHeader
        title="知识库搜索"
        subtitle="跨库聚合检索"
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
