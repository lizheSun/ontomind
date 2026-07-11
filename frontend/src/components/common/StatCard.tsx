import React from 'react';
import { Typography } from 'antd';
import { GlassPanel } from './GlassPanel';

const { Text } = Typography;

interface StatCardProps {
  icon: React.ReactNode;
  label: React.ReactNode;
  value: React.ReactNode;
  trend?: {
    delta: string;
    direction: 'up' | 'down' | 'flat';
  };
  accent?: 'blue' | 'purple' | 'cyan' | 'emerald' | 'amber' | 'rose';
  className?: string;
}

const ACCENT_BG: Record<NonNullable<StatCardProps['accent']>, string> = {
  blue: 'rgba(59, 130, 246, 0.14)',
  purple: 'rgba(167, 139, 250, 0.14)',
  cyan: 'rgba(34, 211, 238, 0.14)',
  emerald: 'rgba(52, 211, 153, 0.14)',
  amber: 'rgba(251, 191, 36, 0.14)',
  rose: 'rgba(251, 113, 133, 0.14)',
};
const ACCENT_FG: Record<NonNullable<StatCardProps['accent']>, string> = {
  blue: '#60a5fa',
  purple: '#a78bfa',
  cyan: '#22d3ee',
  emerald: '#34d399',
  amber: '#fbbf24',
  rose: '#fb7185',
};

export const StatCard: React.FC<StatCardProps> = ({
  icon,
  label,
  value,
  trend,
  accent = 'blue',
  className,
}) => {
  const trendColor =
    trend?.direction === 'up' ? '#34d399' :
    trend?.direction === 'down' ? '#fb7185' : '#8895b4';
  return (
    <GlassPanel padded className={className}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: ACCENT_BG[accent],
            color: ACCENT_FG[accent],
            fontSize: 22,
          }}
        >
          {icon}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text style={{ display: 'block', color: 'var(--text-secondary, #8895b4)', fontSize: 13 }}>
            {label}
          </Text>
          <div
            style={{
              marginTop: 4,
              display: 'flex',
              alignItems: 'baseline',
              gap: 8,
            }}
          >
            <span
              style={{
                fontSize: 26,
                fontWeight: 600,
                fontFamily: 'var(--font-mono, ui-monospace, monospace)',
                color: 'var(--text-primary, #e8eef5)',
                lineHeight: 1,
              }}
            >
              {value}
            </span>
            {trend && (
              <span style={{ color: trendColor, fontSize: 12, fontWeight: 500 }}>
                {trend.delta}
              </span>
            )}
          </div>
        </div>
      </div>
    </GlassPanel>
  );
};
