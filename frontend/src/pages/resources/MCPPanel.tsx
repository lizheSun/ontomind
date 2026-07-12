/**
 * MCPPanel — MCP 工具面板 (T49 Wave 10)
 *
 * 5 层导航第 5 层：Model Context Protocol 工具连接。对应 opencode
 * `opencode.json` 里 `mcp:*` 段的定义，同一 MCP 可被多个智能体共享。
 *
 * 本 panel 支持：
 *   - 展示 SSE / Stdio / HTTP 三种类型
 *   - 手动新增 / 删除
 *   - 后续 T48 的 auto-discover 端点通过顶部「一键发现」按钮统一触发
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Space, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ReloadOutlined } from '@ant-design/icons';
import {
  DangerConfirm,
  DataTable,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';
import type { MCPConfig } from '../../types';

interface MCPPanelProps {
  onCountChange?: (count: number) => void;
}

const TYPE_LABELS: Record<MCPConfig['mcp_type'], string> = {
  sse: 'SSE',
  stdio: 'Stdio',
  http: 'HTTP',
};

const TYPE_COLORS: Record<
  MCPConfig['mcp_type'],
  'blue' | 'emerald' | 'amber'
> = {
  sse: 'blue',
  stdio: 'emerald',
  http: 'amber',
};

export default function MCPPanel({ onCountChange }: MCPPanelProps) {
  const { message } = App.useApp();
  const [items, setItems] = useState<MCPConfig[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await resourcesAPI.listMCPs({ skip: 0, limit: 200 });
      const list: MCPConfig[] = res.data?.data ?? [];
      setItems(list);
      onCountChange?.(list.length);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '加载 MCP 失败',
      );
    } finally {
      setLoading(false);
    }
  }, [message, onCountChange]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = (row: MCPConfig) => {
    DangerConfirm({
      title: `确认删除 MCP “${row.name}”？`,
      onOk: async () => {
        try {
          await resourcesAPI.deleteMCP(row.id);
          message.success('已删除');
          await load();
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  };

  const columns: ColumnsType<MCPConfig> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string) => (
        <span style={{ color: '#e8eef5', fontWeight: 500 }}>{v}</span>
      ),
    },
    {
      title: '类型',
      dataIndex: 'mcp_type',
      key: 'mcp_type',
      width: 110,
      render: (t: MCPConfig['mcp_type']) => (
        <TagPill color={TYPE_COLORS[t] ?? 'blue'}>
          {TYPE_LABELS[t] ?? t}
        </TagPill>
      ),
    },
    {
      title: '端点',
      key: 'endpoint',
      render: (_: unknown, row) => {
        const val = row.url ?? row.command ?? '-';
        return (
          <Tooltip title={val}>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#8895b4',
                display: 'inline-block',
                maxWidth: 320,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {val}
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: '自动发现',
      dataIndex: 'auto_discovery_enabled',
      key: 'auto_discovery_enabled',
      width: 100,
      render: (v: boolean) =>
        v ? <Tag color="processing">开启</Tag> : <Tag>关闭</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (active: boolean) =>
        active ? <Tag color="success">启用</Tag> : <Tag>未启用</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, row) => (
        <Space size={0}>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDelete(row)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 8,
          marginBottom: 12,
        }}
      >
        <Button
          icon={<ReloadOutlined />}
          onClick={load}
          loading={loading}
        >
          刷新
        </Button>
      </div>
      <DataTable<MCPConfig>
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        emptyTitle="暂无 MCP 工具"
        emptyDescription="MCP 由「一键发现」自动同步自 ~/.config/opencode/opencode.json"
      />
    </div>
  );
}
