/** LogViewer — 只读日志视图（等宽字体 + 级别着色 + 跟随滚动）. */
import { useEffect, useRef, useState } from 'react';
import { Switch } from 'antd';
import type { LogLine } from './types';

const LEVEL_COLOR: Record<LogLine['level'], string> = {
  info: 'var(--ink-80)',
  warn: '#a86e12',
  error: '#a5361e',
  event: '#3b52af',
};

export default function LogViewer({ lines, height = 440 }: { lines: LogLine[]; height?: number }) {
  const [follow, setFollow] = useState(true);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (follow && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [lines, follow]);

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
        gap: 8, marginBottom: 8, fontSize: 12, color: 'var(--ink-40)',
      }}>
        跟随滚动
        <Switch size="small" checked={follow} onChange={setFollow} />
      </div>
      <div
        ref={bodyRef}
        style={{
          height, overflow: 'auto',
          background: 'var(--paper-02)',
          border: '1px solid var(--border-hairline)',
          borderRadius: 8, padding: '10px 12px',
        }}
      >
        {lines.length === 0 ? (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-40)' }}>
            (暂无日志)
          </div>
        ) : lines.map((l) => (
          <div
            key={l.seq}
            style={{
              fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.7,
              color: LEVEL_COLOR[l.level], whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            }}
          >
            <span style={{ color: 'var(--ink-20)', marginRight: 10, userSelect: 'none' }}>
              {String(l.seq).padStart(4, ' ')}
            </span>
            {l.text}
          </div>
        ))}
      </div>
    </div>
  );
}
