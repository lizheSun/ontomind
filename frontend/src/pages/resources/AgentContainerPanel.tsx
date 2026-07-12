/**
 * AgentContainerPanel — 智能体容器面板 (T49 Wave 10)
 *
 * 5 层导航第 2 层：运行在计算节点上的 Agent runtime（opencode / openclaw /
 * harness / custom）。当前后端仍使用 `/resources/agents` 表示 runtime 定义
 * (Agent Container 语义)，T44 数据模型重构会把它拆到 `agent_containers` 表。
 * 本 panel 保持数据合约稳定，屏幕文案已经切到「容器」语义。
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  BuildOutlined,
  CodeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  DangerConfirm,
  DataTable,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';
import type { Agent } from '../../types';

interface AgentContainerPanelProps {
  onCountChange?: (count: number) => void;
}

const TYPE_LABELS: Record<Agent['agent_type'], string> = {
  openclaw: 'OpenClaw',
  opencode: 'OpenCode',
  harness: 'Harness',
  custom: '自定义',
};

const TYPE_COLORS: Record<
  Agent['agent_type'],
  'amber' | 'emerald' | 'blue' | 'purple'
> = {
  openclaw: 'amber',
  opencode: 'emerald',
  harness: 'blue',
  custom: 'purple',
};

const RUNTIME_LABELS: Record<Agent['runtime'], string> = {
  docker: 'Docker',
  python: 'Python',
  node: 'Node.js',
  binary: '二进制',
};

export default function AgentContainerPanel({
  onCountChange,
}: AgentContainerPanelProps) {
  const { message } = App.useApp();
  const [items, setItems] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await resourcesAPI.listAgents({ skip: 0, limit: 200 });
      const list: Agent[] = res.data?.data ?? [];
      setItems(list);
      onCountChange?.(list.length);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '加载智能体容器失败',
      );
    } finally {
      setLoading(false);
    }
  }, [message, onCountChange]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = (row: Agent) => {
    DangerConfirm({
      title: `确认删除容器 “${row.name}”？`,
      content: '关联的智能体实例将失去 runtime 绑定。',
      onOk: async () => {
        try {
          await resourcesAPI.deleteAgent(row.id);
          message.success('已删除');
          await load();
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  };

  const columns: ColumnsType<Agent> = [
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
      dataIndex: 'agent_type',
      key: 'agent_type',
      width: 140,
      render: (t: Agent['agent_type']) => (
        <TagPill color={TYPE_COLORS[t] ?? 'blue'}>
          {TYPE_LABELS[t] ?? t}
        </TagPill>
      ),
    },
    {
      title: 'Runtime',
      dataIndex: 'runtime',
      key: 'runtime',
      width: 120,
      render: (r: Agent['runtime']) => (
        <span style={{ color: '#8895b4', fontSize: 12 }}>
          <CodeOutlined /> {RUNTIME_LABELS[r] ?? r}
        </span>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (v: string) =>
        v ? (
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#8895b4' }}>
            {v}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (active: boolean) =>
        active ? <Tag color="success">已启用</Tag> : <Tag>未启用</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
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
      <DataTable<Agent>
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        emptyTitle="暂无智能体容器"
        emptyDescription="容器由计算节点扫描自动发现；点击顶部「一键发现」触发扫描"
        emptyAction={
          <Space size={4} style={{ color: '#8895b4', fontSize: 12 }}>
            <BuildOutlined /> 支持 opencode / openclaw / harness 自动识别
          </Space>
        }
      />
    </div>
  );
}
