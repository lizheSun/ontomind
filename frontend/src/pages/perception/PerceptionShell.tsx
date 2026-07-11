import { useNavigate } from 'react-router-dom';
import { Button, Space, Typography } from 'antd';
import {
  DatabaseOutlined,
  BookOutlined,
  ArrowRightOutlined,
  ConsoleSqlOutlined,
  TableOutlined,
  FileTextOutlined,
  BulbOutlined,
  GithubOutlined,
} from '@ant-design/icons';
import { PageHeader, GlassPanel } from '../../components/common';

const { Text } = Typography;

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  bullets: { icon: React.ReactNode; label: string }[];
  cta: string;
  onClick: () => void;
  accentVar: string;
}

function FeatureCard({ icon, title, subtitle, bullets, cta, onClick, accentVar }: FeatureCardProps) {
  return (
    <GlassPanel
      padded
      bordered
      hover
      style={{
        flex: 1,
        minWidth: 320,
        minHeight: 340,
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
      }}
    >
      <div
        onClick={onClick}
        style={{ display: 'flex', flexDirection: 'column', flex: 1 }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 14,
            background: `linear-gradient(135deg, ${accentVar}22 0%, ${accentVar}11 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 28,
            color: accentVar,
            marginBottom: 20,
          }}
        >
          {icon}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 600,
            color: 'var(--text-primary, #e8eef5)',
          }}
        >
          {title}
        </div>
        <Text
          style={{
            display: 'block',
            marginTop: 8,
            fontSize: 14,
            color: 'var(--text-secondary, #8895b4)',
            lineHeight: 1.6,
          }}
        >
          {subtitle}
        </Text>
        <Space
          direction="vertical"
          size={12}
          style={{ marginTop: 24, marginBottom: 24, flex: 1 }}
        >
          {bullets.map((b, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ color: accentVar, fontSize: 14 }}>{b.icon}</span>
              <Text style={{ fontSize: 13, color: 'var(--text-secondary, #8895b4)' }}>
                {b.label}
              </Text>
            </div>
          ))}
        </Space>
        <Button
          type="primary"
          size="large"
          icon={<ArrowRightOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          style={{ borderRadius: 10, alignSelf: 'flex-start' }}
        >
          {cta}
        </Button>
      </div>
    </GlassPanel>
  );
}

export default function PerceptionShell() {
  const navigate = useNavigate();
  return (
    <div>
      <PageHeader
        title="感知层"
        subtitle="信息入口 · 连接一切数据源与知识资产"
      />
      <div
        style={{
          display: 'flex',
          gap: 24,
          marginTop: 12,
          flexWrap: 'wrap',
        }}
      >
        <FeatureCard
          icon={<DatabaseOutlined />}
          title="数据平台"
          subtitle="数据源管理 · SQL 探查 · AI 对话生成 SQL · 元数据浏览与智能标注"
          accentVar="var(--accent, #3b82f6)"
          bullets={[
            { icon: <DatabaseOutlined />, label: '数据源 CRUD · Fernet 加密 · 智能添加' },
            { icon: <ConsoleSqlOutlined />, label: 'SQL Editor + AI 对话生成 SQL' },
            { icon: <TableOutlined />, label: '元数据浏览 · Cursor 风格流式标注' },
          ]}
          cta="进入数据平台"
          onClick={() => navigate('/data-platform/sources')}
        />
        <FeatureCard
          icon={<BookOutlined />}
          title="知识库"
          subtitle="数据资产 · 代码库 · 文档库 · 业务经验"
          accentVar="var(--accent-purple, #a78bfa)"
          bullets={[
            { icon: <TableOutlined />, label: '数据资产 · 按业务域整理' },
            { icon: <GithubOutlined />, label: '代码库 · 内外部 Git 仓库索引' },
            { icon: <FileTextOutlined />, label: '文档库 · 制度 / SOP / 手册' },
            { icon: <BulbOutlined />, label: '业务经验 · 场景/内容/结果沉淀 · 跨库搜索' },
          ]}
          cta="进入知识库"
          onClick={() => navigate('/knowledge-base/data-assets')}
        />
      </div>
    </div>
  );
}
