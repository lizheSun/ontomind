import React from 'react';

interface SectionTitleProps {
  children: React.ReactNode;
  extra?: React.ReactNode;
  className?: string;
}

export const SectionTitle: React.FC<SectionTitleProps> = ({ children, extra, className }) => {
  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
      }}
    >
      <h3
        style={{
          margin: 0,
          fontSize: 16,
          fontWeight: 600,
          color: 'var(--text-primary, #e8eef5)',
          position: 'relative',
          paddingLeft: 12,
          lineHeight: 1.4,
        }}
      >
        <span
          aria-hidden
          style={{
            position: 'absolute',
            left: 0,
            top: 4,
            bottom: 4,
            width: 3,
            borderRadius: 2,
            background:
              'var(--gradient-hero, linear-gradient(135deg, #3b82f6 0%, #8b5cf6 45%, #06b6d4 100%))',
          }}
        />
        {children}
      </h3>
      {extra}
    </div>
  );
};
