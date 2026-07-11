import React from 'react';

type TagColor = 'blue' | 'purple' | 'cyan' | 'emerald' | 'amber' | 'rose';

interface TagPillProps {
  children: React.ReactNode;
  color?: TagColor;
  onClick?: () => void;
  active?: boolean;
  className?: string;
}

const BG: Record<TagColor, string> = {
  blue: 'var(--kb-tag-blue, rgba(59, 130, 246, 0.16))',
  purple: 'var(--kb-tag-purple, rgba(167, 139, 250, 0.16))',
  cyan: 'var(--kb-tag-cyan, rgba(34, 211, 238, 0.16))',
  emerald: 'var(--kb-tag-emerald, rgba(52, 211, 153, 0.16))',
  amber: 'var(--kb-tag-amber, rgba(251, 191, 36, 0.16))',
  rose: 'var(--kb-tag-rose, rgba(251, 113, 133, 0.16))',
};
const FG: Record<TagColor, string> = {
  blue: '#60a5fa',
  purple: '#a78bfa',
  cyan: '#22d3ee',
  emerald: '#34d399',
  amber: '#fbbf24',
  rose: '#fb7185',
};

export const TagPill: React.FC<TagPillProps> = ({
  children,
  color = 'blue',
  onClick,
  active = false,
  className,
}) => {
  const clickable = !!onClick;
  return (
    <span
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        clickable
          ? (e) => (e.key === 'Enter' || e.key === ' ') && onClick?.()
          : undefined
      }
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 500,
        background: BG[color],
        color: FG[color],
        cursor: clickable ? 'pointer' : 'default',
        border: active
          ? `1px solid ${FG[color]}`
          : '1px solid transparent',
        transition: 'all var(--duration-fast, 150ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1))',
        userSelect: 'none',
      }}
    >
      {children}
    </span>
  );
};
