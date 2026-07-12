/**
 * AgentPanel — 智能体面板 (T49 Wave 10)
 *
 * 5 层导航第 3 层：运行在智能体容器中的定制 Agent（Agent Looper）。
 * 替代 Wave 9 的 `AgentLooperListPage`，接口保持一致 —— 只是嵌入到
 * 新的资源页 5 层导航中，标题、CTA 文案切到「智能体」语义。
 *
 * 数据源：`agentLooperService.list()`。
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  DangerConfirm,
  DataTable,
  TagPill,
} from '../../components/common';
import { agentLooperService } from '../../services/agentLooper.service';
import type {
  AgentListEntry,
  AgentType,
} from '../../types/agent';

interface AgentPanelProps {
  onCountChange?: (count: number) => void;
}

const TYPE_LABELS: Record<AgentType, string> = {
  custom_looper: '自定义 Loop',
  opencode_native: 'OpenCode 原生',
  mcp_agent: 'MCP Agent',
  imported: '导入',
};

const TYPE_COLORS: Record<
  AgentType,
  'blue' | 'purple' | 'cyan' | 'amber'
> = {
  custom_looper: 'blue',
  opencode_native: 'purple',
  mcp_agent: 'cyan',
  imported: 'amber',
};

const STRATEGY_LABELS: Record<string, string> = {
  single_shot: '单次',
  react: 'ReAct',
  plan_execute: 'Plan-Execute',
  reflect: 'Reflect',
};

export default function AgentPanel({ onCountChange }: AgentPanelProps) {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [entries, setEntries] = useState<AgentListEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [discovering, setDiscovering] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await agentLooperService.list();
      setEntries(list);
      onCountChange?.(list.length);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '加载智能体列表失败',
      );
    } finally {
      setLoading(false);
    }
  }, [message, onCountChange]);

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

  const handleView = (row: AgentListEntry) => {
    navigate(`/resources/agent-looper/${row.id}`);
  };

  const handleEdit = (row: AgentListEntry) => {
    navigate(`/resources/agent-looper/${row.id}?edit=true`);
  };

  const handleDelete = (row: AgentListEntry) => {
    DangerConfirm({
      title: `确认删除智能体 “${row.name}”？`,
      content: '此操作不可撤销，历史版本也会一并删除。',
      onOk: async () => {
        try {
          await agentLooperService.delete(row.id);
          message.success('已删除');
          setEntries((cur) => cur.filter((e) => e.id !== row.id));
          onCountChange?.(entries.length - 1);
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  };

  const columns: ColumnsType<AgentListEntry> = [
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
      render: (t: AgentType) => (
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
      width: 120,
      render: (v: string) => STRATEGY_LABELS[v] ?? v,
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
      title: '已发布',
      dataIndex: 'is_published',
      key: 'is_published',
      width: 90,
      render: (v: boolean) =>
        v ? <Tag color="processing">已发布</Tag> : <Tag>草稿</Tag>,
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
          新建智能体
        </Button>
      </div>
      <DataTable<AgentListEntry>
        rowKey="id"
        columns={columns}
        dataSource={entries}
        loading={loading}
        emptyTitle="暂无智能体"
        emptyDescription="点击「发现本地 Agent」自动扫描本机 opencode 配置，或「新建智能体」手动创建"
      />
    </div>
  );
}
