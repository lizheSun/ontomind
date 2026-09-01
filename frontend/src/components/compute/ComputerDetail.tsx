/** 单台电脑详情 — 对齐 Yao /dashboard/computers/detail。 */
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Space } from 'antd';
import {
  ClockCircleOutlined,
  DesktopOutlined,
  HomeOutlined,
  LeftOutlined,
  ReloadOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { PageHeader } from '../common/PageHeader';
import { EmptyState } from '../common/EmptyState';
import useComputeStore from '../../stores/computeStore';
import { AddrFoot, HostCard, HostGlyph, InfoTile, StatusPill, timeAgo } from './computerUi';
import { containerStatusLabel } from '../../types/compute';

export default function ComputerDetail() {
  const { nodeId } = useParams();
  const navigate = useNavigate();
  const {
    nodes,
    selectedNode,
    selectNode,
    fetchNodes,
    ensureLocalNode,
    containers,
    fetchContainers,
    containersLoading,
  } = useComputeStore();

  const id = Number(nodeId);
  const node = nodes.find((n) => n.id === id) ?? (selectedNode?.id === id ? selectedNode : null);

  useEffect(() => {
    void ensureLocalNode();
    void fetchNodes();
  }, [ensureLocalNode, fetchNodes]);

  useEffect(() => {
    if (node) {
      selectNode(node);
      void fetchContainers();
    }
  }, [node?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!node) {
    return (
      <EmptyState
        title="找不到这台电脑"
        description="节点可能已删除。"
        action={
          <Button onClick={() => navigate('/infra/compute')}>
            返回列表
          </Button>
        }
      />
    );
  }

  const running = node.status === 'online';

  return (
    <div>
      <button type="button" className="om-comp-back" onClick={() => navigate('/infra/compute')}>
        <LeftOutlined /> 电脑
      </button>

      <PageHeader
        title={
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <HostGlyph>{node.isLocal ? <HomeOutlined /> : <DesktopOutlined />}</HostGlyph>
            {node.name}
          </span>
        }
        desc={
          <span className="om-comp-id">
            {node.isLocal ? 'local' : 'ssh'} · id {node.id}
            {node.description ? ` · ${node.description}` : ''}
          </span>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void fetchNodes()}>
            刷新
          </Button>
        }
      />

      <div className="om-comp-statusbar">
        <StatusPill tone={running ? 'ok' : 'off'} label={running ? '运行中' : node.status || '离线'} />
        <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>{node.isLocal ? '持久 · 本地' : '远程 SSH'}</span>
      </div>

      <div className="om-comp-grid">
        <InfoTile label="节点" icon={<ThunderboltOutlined />} value={`${node.host}:${node.port}`} />
        <InfoTile
          label="上次检测"
          icon={<ClockCircleOutlined />}
          value={node.lastCheckedAt ? `${timeAgo(node.lastCheckedAt)}` : '从未'}
        />
        <InfoTile label="认证" icon={<SafetyOutlined />} value={node.authType === 'key' ? 'SSH 私钥' : '密码'} />
        <InfoTile label="用户" icon={<UserOutlined />} value={node.username} />
      </div>

      <div className="om-comp-section">
        <div className="om-comp-section-head">
          <div className="om-comp-section-title">系统信息</div>
        </div>
        <div className="om-comp-grid">
          <InfoTile label="主机" value={node.host} />
          <InfoTile label="端口" value={String(node.port)} />
          <InfoTile label="类型" value={node.isLocal ? '本机 Docker' : '远程节点'} />
          <InfoTile label="状态" value={node.status || 'unknown'} />
        </div>
      </div>

      <div className="om-comp-section">
        <div className="om-comp-section-head">
          <div className="om-comp-section-title">容器</div>
          <Button type="link" size="small" onClick={() => navigate('/infra/compute/docker')}>
            全部
          </Button>
        </div>
        {containers.length === 0 ? (
          <div style={{ color: 'var(--text-tertiary)', fontSize: 13, padding: '8px 0' }}>
            {containersLoading ? '加载中…' : '暂无容器'}
          </div>
        ) : (
          <div className="om-host-list">
            {containers.slice(0, 6).map((c) => {
              const on = c.status === 'running';
              return (
                <HostCard
                  key={c.id}
                  title={c.name}
                  subtitle={c.image}
                  pill={
                    <StatusPill
                      tone={on ? 'ok' : 'off'}
                      label={containerStatusLabel[c.status] || c.status}
                    />
                  }
                  onClick={() => navigate('/infra/compute/docker')}
                  foot={<AddrFoot addr={c.ports || '无端口'} tag={c.network || 'bridge'} when={c.created} />}
                />
              );
            })}
          </div>
        )}
      </div>

      <div className="om-comp-section">
        <div className="om-comp-section-head">
          <div className="om-comp-section-title">服务</div>
          <Space>
            <Button type="link" size="small" onClick={() => navigate('/infra/compute/services')}>
              管理服务
            </Button>
          </Space>
        </div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>在「服务」页查看容器内常驻进程（opencode 等）。</div>
      </div>
    </div>
  );
}
