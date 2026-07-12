/**
 * AgentContainerPanel — 智能体容器面板 (T49 Wave 10)
 *
 * 5 层导航第 2 层：运行在计算节点上的 Agent 容器（opencode / openclaw /
 * harness / custom）。T44 后 `/resources/agents` 返回新的 agents 表
 * (agent_looper 配置)，容器由 register-local 自动发现，通过
 * `discovered_containers` 字段返回。
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  BuildOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  DataTable,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';

interface AgentContainerPanelProps {
  onCountChange?: (count: number) => void;
}

interface DiscoveredContainer {
  kind: string;
  label: string;
  icon: string;
  cli_path: string | null;
  pids: number[];
  open_ports: number[];
  is_running: boolean;
}

export default function AgentContainerPanel({
  onCountChange,
}: AgentContainerPanelProps) {
  const { message } = App.useApp();
  const [containers, setContainers] = useState<DiscoveredContainer[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await resourcesAPI.registerLocalInstance();
      const data = res?.data || {};
      const list: DiscoveredContainer[] = data?.discovered_containers ?? [];
      setContainers(list);
      onCountChange?.(list.length);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '发现容器失败',
      );
    } finally {
      setLoading(false);
    }
  }, [message, onCountChange]);

  useEffect(() => {
    load();
  }, [load]);

  const columns: ColumnsType<DiscoveredContainer> = [
    {
      title: '名称',
      dataIndex: 'label',
      key: 'label',
      render: (v: string) => (
        <span style={{ color: '#e8eef5', fontWeight: 500 }}>{v}</span>
      ),
    },
    {
      title: '类型',
      dataIndex: 'kind',
      key: 'kind',
      width: 140,
      render: (t: string) => (
        <TagPill color={t === 'opencode' ? 'emerald' : 'amber'}>
          {t === 'opencode' ? 'OpenCode' : 'OpenClaw'}
        </TagPill>
      ),
    },
    {
      title: 'CLI 路径',
      dataIndex: 'cli_path',
      key: 'cli_path',
      width: 300,
      render: (v: string | null) =>
        v ? (
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#8895b4' }}>
            {v}
          </span>
        ) : (
          '-'
        ),
    },
    {
      title: '端口',
      dataIndex: 'open_ports',
      key: 'open_ports',
      width: 100,
      render: (ports: number[]) => (ports.length > 0 ? ports.join(', ') : '-'),
    },
    {
      title: '状态',
      key: 'status',
      width: 90,
      render: (_: unknown, row: DiscoveredContainer) =>
        row.is_running ? <Tag color="success">运行中</Tag> : <Tag>已停止</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: () => <span style={{ color: '#506080' }}>自动发现</span>,
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
      <DataTable<DiscoveredContainer>
        rowKey="label"
        columns={columns}
        dataSource={containers}
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
