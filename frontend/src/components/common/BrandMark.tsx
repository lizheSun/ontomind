/** OntoMind 标识：蓝底圆 + 三节点（本体星座），处理方式对齐 Yao logo 圆标。 */
export function BrandMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <circle cx="16" cy="16" r="16" fill="var(--accent)" />
      <circle cx="16" cy="10.2" r="2.1" fill="#fff" />
      <circle cx="10.6" cy="20.6" r="2.1" fill="#fff" opacity="0.92" />
      <circle cx="21.4" cy="20.6" r="2.1" fill="#fff" opacity="0.92" />
      <path
        d="M16 12.2 11.6 19.1M16 12.2l4.4 6.9"
        stroke="#fff"
        strokeWidth="1.35"
        strokeLinecap="round"
        opacity="0.85"
      />
    </svg>
  );
}
