/**
 * 发布中心 — Bundle → Docker 容器.
 *
 * 五阶段：解析 → 校验 → 写入 → 重启 → 回读校验
 *
 * 必须让用户看清的两件事：
 * 1. **发布会重启容器内 opencode**（实测 PATCH /config 不生效、写文件不热感知，
 *    只有重启这条路），会中断进行中的会话 → 显式勾选确认
 * 2. **回读校验结果**：期望 vs 容器实际。不做 fire-and-forget，
 *    发布完到底生效没有必须可证伪。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App,
  Alert,
  Button,
  Checkbox,
  Descriptions,
  Divider,
  Empty,
  Modal,
  Select,
  Space,
  Steps,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloudUploadOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import useComputeStore, { extractErrMsg } from '../../stores/computeStore';
import * as svc from '../../services/agentFactory.service';
import type {
  AgentBundle,
  Deployment,
  DeployScope,
  PreviewResponse,
} from '../../types/agentFactory';
import { deployStatusColor, deployStatusLabel } from '../../types/agentFactory';
import { ArtifactPreview, ArtifactTree, VerifyIcon } from './shared';

const { Text } = Typography;

const SCOPE_HINT: Record<DeployScope, string> = {
  global: '/root/.config/opencode —— 对该容器内所有项目生效（推荐）',
  project: '/workspace/.opencode —— 只对该工作区生效',
};

interface Props {
  /** 从编排页「去发布」带过来的 bundle */
  initialBundleId?: number | null;
}

export default function DeployCenter({ initialBundleId }: Props) {
  const { notification } = App.useApp();
  const { nodes, containers, selectedNode, fetchNodes, fetchContainers, ensureLocalNode } =
    useComputeStore();

  const [bundles, setBundles] = useState<AgentBundle[]>([]);
  const [bundleId, setBundleId] = useState<number | undefined>(initialBundleId ?? undefined);
  const [nodeId, setNodeId] = useState<number | undefined>();
  const [containerId, setContainerId] = useState<string | undefined>();
  const [scope, setScope] = useState<DeployScope>('global');
  const [prune, setPrune] = useState(true);
  const [restartOk, setRestartOk] = useState(false);

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewPath, setPreviewPath] = useState('');
  const [prevDeploy, setPrevDeploy] = useState<Deployment | null>(null);

  const [deploying, setDeploying] = useState(false);
  const [result, setResult] = useState<Deployment | null>(null);
  const [history, setHistory] = useState<Deployment[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<Deployment | null>(null);

  const loadBase = useCallback(async () => {
    try {
      const [b, h] = await Promise.all([svc.listBundles(), svc.listDeployments()]);
      setBundles(b);
      setHistory(h);
    } catch (err) {
      notification.error({ title: '加载失败', description: extractErrMsg(err) });
    }
  }, [notification]);

  useEffect(() => {
    void loadBase();
    void fetchNodes();
    void ensureLocalNode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (initialBundleId) setBundleId(initialBundleId);
  }, [initialBundleId]);

  // 默认选中本地节点
  useEffect(() => {
    if (!nodeId && (selectedNode || nodes.length)) {
      setNodeId(selectedNode?.id ?? nodes[0]?.id);
    }
  }, [nodeId, selectedNode, nodes]);

  useEffect(() => {
    if (nodeId) void fetchContainers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeId]);

  // 产物预览 + 上次发布（用于 diff）
  useEffect(() => {
    if (!bundleId) {
      setPreview(null);
      return;
    }
    void (async () => {
      try {
        const p = await svc.previewBundle(bundleId);
        setPreview(p);
        setPreviewPath((cur) => cur || p.artifacts[0]?.path || '');
      } catch (err) {
        notification.error({ title: '预览失败', description: extractErrMsg(err) });
      }
    })();
  }, [bundleId, notification]);

  useEffect(() => {
    if (!bundleId || !containerId) {
      setPrevDeploy(null);
      return;
    }
    const hit = history.find(
      (d) => d.bundle_id === bundleId && d.container_id.startsWith(containerId.slice(0, 12)),
    );
    setPrevDeploy(hit ?? null);
  }, [bundleId, containerId, history]);

  /** 与上次发布对比，标出新增/修改/未变 */
  const diffMap = useMemo(() => {
    const out: Record<string, 'new' | 'changed' | 'same'> = {};
    if (!preview) return out;
    const prevHashes = new Map(
      (prevDeploy?.artifacts_json?.files ?? []).map((f) => [f.path, f.sha256]),
    );
    preview.artifacts.forEach((a) => {
      const ph = prevHashes.get(a.path);
      out[a.path] = ph === undefined ? 'new' : ph === a.sha256 ? 'same' : 'changed';
    });
    return out;
  }, [preview, prevDeploy]);

  const orphans = useMemo(() => {
    if (!preview || !prevDeploy) return [];
    const cur = new Set(preview.artifacts.map((a) => a.path));
    return (prevDeploy.artifacts_json?.files ?? [])
      .map((f) => f.path)
      .filter((p) => !cur.has(p));
  }, [preview, prevDeploy]);

  const runningContainers = useMemo(
    () => containers.filter((c) => c.status === 'running'),
    [containers],
  );

  const canDeploy = !!bundleId && !!nodeId && !!containerId && restartOk && !deploying;

  const doDeploy = async () => {
    if (!bundleId || !nodeId || !containerId) return;
    setDeploying(true);
    setResult(null);
    try {
      const d = await svc.deployBundle(bundleId, {
        node_id: nodeId,
        container_id: containerId,
        scope,
        restart_confirmed: true,
        prune,
      });
      setResult(d);
      await loadBase();
      if (d.status === 'success') {
        notification.success({
          title: '发布成功',
          description: `${d.bundle_name} → ${d.container_name}，回读校验全部一致`,
          duration: 6,
        });
      } else {
        notification.warning({
          title: `发布${deployStatusLabel[d.status]}`,
          description: d.error_detail ?? '请查看下方校验结果',
          duration: 12,
        });
      }
    } catch (err) {
      notification.error({ title: '发布失败', description: extractErrMsg(err), duration: 15 });
    } finally {
      setDeploying(false);
    }
  };

  const reverify = async (id: number) => {
    try {
      const d = await svc.reverifyDeployment(id);
      notification.success({
        title: '已重新校验',
        description: `${d.verify_json?.summary.matched}/${d.verify_json?.summary.total} 一致`,
      });
      if (result?.id === id) setResult(d);
      if (detail?.id === id) setDetail(d);
      await loadBase();
    } catch (err) {
      notification.error({ title: '校验失败', description: extractErrMsg(err), duration: 10 });
    }
  };

  /** 五阶段进度：由最终 status 反推走到了哪一步 */
  const stepIndex = (s?: string) => {
    switch (s) {
      case 'validating':
        return 1;
      case 'writing':
        return 2;
      case 'reloading':
        return 3;
      case 'verifying':
        return 4;
      case 'success':
      case 'partial':
        return 5;
      case 'failed':
        return 2;
      default:
        return 0;
    }
  };

  const historyColumns: ColumnsType<Deployment> = [
    {
      title: '方案',
      key: 'bundle',
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Text style={{ fontSize: 12.5 }}>{r.bundle_name}</Text>
          <Text type="secondary" style={{ fontSize: 10.5 }}>
            v{r.bundle_version} → {r.container_name} ({r.scope})
          </Text>
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Tag color={deployStatusColor[r.status]} style={{ margin: 0 }}>
            {deployStatusLabel[r.status]}
          </Tag>
          {r.verify_json && (
            <Text type="secondary" style={{ fontSize: 10.5 }}>
              校验 {r.verify_json.summary.matched}/{r.verify_json.summary.total}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '产物',
      key: 'artifacts',
      width: 110,
      render: (_, r) =>
        r.artifacts_json ? (
          <Text style={{ fontSize: 11.5 }}>
            写 {r.artifacts_json.written} / 跳 {r.artifacts_json.skipped}
            {r.artifacts_json.pruned?.length ? ` / 清 ${r.artifacts_json.pruned.length}` : ''}
          </Text>
        ) : (
          '—'
        ),
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      width: 76,
      render: (v: number | null) => (v ? `${(v / 1000).toFixed(1)}s` : '—'),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 150,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '—'),
    },
    {
      title: '',
      key: 'act',
      width: 130,
      render: (_, r) => (
        <Space size={2}>
          <Button
            size="small"
            type="link"
            onClick={() => {
              setDetail(r);
              setDetailOpen(true);
            }}
          >
            详情
          </Button>
          <Tooltip title="重新回读校验（不重写、不重启）">
            <Button size="small" type="text" icon={<ReloadOutlined />} onClick={() => void reverify(r.id)} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const shown = result ?? null;

  return (
    <div style={{ padding: '14px 16px' }}>{/* 【UI 重构】参照左侧栏 14px 垂直内边距 */}
      {/* ---------- 发布配置 ---------- */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 16 }}>
        <div style={{ flex: 1, minWidth: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: 16 }}>
          <Space size={12} wrap align="start" style={{ marginBottom: 12 }}>
            <div>
              <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                编排方案 <Text type="danger">*</Text>
              </Text>
              <Select
                size="small"
                style={{ width: 220 }}
                placeholder="选择要发布的方案"
                value={bundleId}
                onChange={setBundleId}
                options={bundles.map((b) => ({
                  value: b.id,
                  label: `${b.name} (${b.members.length} 成员)`,
                }))}
              />
            </div>
            <div>
              <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                目标节点 <Text type="danger">*</Text>
              </Text>
              <Select
                size="small"
                style={{ width: 150 }}
                value={nodeId}
                onChange={setNodeId}
                options={nodes.map((n) => ({ value: n.id, label: n.name }))}
              />
            </div>
            <div>
              <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                目标容器 <Text type="danger">*</Text>
              </Text>
              <Select
                size="small"
                style={{ width: 220 }}
                placeholder="选择运行中的容器"
                value={containerId}
                onChange={setContainerId}
                options={runningContainers.map((c) => ({
                  value: c.id,
                  label: `${c.name} · ${c.ports || '无端口映射'}`,
                }))}
                notFoundContent={
                  <div style={{ padding: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      没有运行中的容器
                    </Text>
                  </div>
                }
              />
            </div>
            <div>
              <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                <Tooltip title={SCOPE_HINT[scope]}>写入范围</Tooltip>
              </Text>
              <Select
                size="small"
                style={{ width: 130 }}
                value={scope}
                onChange={(v) => setScope(v)}
                options={[
                  { value: 'global', label: '容器全局' },
                  { value: 'project', label: '项目级' },
                ]}
              />
            </div>
          </Space>

          <Text type="secondary" style={{ fontSize: 11.5, display: 'block', marginBottom: 10 }}>
            目标目录：<Text code>{scope === 'global' ? '/root/.config/opencode' : '/workspace/.opencode'}</Text>
          </Text>

          {/* 重启确认 —— 必须显式勾选 */}
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 10 }}
            title="发布会重启容器内的 opencode 服务"
            description={
              <div style={{ fontSize: 12 }}>
                <p style={{ margin: '0 0 6px' }}>
                  实测：<Text code>PATCH /config</Text> 返回 200 但不生效，写文件也不会被热感知 ——
                  <b>只有重启才能让新 agent/skill 生效</b>。重启会中断该容器里正在进行的会话。
                </p>
                <Checkbox checked={restartOk} onChange={(e) => setRestartOk(e.target.checked)}>
                  我已确认，可以重启
                </Checkbox>
              </div>
            }
          />

          <Space size={10} style={{ marginBottom: 12 }}>
            <Checkbox checked={prune} onChange={(e) => setPrune(e.target.checked)}>
              <Tooltip title="清理本方案上次发布过、本次已移除的产物，避免容器里留下「孤儿 agent」">
                <Text style={{ fontSize: 12.5 }}>清理孤儿产物</Text>
              </Tooltip>
            </Checkbox>
            {orphans.length > 0 && (
              <Text type="warning" style={{ fontSize: 11.5 }}>
                将清理 {orphans.length} 个：{orphans.join(', ')}
              </Text>
            )}
          </Space>

          <div>
            <Button
              type="primary"
              size="middle"
              icon={<RocketOutlined />}
              loading={deploying}
              disabled={!canDeploy}
              onClick={() => void doDeploy()}
            >
              {deploying ? '发布中…' : '开始发布'}
            </Button>
            {!restartOk && (
              <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 10 }}>
                需先勾选「我已确认，可以重启」
              </Text>
            )}
          </div>
        </div>

        {/* 产物 diff 预览 */}
        <div style={{ width: 340, flexShrink: 0, background: '#FFFFFF', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', padding: 12, maxHeight: 'calc(100vh - 140px)', display: 'flex', flexDirection: 'column' }}>
          <Space size={6} style={{ marginBottom: 6 }}>
            <CloudUploadOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
            <Text strong style={{ fontSize: 13 }}>
              将写入的产物
            </Text>
            {preview && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                {preview.artifacts.length} 个文件
              </Text>
            )}
          </Space>
          {preview ? (
            <>
              <ArtifactTree
                artifacts={preview.artifacts}
                selected={previewPath}
                onSelect={setPreviewPath}
                diffMap={diffMap}
              />
              <Divider style={{ margin: '8px 0' }} />
              <ArtifactPreview
                artifact={
                  preview.artifacts.find((a) => a.path === previewPath) ?? preview.artifacts[0]
                }
                maxHeight={220}
              />
            </>
          ) : (
            <Alert
              type="info"
              showIcon
              title="选择编排方案"
              description={
                <span style={{ fontSize: 12 }}>
                  选定后这里会列出将写入容器的全部文件，并与上次发布做 diff。
                </span>
              }
            />
          )}
        </div>
      </div>

      {/* ---------- 本次发布结果 ---------- */}
      {(deploying || shown) && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <Steps
            size="small"
            current={deploying ? 2 : stepIndex(shown?.status)}
            status={shown?.status === 'failed' ? 'error' : shown?.status === 'partial' ? 'finish' : undefined}
            style={{ marginBottom: 14 }}
            items={[
              { title: '解析' },
              { title: '校验' },
              { title: '写入' },
              { title: '重启' },
              { title: '回读校验' },
            ]}
          />
          {shown && <DeployResultPanel d={shown} onReverify={() => void reverify(shown.id)} />}
        </>
      )}

      {/* ---------- 历史 ---------- */}
      <Divider style={{ margin: '14px 0 10px' }} />
      <Space size={8} style={{ marginBottom: 8 }}>
        <Text strong style={{ fontSize: 13 }}>
          发布历史
        </Text>
        <Button size="small" icon={<ReloadOutlined />} onClick={() => void loadBase()}>
          刷新
        </Button>
      </Space>
      <Table<Deployment>
        size="small"
        rowKey="id"
        columns={historyColumns}
        dataSource={history}
        pagination={{ pageSize: 8, size: 'small' }}
        locale={{
          emptyText: (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有发布记录" />
          ),
        }}
      />

      {/* 详情 Modal */}
      <Modal
        title={`发布详情 · ${detail?.bundle_name ?? ''}`}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={780}
        destroyOnHidden
      >
        {detail && <DeployResultPanel d={detail} onReverify={() => void reverify(detail.id)} />}
      </Modal>
    </div>
  );
}

/** 发布结果面板（本次结果与历史详情共用） */
function DeployResultPanel({ d, onReverify }: { d: Deployment; onReverify: () => void }) {
  const v = d.verify_json;
  const a = d.artifacts_json;

  return (
    <div>
      <Descriptions
        size="small"
        column={3}
        bordered
        style={{ marginBottom: 12 }}
        items={[
          {
            key: 'status',
            label: '状态',
            children: (
              <Tag color={deployStatusColor[d.status]} style={{ margin: 0 }}>
                {deployStatusLabel[d.status]}
              </Tag>
            ),
          },
          { key: 'target', label: '容器', children: d.container_name },
          {
            key: 'dur',
            label: '耗时',
            children: d.duration_ms ? `${(d.duration_ms / 1000).toFixed(1)}s` : '—',
          },
          { key: 'dir', label: '目录', children: <Text code style={{ fontSize: 11 }}>{d.target_dir}</Text>, span: 2 },
          {
            key: 'restart',
            label: '已重启',
            children: d.restart_used ? '是' : '否',
          },
        ]}
      />

      {d.error_detail && (
        <Alert
          type={d.status === 'failed' ? 'error' : 'warning'}
          showIcon
          style={{ marginBottom: 12 }}
          title={d.status === 'failed' ? '发布失败' : '部分不一致'}
          description={<span style={{ fontSize: 12 }}>{d.error_detail}</span>}
        />
      )}

      {/* 产物 */}
      {a && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 13 }}>
            产物：写入 {a.written} · 跳过 {a.skipped}
            {a.pruned?.length ? ` · 清理 ${a.pruned.length}` : ''}
          </Text>
          <div style={{ marginTop: 4 }}>
            {a.files.map((f) => (
              <div key={f.path} style={{ display: 'flex', gap: 8, fontSize: 11.5 }}>
                <Text style={{ fontFamily: 'monospace', flex: 1 }}>{f.path}</Text>
                <Text type="secondary">{f.bytes}B</Text>
                {f.skipped && (
                  <Tag style={{ fontSize: 10, margin: 0 }}>未变</Tag>
                )}
              </div>
            ))}
            {a.pruned?.map((p) => (
              <div key={p} style={{ fontSize: 11.5 }}>
                <Text delete type="secondary" style={{ fontFamily: 'monospace' }}>
                  {p}
                </Text>{' '}
                <Tag color="orange" style={{ fontSize: 10, margin: 0 }}>
                  已清理
                </Tag>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 回读校验 —— 发布结果的可证伪凭证 */}
      {v && (
        <div>
          <Space size={8} style={{ marginBottom: 6 }}>
            <Text strong style={{ fontSize: 13 }}>
              回读校验
            </Text>
            {v.summary.all_match ? (
              <Space size={4}>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <Text type="success" style={{ fontSize: 12 }}>
                  {v.summary.matched}/{v.summary.total} 全部一致
                </Text>
              </Space>
            ) : (
              <Space size={4}>
                <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                <Text type="warning" style={{ fontSize: 12 }}>
                  {v.summary.matched}/{v.summary.total} 一致
                </Text>
              </Space>
            )}
            <Button size="small" icon={<ReloadOutlined />} onClick={onReverify}>
              重新校验
            </Button>
          </Space>

          {v.reload?.control_url && (
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 6 }}>
              控制面：<Text code style={{ fontSize: 10.5 }}>{v.reload.control_url}/agent</Text>
              {v.reload.listening === false && (
                <Text type="warning"> · 端口未恢复监听</Text>
              )}
            </Text>
          )}
          {v.summary.agent_probe_error && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 8 }}
              title="无法回读 agent"
              description={<span style={{ fontSize: 12 }}>{v.summary.agent_probe_error}</span>}
            />
          )}

          <Table
            size="small"
            rowKey={(r) => `${r.kind}-${r.name}`}
            pagination={false}
            dataSource={v.items}
            columns={[
              {
                title: '类型',
                dataIndex: 'kind',
                width: 66,
                render: (k: string) => (
                  <Tag style={{ fontSize: 10, margin: 0 }}>{k === 'agent' ? 'Agent' : 'Skill'}</Tag>
                ),
              },
              {
                title: '名称',
                dataIndex: 'name',
                width: 150,
                render: (n: string) => (
                  <Text style={{ fontSize: 12, fontFamily: 'monospace' }}>{n}</Text>
                ),
              },
              {
                title: '容器实际',
                dataIndex: 'match',
                width: 90,
                render: (m: boolean) => (
                  <Space size={4}>
                    <VerifyIcon match={m} />
                    <Text style={{ fontSize: 12 }}>{m ? '一致' : '不一致'}</Text>
                  </Space>
                ),
              },
              {
                title: '说明',
                dataIndex: 'detail',
                ellipsis: true,
                render: (t: string | null) =>
                  t ? (
                    <Tooltip title={t} styles={{ root: { maxWidth: 420 } }}>
                      <Text style={{ fontSize: 11.5 }}>{t}</Text>
                    </Tooltip>
                  ) : (
                    <Text type="secondary" style={{ fontSize: 11.5 }}>
                      —
                    </Text>
                  ),
              },
            ]}
          />
        </div>
      )}
    </div>
  );
}
