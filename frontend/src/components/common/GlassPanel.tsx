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
      className={className ? `${className} om-card` : 'om-card'}
      style={{
        border: bordered ? undefined : 'none',
        boxShadow: hover ? 'var(--shadow-lg)' : undefined,
        padding: padded ? undefined : 0,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
