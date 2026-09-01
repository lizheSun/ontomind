/** Yao /dashboard/computers 风格的列表/详情基元。 */
import type { ReactNode } from 'react';
import { DesktopOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { StatusDot } from '../common/StatusDot';

export function timeAgo(iso?: string | null): string {
  if (!iso) return '从未';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '—';
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (sec < 15) return '刚刚';
  if (sec < 60) return `${sec} 秒前`;
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} 小时前`;
  return `${Math.floor(sec / 86400)} 天前`;
}

export function StatusPill({
  tone = 'ok',
  label,
}: {
  tone?: 'ok' | 'off' | 'warn';
  label: string;
}) {
  const cls =
    tone === 'off' ? 'om-status-pill is-off' : tone === 'warn' ? 'om-status-pill is-warn' : 'om-status-pill';
  const dot: 'ok' | 'idle' | 'warn' = tone === 'off' ? 'idle' : tone === 'warn' ? 'warn' : 'ok';
  return (
    <span className={cls}>
      <StatusDot tone={dot} pulse={tone === 'ok'} />
      {label}
    </span>
  );
}

export function FilterTabs({
  items,
  value,
  onChange,
}: {
  items: { key: string; label: string; count?: number }[];
  value: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="om-comp-filters">
      {items.map((it) => (
        <button
          key={it.key}
          type="button"
          className={value === it.key ? 'om-comp-filter active' : 'om-comp-filter'}
          onClick={() => onChange(it.key)}
        >
          {it.label}
          {typeof it.count === 'number' ? <span className="n">{it.count}</span> : null}
        </button>
      ))}
    </div>
  );
}

export function HostGlyph({ children }: { children?: ReactNode }) {
  return <div className="om-host-glyph">{children ?? <DesktopOutlined />}</div>;
}

export function HostCard({
  glyph,
  title,
  subtitle,
  pill,
  foot,
  onClick,
  actions,
}: {
  glyph?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  pill: ReactNode;
  foot?: ReactNode;
  onClick?: () => void;
  actions?: ReactNode;
}) {
  return (
    <article
      className="om-host-card"
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div className="om-host-card-top">
        <HostGlyph>{glyph}</HostGlyph>
        <div className="om-host-meta">
          <div className="om-host-title">{title}</div>
          {subtitle ? <div className="om-host-sub">{subtitle}</div> : null}
        </div>
        {pill}
      </div>
      {(foot || actions) && (
        <div className="om-host-foot" onClick={(e) => e.stopPropagation()}>
          {foot}
          {actions ? <div className="om-comp-actions">{actions}</div> : null}
        </div>
      )}
    </article>
  );
}

export function InfoTile({
  label,
  value,
  icon,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="om-comp-tile">
      <div className="om-comp-tile-label">
        {icon}
        {label}
      </div>
      <div className="om-comp-tile-value">{value ?? '—'}</div>
    </div>
  );
}

export function AddrFoot({
  addr,
  tag,
  when,
}: {
  addr: ReactNode;
  tag?: ReactNode;
  when?: ReactNode;
}) {
  return (
    <>
      <ThunderboltOutlined />
      <code>{addr}</code>
      {tag ? <span>{tag}</span> : null}
      {when ? <span>{when}</span> : null}
    </>
  );
}
