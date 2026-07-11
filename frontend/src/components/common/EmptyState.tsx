import React from 'react';
import { Empty, Typography } from 'antd';

const { Text } = Typography;

interface EmptyStateProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = '暂无数据',
  description,
  action,
  icon,
  className,
}) => {
  return (
    <div
      className={className}
      style={{
        padding: '48px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Empty
        image={icon ?? Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                color: 'var(--text-primary, #e8eef5)',
                fontSize: 15,
                fontWeight: 500,
                marginBottom: description ? 4 : 12,
              }}
            >
              {title}
            </div>
            {description && (
              <Text style={{ color: 'var(--text-secondary, #8895b4)', fontSize: 13 }}>
                {description}
              </Text>
            )}
            {action && <div style={{ marginTop: 16 }}>{action}</div>}
          </div>
        }
      />
    </div>
  );
};
