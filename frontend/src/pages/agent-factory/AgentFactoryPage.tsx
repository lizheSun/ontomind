/**
 * Agent 工厂主页 — 面板由 /agentops/{agents,bundles,deploy} 侧边栏路由控制。
 * 不再使用内部 Tabs —— 二级导航已由左侧栏承担。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { App, Alert, Spin, Typography } from 'antd';
import { extractErrMsg } from '../../stores/computeStore';
import * as svc from '../../services/agentFactory.service';
import type { PermissionKeyMeta, PresetsResponse } from '../../types/agentFactory';
import AgentDesigner from '../../components/agent-factory/AgentDesigner';
import BundleDesigner from '../../components/agent-factory/BundleDesigner';
import DeployCenter from '../../components/agent-factory/DeployCenter';

const { Text } = Typography;

export default function AgentFactoryPage() {
  const { notification } = App.useApp();
  const location = useLocation();

  const [meta, setMeta] = useState<PermissionKeyMeta[]>([]);
  const [presets, setPresets] = useState<PresetsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fatal, setFatal] = useState<string>('');
  const [deployBundleId, setDeployBundleId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pk, ps] = await Promise.all([svc.getPermissionKeys(), svc.getPresets()]);
      setMeta(pk.meta);
      setPresets(ps);
      setFatal('');
    } catch (err) {
      setFatal(extractErrMsg(err));
      notification.error({ title: '加载 Agent 工厂元数据失败', description: extractErrMsg(err) });
    } finally {
      setLoading(false);
    }
  }, [notification]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 根据 URL 路径决定显示哪个面板
  const panel = useMemo(() => {
    const p = location.pathname;
    if (p.startsWith('/agentops/bundles')) return 'bundles';
    if (p.startsWith('/agentops/deploy')) return 'deploy';
    return 'agents';
  }, [location.pathname]);

  const goDeploy = (bundleId: number) => {
    setDeployBundleId(bundleId);
    // 由路由控制跳转，侧边栏自动高亮
    window.history.pushState(null, '', '/agentops/deploy');
  };

  if (loading) {
    return (
      <div style={{ padding: 60, textAlign: 'center' }}>
        <Spin />
        <div style={{ marginTop: 10 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>加载权限元数据与内置预设…</Text>
        </div>
      </div>
    );
  }

  if (fatal) {
    return (
      <Alert type="error" showIcon style={{ margin: 20 }} title="Agent 工厂不可用"
        description={<span style={{ fontSize: 12 }}>{fatal}<br />请确认后端已启动（http://localhost:8000）。</span>} />
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-root)' }}>
      <div style={{ flex: 1, minHeight: 0, padding: '16px 16px 0', overflow: 'auto' }}>
        {panel === 'agents' && <AgentDesigner meta={meta} />}
        {panel === 'bundles' && <BundleDesigner presets={presets} onDeploy={goDeploy} />}
        {panel === 'deploy' && <DeployCenter initialBundleId={deployBundleId} />}
      </div>
    </div>
  );
}
