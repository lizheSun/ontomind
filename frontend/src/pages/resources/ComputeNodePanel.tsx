/**
 * ComputeNodePanel — 计算节点面板 (T49 Wave 10)
 *
 * 5 层导航第 1 层：物理机 / 虚拟机 / Docker Host / K8s Pod 等宿主机。
 *
 * 数据源：`resourcesAPI.listInstances()` (T37 及以前)。
 * 后续 T44/T47 会引入独立 `/api/v1/compute-nodes` 端点，届时替换即可 —
 * panel 组件保持接口稳定。
 */
import { useCallback, useEffect, useState } from 'react';
import { App, Button, Space, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  DesktopOutlined,
  ExperimentOutlined,
  HomeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  DangerConfirm,
  DataTable,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';
import type { AgentScanResult, Instance } from '../../types';

interface ComputeNodePanelProps {
  onCountChange?: (count: number) => void;
}

const TYPE_LABELS: Record<Instance['instance_type'], string> = {
  physical: '物理机',
  docker: 'Docker',
  k8s_pod: 'K8s Pod',
};

const TYPE_COLORS: Record<
  Instance['instance_type'],
  'blue' | 'emerald' | 'purple'
> = {
  physical: 'blue',
  docker: 'emerald',
  k8s_pod: 'purple',
};

export default function ComputeNodePanel({ onCountChange }: ComputeNodePanelProps) {
  const { message } = App.useApp();
  const [items, setItems] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(false);
  const [registeringLocal, setRegisteringLocal] = useState(false);
  const [scanningId, setScanningId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await resourcesAPI.listInstances({ skip: 0, limit: 200 });
      const list: Instance[] = res.data?.data ?? [];
      setItems(list);
      onCountChange?.(list.length);
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '加载计算节点失败',
      );
    } finally {
      setLoading(false);
    }
  }, [message, onCountChange]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRegisterLocal = async () => {
    setRegisteringLocal(true);
    try {
      const res = await resourcesAPI.registerLocalInstance();
      message.success(res.data?.message ?? '本地节点已注册');
      await load();
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '注册本地节点失败',
      );
    } finally {
      setRegisteringLocal(false);
    }
  };

  const handleScan = async (row: Instance) => {
    setScanningId(row.id);
    try {
      const res = await resourcesAPI.scanAgents(row.id);
      const data: AgentScanResult = res.data?.data ?? res.data;
      const healthy = data.agents?.filter((a) => a.is_healthy).length ?? 0;
      message.success(
        `扫描完成：发现 ${data.agents?.length ?? 0} 个 Agent，${healthy} 个健康`,
      );
      await load();
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : '扫描失败',
      );
    } finally {
      setScanningId(null);
    }
  };

  const handleDelete = (row: Instance) => {
    DangerConfirm({
      title: `确认删除节点 “${row.name}”？`,
      content: '删除后其上运行的 Agent 记录将失去关联。',
      onOk: async () => {
        try {
          await resourcesAPI.deleteInstance(row.id);
          message.success('已删除');
          await load();
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  };

  const columns: ColumnsType<Instance> = [
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
      dataIndex: 'instance_type',
      key: 'instance_type',
      width: 120,
      render: (t: Instance['instance_type']) => (
        <TagPill color={TYPE_COLORS[t] ?? 'blue'}>
          {TYPE_LABELS[t] ?? t}
        </TagPill>
      ),
    },
    {
      title: '主机地址',
      key: 'address',
      width: 200,
      render: (_: unknown, row) => (
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#94a3b8' }}>
          {row.host}:{row.port}
        </span>
      ),
    },
    {
      title: '规格',
      key: 'spec',
      width: 200,
      render: (_: unknown, row) => (
        <Space size={4} style={{ fontSize: 12, color: '#8895b4' }}>
          {row.cpu_cores != null && <span>{row.cpu_cores}c</span>}
          {row.memory_mb != null && <span>· {Math.round(row.memory_mb / 1024)}G</span>}
          {row.disk_gb != null && <span>· {row.disk_gb}G</span>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: Instance['status']) => {
        const color =
          s === 'online' ? 'success' : s === 'maintenance' ? 'warning' : 'default';
        const label =
          s === 'online' ? '在线' : s === 'maintenance' ? '维护中' : '离线';
        return <Tag color={color}>{label}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, row) => (
        <Space size={0}>
          <Tooltip title="扫描节点上的 Agent 容器">
            <Button
              type="link"
              size="small"
              icon={<ExperimentOutlined />}
              loading={scanningId === row.id}
              onClick={() => handleScan(row)}
            >
              扫描
            </Button>
          </Tooltip>
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
          icon={<HomeOutlined />}
          loading={registeringLocal}
          onClick={handleRegisterLocal}
        >
          注册本机
        </Button>
      </div>
      <DataTable<Instance>
        rowKey="id"
        columns={columns}
        dataSource={items}
        loading={loading}
        emptyTitle="暂无计算节点"
        emptyDescription="点击「注册本机」自动检测并添加本机为计算节点"
        emptyAction={
          <Button
            type="primary"
            icon={<DesktopOutlined />}
            loading={registeringLocal}
            onClick={handleRegisterLocal}
          >
            注册本机为计算节点
          </Button>
        }
      />
    </div>
  );
}
