import React from 'react';
import { Typography, Space } from 'antd';

const { Title, Text } = Typography;

interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  extra?: React.ReactNode;
  className?: string;
  compact?: boolean;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  extra,
  className,
  compact = false,
}) => {
  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        padding: compact ? '12px 0 16px' : '20px 0 24px',
        marginBottom: 8,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <Title
          level={2}
          style={{
            margin: 0,
            fontSize: compact ? 22 : 28,
            lineHeight: 1.2,
            fontWeight: 600,
            letterSpacing: '-0.01em',
            color: 'var(--text-primary, #e8eef5)',
          }}
        >
          {title}
        </Title>
        {subtitle && (
          <Text
            style={{
              display: 'block',
              marginTop: 6,
              fontSize: 14,
              color: 'var(--text-secondary, #8895b4)',
              lineHeight: 1.5,
            }}
          >
            {subtitle}
          </Text>
        )}
      </div>
      {extra && <Space size={12}>{extra}</Space>}
    </div>
  );
};
