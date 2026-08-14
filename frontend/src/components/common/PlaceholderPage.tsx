import { Empty, Space, Typography } from 'antd';
const { Text } = Typography;
export default function PlaceholderPage({ title, desc }: { title: string; desc: string }) {
  return (
    <div style={{ padding: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={
        <Space direction="vertical" size={8} style={{ textAlign: 'center' }}>
          <Text strong style={{ fontSize: 17, fontFamily: "var(--font-sans, -apple-system, 'SF Pro Display', sans-serif)" }}>{/* 【UI 重构】Fraunces serif → SF Pro */}{title}</Text>
          <Text type="secondary" style={{ fontSize: 12.5, maxWidth: 400, display: 'block' }}>{desc}</Text>
        </Space>
      } />
    </div>
  );
}