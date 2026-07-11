import { useMemo, useRef } from 'react';
import { Button, Space, Tooltip, Typography } from 'antd';
import { DownloadOutlined, TableOutlined, FieldTimeOutlined } from '@ant-design/icons';
import { useVirtualizer } from '@tanstack/react-virtual';
import { GlassPanel } from './GlassPanel';
import { EmptyState } from './EmptyState';

const { Text } = Typography;

export interface ResultGridProps {
  columns: string[];
  rows: unknown[][];
  rowCount?: number;
  elapsedMs?: number;
  truncated?: boolean;
  onExportCsv?: () => void;
  height?: number;
  'data-testid'?: string;
}

const ROW_HEIGHT = 32;

function toCsvCell(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function defaultExport(columns: string[], rows: unknown[][]): void {
  const header = columns.map(toCsvCell).join(',');
  const body = rows.map((r) => r.map(toCsvCell).join(',')).join('\n');
  const csv = `${header}\n${body}`;
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `result-${Date.now()}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export const ResultGrid: React.FC<ResultGridProps> = ({
  columns,
  rows,
  rowCount,
  elapsedMs,
  truncated,
  onExportCsv,
  height = 480,
  'data-testid': testId,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const displayCount = rowCount ?? rows.length;

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  const virtualItems = virtualizer.getVirtualItems();
  const totalSize = virtualizer.getTotalSize();
  const columnWidths = useMemo(() => columns.map(() => 180), [columns]);

  const handleExport = (): void => {
    if (onExportCsv) {
      onExportCsv();
      return;
    }
    defaultExport(columns, rows);
  };

  return (
    <GlassPanel padded={false} className="result-grid" style={{ overflow: 'hidden' }}>
      <div
        style={{
          padding: '10px 14px',
          borderBottom: '1px solid var(--dp-panel-border, rgba(59,130,246,0.14))',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <Space size={12} align="center">
          <TableOutlined style={{ color: 'var(--accent, #3b82f6)' }} />
          <Text style={{ fontSize: 13, color: 'var(--text-secondary, #8895b4)' }}>
            {displayCount.toLocaleString('zh-CN')} 行
          </Text>
          {typeof elapsedMs === 'number' && (
            <Space size={4} align="center">
              <FieldTimeOutlined style={{ color: 'var(--text-tertiary, #506080)' }} />
              <Text style={{ fontSize: 13, color: 'var(--text-secondary, #8895b4)' }}>
                {elapsedMs} ms
              </Text>
            </Space>
          )}
          {truncated && (
            <Text
              style={{
                fontSize: 12,
                color: 'var(--accent-amber, #fbbf24)',
                padding: '2px 8px',
                borderRadius: 999,
                background: 'var(--kb-tag-amber, rgba(251,191,36,0.16))',
              }}
            >
              已截断
            </Text>
          )}
        </Space>
        <Button
          type="text"
          size="small"
          icon={<DownloadOutlined />}
          onClick={handleExport}
          disabled={rows.length === 0}
        >
          导出 CSV
        </Button>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="暂无查询结果" description="执行 SQL 后结果会在此展示" />
      ) : (
        <div
          ref={scrollRef}
          data-testid={testId ?? 'result-grid-scroll'}
          style={{ height, overflow: 'auto', position: 'relative' }}
        >
          <table
            style={{
              display: 'grid',
              width: 'max-content',
              minWidth: '100%',
              borderCollapse: 'separate',
              borderSpacing: 0,
            }}
          >
            <thead
              style={{
                display: 'grid',
                position: 'sticky',
                top: 0,
                zIndex: 2,
                background: 'var(--bg-elevated, #111827)',
              }}
            >
              <tr style={{ display: 'flex' }}>
                {columns.map((col, i) => (
                  <th
                    key={col + i}
                    style={{
                      width: columnWidths[i],
                      minWidth: columnWidths[i],
                      padding: '8px 12px',
                      textAlign: 'left',
                      fontSize: 12,
                      fontWeight: 600,
                      color: 'var(--text-secondary, #8895b4)',
                      borderBottom: '1px solid var(--dp-panel-border, rgba(59,130,246,0.14))',
                    }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody
              style={{
                display: 'grid',
                height: totalSize,
                position: 'relative',
              }}
            >
              {virtualItems.map((vRow) => {
                const row = rows[vRow.index];
                return (
                  <tr
                    key={vRow.key}
                    data-index={vRow.index}
                    data-testid="rg-row"
                    style={{
                      display: 'flex',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      transform: `translateY(${vRow.start}px)`,
                      height: vRow.size,
                      borderBottom: '1px solid var(--border-subtle, rgba(255,255,255,0.05))',
                    }}
                  >
                    {row.map((cell, ci) => {
                      const rendered =
                        cell === null || cell === undefined
                          ? <span style={{ color: 'var(--text-tertiary, #506080)' }}>NULL</span>
                          : typeof cell === 'object'
                          ? JSON.stringify(cell)
                          : String(cell);
                      const raw = typeof cell === 'object' ? JSON.stringify(cell) : String(cell ?? '');
                      return (
                        <td
                          key={ci}
                          style={{
                            width: columnWidths[ci],
                            minWidth: columnWidths[ci],
                            padding: '6px 12px',
                            fontSize: 13,
                            fontFamily: 'var(--font-mono, ui-monospace, monospace)',
                            color: 'var(--text-primary, #e8eef5)',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          <Tooltip title={raw} placement="topLeft" mouseEnterDelay={0.4}>
                            <span>{rendered}</span>
                          </Tooltip>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </GlassPanel>
  );
};
