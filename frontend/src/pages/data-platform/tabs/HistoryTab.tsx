import { useEffect, useState } from 'react';
import { Button, Modal, Space, Tag, Tooltip, Typography, message } from 'antd';
import {
  CopyOutlined,
  EyeOutlined,
  LoadingOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { DataTable } from '../../../components/common';
import type { DpHistoryStatus, DpQueryHistory } from '../../../types/dataPlatform';
import { dataPlatformService } from '../../../services/dataPlatform.service';

const { Text } = Typography;

interface Props {
  sourceId: number;
  onRerun: (sql: string) => void;
}

const STATUS_META: Record<
  DpHistoryStatus,
  { label: string; color: string; bg: string }
> = {
  success: { label: '成功', color: '#34d399', bg: 'rgba(52,211,153,0.14)' },
  error: { label: '失败', color: '#fb7185', bg: 'rgba(251,113,133,0.14)' },
  running: { label: '运行中', color: '#60a5fa', bg: 'rgba(96,165,250,0.14)' },
  canceled: { label: '已取消', color: '#8895b4', bg: 'rgba(136,149,180,0.14)' },
  timeout: { label: '超时', color: '#fbbf24', bg: 'rgba(251,191,36,0.14)' },
};

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

export default function HistoryTab({ sourceId, onRerun }: Props) {
  const [rows, setRows] = useState<DpQueryHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewRow, setViewRow] = useState<DpQueryHistory | null>(null);

  const load = async (): Promise<void> => {
    setLoading(true);
    try {
      const list = await dataPlatformService.listHistory(sourceId);
      setRows(list);
    } catch (err: unknown) {
      const anyErr = err as { message?: string };
      message.error(anyErr.message ?? '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceId]);

  const handleCopy = async (text: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      message.success('已复制');
    } catch {
      message.error('复制失败');
    }
  };

  const columns: ColumnsType<DpQueryHistory> = [
    {
      title: '时间',
      dataIndex: 'startedAt',
      key: 'startedAt',
      width: 170,
      render: (v: string | null) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: 'SQL 摘要',
      dataIndex: 'sqlText',
      key: 'sqlText',
      render: (sql: string) => (
        <Tooltip title={<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{sql}</pre>}>
          <Text style={{ fontFamily: 'var(--font-mono, ui-monospace, monospace)', fontSize: 12.5 }}>
            {truncate(sql, 60)}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: DpHistoryStatus) => {
        const meta = STATUS_META[s];
        return (
          <Tag
            icon={s === 'running' ? <LoadingOutlined spin /> : undefined}
            style={{
              borderRadius: 6,
              background: meta.bg,
              color: meta.color,
              border: 'none',
            }}
          >
            {meta.label}
          </Tag>
        );
      },
    },
    {
      title: '行数',
      dataIndex: 'rowCount',
      key: 'rowCount',
      width: 90,
      render: (v: number | null) => (v ?? '-'),
    },
    {
      title: '用时',
      dataIndex: 'elapsedMs',
      key: 'elapsedMs',
      width: 110,
      render: (v: number | null) => (v == null ? '-' : `${v} ms`),
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: unknown, record: DpQueryHistory) => (
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => setViewRow(record)}
          >
            查看
          </Button>
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => onRerun(record.sqlText)}
          >
            重跑
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: 'var(--text-secondary, #8895b4)', fontSize: 13 }}>
          最近 50 条执行历史
        </Text>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => void load()}>
          刷新
        </Button>
      </div>

      <DataTable<DpQueryHistory>
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        emptyTitle="暂无执行历史"
        emptyDescription="在编辑器中执行 SQL 后，这里会显示历史记录"
      />

      <Modal
        open={viewRow !== null}
        title="SQL 详情"
        footer={
          <Space>
            <Button
              icon={<CopyOutlined />}
              onClick={() => void handleCopy(viewRow?.sqlText ?? '')}
            >
              复制 SQL
            </Button>
            <Button onClick={() => setViewRow(null)}>关闭</Button>
          </Space>
        }
        onCancel={() => setViewRow(null)}
        width={720}
      >
        {viewRow && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <pre
              style={{
                margin: 0,
                padding: 12,
                borderRadius: 8,
                background: 'var(--code-bg, #0a0f1f)',
                fontFamily: 'var(--font-mono, ui-monospace, monospace)',
                fontSize: 12.5,
                whiteSpace: 'pre-wrap',
                color: 'var(--text-primary, #e8eef5)',
                maxHeight: 360,
                overflow: 'auto',
              }}
            >
              {viewRow.sqlText}
            </pre>
            {viewRow.errorMessage && (
              <Text style={{ color: '#fb7185', fontSize: 12.5 }}>
                错误：{viewRow.errorMessage}
              </Text>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
