/**
 * Agent Looper — list page (Wave 9 W2 T38).
 *
 * Replaces the legacy AgentsPanel inside /resources. Consumes
 * `agentLooperService.list()` and offers:
 *   - 「新建 Agent」 → navigate to detail with edit mode
 *   - 「发现本地 Agent」 → agentLooperService.discover()
 *   - row actions: 详情 / 编辑 / 删除 (DangerConfirm)
 */

import { useCallback, useEffect, useState } from 'react';
import { Button, Space, Tag, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  PageHeader,
  DataTable,
  TagPill,
  DangerConfirm,
} from '../../components/common';
import { agentLooperService } from '../../services/agentLooper.service';
import type {
  AgentLooperListEntry,
  AgentLooperType,
} from '../../types/agentLooper';

const TYPE_LABELS: Record<AgentLooperType, string> = {
  custom_looper: '自定义 Loop',
  opencode_native: 'OpenCode 原生',
  mcp_agent: 'MCP Agent',
  imported: '导入',
};

const TYPE_COLORS: Record<
  AgentLooperType,
  'blue' | 'purple' | 'cyan' | 'emerald' | 'amber' | 'rose'
> = {
  custom_looper: 'blue',
  opencode_native: 'purple',
  mcp_agent: 'cyan',
  imported: 'amber',
};

const STRATEGY_LABELS: Record<string, string> = {
  single_shot: '单次调用',
  react: 'ReAct',
  plan_execute: 'Plan-Execute',
  reflect: 'Reflect',
};

export default function AgentLooperListPage() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<AgentLooperListEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [discovering, setDiscovering] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await agentLooperService.list();
      setEntries(list);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '加载 Agent Looper 列表失败',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDiscover = async () => {
    setDiscovering(true);
    try {
      const res = await agentLooperService.discover();
      message.success(`发现完成：已同步 ${res.upserted_count} 个本地 Agent`);
      await load();
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '发现本地 Agent 失败',
      );
    } finally {
      setDiscovering(false);
    }
  };

  const handleCreate = () => {
    navigate('/resources/agent-looper/new?edit=true');
  };

  const handleView = (row: AgentLooperListEntry) => {
    navigate(`/resources/agent-looper/${row.id}`);
  };

  const handleEdit = (row: AgentLooperListEntry) => {
    navigate(`/resources/agent-looper/${row.id}?edit=true`);
  };

  const handleDelete = (row: AgentLooperListEntry) => {
    DangerConfirm({
      title: `确认删除 Agent “${row.name}”？`,
      content: '此操作不可撤销，历史版本也会一并删除。',
      onOk: async () => {
        try {
          await agentLooperService.delete(row.id);
          message.success('已删除');
          setEntries((cur) => cur.filter((e) => e.id !== row.id));
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  };

  const columns: ColumnsType<AgentLooperListEntry> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string, row) => (
        <a
          onClick={() => handleView(row)}
          style={{ color: '#60a5fa', fontWeight: 500 }}
        >
          {v}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 140,
      render: (t: AgentLooperType) => (
        <TagPill color={TYPE_COLORS[t] ?? 'blue'}>
          {TYPE_LABELS[t] ?? t}
        </TagPill>
      ),
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      width: 180,
      render: (v: string) =>
        v ? (
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
            {v}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '循环策略',
      dataIndex: 'loop_strategy',
      key: 'loop_strategy',
      width: 130,
      render: (v: string) => STRATEGY_LABELS[v] ?? v,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (active: boolean) =>
        active ? (
          <Tag color="success">启用</Tag>
        ) : (
          <Tag color="default">未启用</Tag>
        ),
    },
    {
      title: '已发布',
      dataIndex: 'is_published',
      key: 'is_published',
      width: 90,
      render: (v: boolean) =>
        v ? <Tag color="processing">已发布</Tag> : <Tag>草稿</Tag>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 170,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, row) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => handleView(row)}>
            详情
          </Button>
          <Button type="link" size="small" onClick={() => handleEdit(row)}>
            编辑
          </Button>
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
      <PageHeader
        title="Agent Looper"
        subtitle="AI Agent 定制与生命周期管理"
        extra={
          <Space>
            <Button
              icon={<ThunderboltOutlined />}
              loading={discovering}
              onClick={handleDiscover}
            >
              发现本地 Agent
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              新建 Agent
            </Button>
          </Space>
        }
      />
      <DataTable<AgentLooperListEntry>
        rowKey="id"
        columns={columns}
        dataSource={entries}
        loading={loading}
        emptyTitle="暂无 Agent 配置"
        emptyDescription="点击「发现本地 Agent」自动扫描本地 opencode 配置，或点击「新建 Agent」创建"
        emptyAction={
          <Space>
            <Button
              icon={<ThunderboltOutlined />}
              loading={discovering}
              onClick={handleDiscover}
            >
              发现本地 Agent
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              新建 Agent
            </Button>
          </Space>
        }
      />
    </div>
  );
}
