import { PageHeader, GlassPanel } from '../../components/common';

export default function DataAssetsPage() {
  return (
    <div>
      <PageHeader
        title="数据资产"
        subtitle="按业务域整理的数据资产目录"
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
