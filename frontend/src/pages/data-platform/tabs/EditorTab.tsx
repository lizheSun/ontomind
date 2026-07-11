import { useMemo } from 'react';
import { Button, Space, Typography, message } from 'antd';
import { PlayCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import { SqlEditor, ResultGrid } from '../../../components/common';
import type { SchemaHint, SupportedDialect } from '../../../components/common';
import type { DpDataSource, DpExecuteResponse, DpSchemaResponse } from '../../../types/dataPlatform';
import { dataPlatformService } from '../../../services/dataPlatform.service';

const { Text } = Typography;

interface Props {
  source: DpDataSource;
  schema?: DpSchemaResponse;
  sql: string;
  onSqlChange: (v: string) => void;
  executeResult: DpExecuteResponse | null;
  setExecuteResult: (r: DpExecuteResponse | null) => void;
  executing: boolean;
  setExecuting: (b: boolean) => void;
}

function dialectFor(d: DpDataSource['dialect']): SupportedDialect {
  if (d === 'postgresql') return 'postgresql';
  if (d === 'sqlite') return 'sqlite';
  return 'mysql';
}

function toSchemaHint(schema: DpSchemaResponse | undefined): SchemaHint | undefined {
  if (!schema) return undefined;
  const tables: SchemaHint['tables'] = [];
  for (const db of schema.databases) {
    for (const t of db.tables) {
      tables.push({
        name: t.name,
        columns: t.columns.map((c) => ({ name: c.name, type: c.type })),
      });
    }
  }
  return { tables };
}

export default function EditorTab({
  source,
  schema,
  sql,
  onSqlChange,
  executeResult,
  setExecuteResult,
  executing,
  setExecuting,
}: Props) {
  const schemaHint = useMemo(() => toSchemaHint(schema), [schema]);

  const runQuery = async (override?: string): Promise<void> => {
    const text = (override ?? sql).trim();
    if (!text) {
      message.warning('请输入 SQL');
      return;
    }
    setExecuting(true);
    try {
      const res = await dataPlatformService.executeSync(source.id, text, 1000);
      setExecuteResult(res);
      message.success(`执行成功 · ${res.rowCount} 行 · ${res.elapsedMs} ms`);
    } catch (err: unknown) {
      const anyErr = err as { response?: { data?: { message?: string } }; message?: string };
      message.error(anyErr.response?.data?.message ?? anyErr.message ?? '执行失败');
    } finally {
      setExecuting(false);
    }
  };

  // TODO(Wave 6+): true SSE stream w/ Authorization header — requires token-in-query support
  const openStream = async (): Promise<void> => {
    const text = sql.trim();
    if (!text) {
      message.warning('请输入 SQL');
      return;
    }
    setExecuting(true);
    try {
      const res = await dataPlatformService.executeSync(source.id, text, 100_000);
      setExecuteResult(res);
      // 复用 ResultGrid 的内置 CSV 导出：直接构建并下载
      const header = res.columns.map((c) => escapeCsv(c.name)).join(',');
      const body = res.rows.map((r) => r.map((v) => escapeCsv(v)).join(',')).join('\n');
      const csv = `${header}\n${body}`;
      const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${source.name}-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${res.rowCount} 行`);
    } catch (err: unknown) {
      const anyErr = err as { response?: { data?: { message?: string } }; message?: string };
      message.error(anyErr.response?.data?.message ?? anyErr.message ?? '导出失败');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <Text style={{ fontSize: 13, color: 'var(--text-secondary, #8895b4)' }}>
          已连接: {source.database}
        </Text>
        <Space size={8}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => runQuery()}
            loading={executing}
          >
            执行 (Ctrl+Enter)
          </Button>
          <Button icon={<DownloadOutlined />} onClick={openStream} disabled={executing}>
            流式导出 CSV
          </Button>
        </Space>
      </div>

      <SqlEditor
        value={sql}
        onChange={onSqlChange}
        dialect={dialectFor(source.dialect)}
        schema={schemaHint}
        onRun={(v) => runQuery(v)}
        height={340}
      />

      <ResultGrid
        columns={executeResult?.columns.map((c) => c.name) ?? []}
        rows={executeResult?.rows ?? []}
        rowCount={executeResult?.rowCount}
        elapsedMs={executeResult?.elapsedMs}
        truncated={executeResult?.truncated}
      />
    </div>
  );
}

function escapeCsv(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}
