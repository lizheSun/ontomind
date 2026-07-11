import React from 'react';

interface GlassPanelProps {
  children: React.ReactNode;
  padded?: boolean;
  bordered?: boolean;
  className?: string;
  style?: React.CSSProperties;
  hover?: boolean;
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  children,
  padded = true,
  bordered = true,
  className,
  style,
  hover = false,
}) => {
  return (
    <div
      className={className}
      style={{
        background: 'rgba(255, 255, 255, 0.03)',
        border: bordered
          ? '1px solid var(--dp-panel-border, rgba(59, 130, 246, 0.14))'
          : 'none',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderRadius: 'var(--radius-lg, 16px)',
        padding: padded ? 24 : 0,
        boxShadow: hover ? 'var(--dp-panel-glow, 0 0 32px rgba(59,130,246,0.10))' : 'none',
        transition: 'box-shadow var(--duration-normal, 300ms) var(--ease-out, cubic-bezier(0.16,1,0.3,1))',
        ...style,
      }}
    >
      {children}
    </div>
  );
};
