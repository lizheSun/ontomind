import { Empty } from 'antd';

export default function PlaceholderPage({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="om-page page-enter" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100%' }}>
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div style={{ textAlign: 'center', maxWidth: 420 }}>
            <div className="om-page-title" style={{ fontSize: 17, marginBottom: 6 }}>{title}</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{desc}</div>
          </div>
        }
      />
    </div>
  );
}
