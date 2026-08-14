/**
 * 平台总览仪表盘 — 整合五个域的核心指标。
 * 【UI 重构】Apple 官网风格：浅色卡片 + 大片留白 + 分层文字。
 * 设计参照 PROTOTYPE-GUIDANCE.md §9.2 导航结构。
 */
import { Space, Typography } from 'antd';
import {
  ApiOutlined, CloudServerOutlined, CodeOutlined,
  DatabaseOutlined, RobotOutlined, SafetyOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface MetricCard {
  title: string;
  value: string;
  trend: string;
  color: string;
  icon: React.ReactNode;
  status: 'up' | 'down' | 'stable' | 'warning';
}

const metrics: MetricCard[] = [
  { title: 'AI 代码贡献率', value: '38.5%', trend: '+3.2%', color: '#0071e3', icon: <CodeOutlined />, status: 'up' },
  { title: '数据资产', value: '1,247', trend: '+87', color: '#0a84ff', icon: <DatabaseOutlined />, status: 'up' },
  { title: '模型服务', value: '12', trend: 'P99: 234ms', color: '#5b5bf6', icon: <RobotOutlined />, status: 'stable' },
  { title: '活跃 Agent', value: '8', trend: '97.3% 成功率', color: '#ff9f0a', icon: <ApiOutlined />, status: 'up' },
  { title: '安全合规', value: '合规', trend: '2 项待办', color: '#ff375f', icon: <SafetyOutlined />, status: 'warning' },
  { title: '算力集群', value: '32', trend: '73% 利用率', color: '#34c759', icon: <CloudServerOutlined />, status: 'stable' },
];

/* 【UI 重构】Apple 风格卡片 hover 动效 */
const cardHoverIn = (e: React.MouseEvent<HTMLDivElement>) => {
  e.currentTarget.style.transform = 'translateY(-2px)';
  e.currentTarget.style.boxShadow = '0 6px 24px rgba(0,0,0,0.07)';
  e.currentTarget.style.borderColor = 'rgba(0,0,0,0.16)';
};
const cardHoverOut = (e: React.MouseEvent<HTMLDivElement>) => {
  e.currentTarget.style.transform = '';
  e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.04)';
  e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)';
};

export default function OverviewPage() {
  return (
    <div className="page-enter" style={{
      padding: '40px 48px',
      maxWidth: 1400,
      margin: '0 auto',
    }}>
      {/* 【UI 重构】Hero 标题区：大留白 + SF 字体层级 */}
      <Space direction="vertical" size={4} style={{ marginBottom: 40 }}>
        <Text style={{
          fontFamily: "var(--font-sans, -apple-system, 'SF Pro Display', sans-serif)",
          fontSize: 36, fontWeight: 700,
          color: '#1d1d1f', letterSpacing: '-0.03em',
        }}>
          OntoMind
        </Text>
        <Text style={{ fontSize: 15, color: '#6e6e73', fontWeight: 400, letterSpacing: '-0.01em' }}>
          AI 领域工程平台 · CodeOps · DataOps · ModelOps · AgentOps · GovOps 五域融合
        </Text>
      </Space>

      {/* 【UI 重构】Bento Grid：Apple 浅色卡片 + 柔和阴影 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: 20,
      }}>
        {metrics.map((m) => (
          <div key={m.title} style={{
            background: '#FFFFFF',
            borderRadius: 18,
            padding: '24px 26px',
            boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
            border: '1px solid rgba(0,0,0,0.06)',
            cursor: 'default',
            transition: 'transform .22s ease, box-shadow .22s ease, border-color .22s ease',
          }}
          onMouseEnter={cardHoverIn}
          onMouseLeave={cardHoverOut}
          >
            {/* 图标 + 状态指示 */}
            <div style={{
              display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
              marginBottom: 16,
            }}>
              <span style={{
                fontSize: 22,
                color: m.color,
                opacity: 0.85,
                transition: 'opacity .18s ease',
              }}>{m.icon}</span>
              {/* 状态段 */}
              <span style={{
                fontSize: 10.5, fontWeight: 600,
                color: m.status === 'up' ? '#34c759'
                  : m.status === 'down' ? '#ff3b30'
                  : m.status === 'warning' ? '#ff9f0a'
                  : '#86868b',
              }}>
                {m.status === 'up' && '↑ '}
                {m.status === 'down' && '↓ '}
                {m.status === 'up' && '增长'}
                {m.status === 'down' && '下降'}
                {m.status === 'stable' && '稳定'}
                {m.status === 'warning' && '待处理'}
              </span>
            </div>

            {/* 数值 */}
            <div style={{
              fontSize: 32, fontWeight: 700,
              color: '#1d1d1f',
              fontFamily: "var(--font-sans, -apple-system, 'SF Pro Display', sans-serif)",
              letterSpacing: '-0.02em',
              marginBottom: 6,
              lineHeight: 1.1,
            }}>
              {m.value}
            </div>

            {/* 标题 */}
            <div style={{
              fontSize: 13, color: '#6e6e73', fontWeight: 500, marginBottom: 4,
            }}>
              {m.title}
            </div>

            {/* 趋势 */}
            <div style={{ fontSize: 12, color: '#86868b' }}>
              {m.trend}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
