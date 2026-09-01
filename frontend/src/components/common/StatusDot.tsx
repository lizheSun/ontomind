type Tone = 'ok' | 'warn' | 'err' | 'idle' | 'run';

const COLOR: Record<Tone, string> = {
  ok: 'var(--success)',
  warn: 'var(--warning)',
  err: 'var(--danger)',
  idle: 'var(--text-tertiary)',
  run: 'var(--accent)',
};

export function StatusDot({
  tone = 'idle',
  pulse = false,
  title,
}: {
  tone?: Tone;
  pulse?: boolean;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={pulse ? 'om-dot om-dot-pulse' : 'om-dot'}
      style={{ background: COLOR[tone] }}
    />
  );
}
