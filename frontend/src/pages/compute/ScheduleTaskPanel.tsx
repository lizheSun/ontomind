/**
 * ScheduleTaskPanel — 调度任务管理.
 * 列表 + 创建/编辑/删除 + 触发 + 运行记录 + 日志查看.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  App, Button, Drawer, Empty, Form, Input, InputNumber, Modal,
  Popconfirm, Select, Space, Spin, Table, Tag, Tooltip, Typography,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, PlayCircleOutlined,
  EditOutlined, DeleteOutlined, PauseCircleOutlined, CaretRightOutlined,
  FileTextOutlined, StopOutlined,
} from '@ant-design/icons';
import { computeService, type ScheduleTask, type TaskRun, type TaskLogEntry } from '../../services/compute.service';

const { Text } = Typography;

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  idle:     { color: '#8f8b84', label: '空闲' },
  running:  { color: '#476a4b', label: '运行中' },
  pending:  { color: '#a86e12', label: '等待中' },
  success:  { color: '#476a4b', label: '成功' },
  failed:   { color: '#a5361e', label: '失败' },
  cancelled: { color: '#8f8b84', label: '已取消' },
  timeout:  { color: '#a86e12', label: '超时' },
  paused:   { color: '#a86e12', label: '暂停' },
  disabled: { color: '#bfbcb5', label: '禁用' },
};

interface FormValues {
  id?: number;
  name: string;
  schedule_type: 'manual' | 'once' | 'interval' | 'cron';
  schedule_expr?: string;
  description?: string;
  docker_service_id?: number;
  prompt: string;
  agent: string;
  model?: string;
  system?: string;
  timeout_seconds: number;
}

export default function ScheduleTaskPanel() {
  const { message } = App.useApp();
  const [tasks, setTasks] = useState<ScheduleTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<ScheduleTask | null>(null);
  const [form] = Form.useForm<FormValues>();

  // 运行记录 & 日志
  const [runsModal, setRunsModal] = useState<{ taskId: number; taskName: string } | null>(null);
  const [runs, setRuns] = useState<TaskRun[]>([]);
  const [runsLoading] = useState(false);
  const [logModal, setLogModal] = useState<{ runId: number; runStatus: string } | null>(null);
  const [logs, setLogs] = useState<TaskLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const logTailRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTasks(await computeService.listTasks());
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally { setLoading(false); }
  }, [message]);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 8000);
    return () => window.clearInterval(t);
  }, [load]);

  // 中断时自动加载 runs
  useEffect(() => {
    if (!runsModal) return;
    const loadRuns = async () => {
      try {
        const list = await computeService.listTaskRuns(runsModal.taskId);
        setRuns(list);
      } catch { /* silent */ }
    };
    loadRuns();
    const t = window.setInterval(loadRuns, 5000);
    return () => window.clearInterval(t);
  }, [runsModal]);

  // 日志自动滚动
  useEffect(() => {
    logTailRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      schedule_type: 'manual', timeout_seconds: 600, agent: 'build',
      prompt: '',
    });
    setDrawerOpen(true);
  };

  const openEdit = (t: ScheduleTask) => {
    setEditing(t);
    const cfg = t.opencode_config || {};
    form.resetFields();
    form.setFieldsValue({
      id: t.id, name: t.name, description: t.description ?? '',
      schedule_type: t.schedule_type, schedule_expr: t.schedule_expr ?? '',
      docker_service_id: t.docker_service_id ?? undefined,
      prompt: String(cfg.prompt || cfg.message || ''),
      agent: String(cfg.agent || 'build'),
      model: String(cfg.model || ''),
      system: String(cfg.system || ''),
      timeout_seconds: t.timeout_seconds,
    });
    setDrawerOpen(true);
  };

  const doTrigger = async (t: ScheduleTask) => {
    try {
      const run = await computeService.triggerTask(t.id);
      message.success(`已触发，运行 ID: ${run.id}`);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '触发失败');
    }
  };

  const doToggle = async (t: ScheduleTask, enabled: boolean) => {
    try {
      await computeService.toggleTask(t.id, enabled);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '操作失败');
    }
  };

  const doDelete = async () => {
    if (!editing) return;
    try {
      await computeService.deleteTask(editing.id);
      message.success('已删除');
      setDrawerOpen(false); setEditing(null);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const submitForm = async () => {
    const v = await form.validateFields();
    const opencodeConfig: Record<string, unknown> = {
      prompt: v.prompt,
      agent: v.agent,
    };
    if (v.model) opencodeConfig.model = v.model;
    if (v.system) opencodeConfig.system = v.system;
    const payload = {
      name: v.name, description: v.description || null,
      schedule_type: v.schedule_type, schedule_expr: v.schedule_expr || null,
      docker_service_id: v.docker_service_id || null,
      opencode_config: opencodeConfig,
      timeout_seconds: v.timeout_seconds,
    };
    try {
      if (editing) {
        await computeService.updateTask(editing.id, payload);
      } else {
        await computeService.createTask(payload);
      }
      message.success('保存成功');
      setDrawerOpen(false); setEditing(null);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    }
  };

  const openRuns = (t: ScheduleTask) => {
    setRunsModal({ taskId: t.id, taskName: t.name });
    setRuns([]);
  };

  const openLogs = async (run: TaskRun) => {
    setLogModal({ runId: run.id, runStatus: run.status });
    setLogsLoading(true);
    try {
      setLogs(await computeService.getRunLogs(run.id, 0));
    } catch { /* silent */ }
    finally { setLogsLoading(false); }
  };

  const loadMoreLogs = async () => {
    if (!logModal) return;
    const maxSeq = logs.reduce((m, l) => Math.max(m, l.sequence), 0);
    try {
      const more = await computeService.getRunLogs(logModal.runId, maxSeq);
      if (more.length > 0) setLogs((prev) => [...prev, ...more]);
    } catch { /* silent */ }
  };

  const runColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60, render: (v: number) => `#${v}` },
    { title: '触发', dataIndex: 'trigger', key: 'trigger', width: 80 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => {
        const m = STATUS_MAP[s];
        return <Tag color={m?.color}>{m?.label || s}</Tag>;
      },
    },
    { title: '开始', dataIndex: 'started_at', key: 'started_at', width: 180,
      render: (v: string) => v ? new Date(v).toLocaleString() : '-',
    },
    { title: '耗时', dataIndex: 'duration_ms', key: 'duration_ms', width: 80,
      render: (v: number) => v != null ? `${(v / 1000).toFixed(1)}s` : '-',
    },
    { title: '输出', dataIndex: 'output_summary', key: 'output_summary', ellipsis: true,
      render: (v: string) => v?.slice(0, 100) || '-',
    },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_: unknown, r: TaskRun) => (
        <Space>
          <Tooltip title="查看日志">
            <Button size="small" icon={<FileTextOutlined />} onClick={() => void openLogs(r)} />
          </Tooltip>
          {(r.status === 'pending' || r.status === 'running') && (
            <Tooltip title="取消运行">
              <Button size="small" icon={<StopOutlined />} onClick={async () => {
                await computeService.cancelRun(r.id);
                message.success('已取消');
              }} />
            </Tooltip>
          )}
          {r.opencode_session_id && (
            <Tag style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>
              {r.opencode_session_id.slice(0, 12)}
            </Tag>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 16, gap: 12,
      }}>
        <Text style={{ color: 'var(--ink-40)', fontSize: 12 }}>
          共 {tasks.length} 个任务 · 运行 {tasks.filter((t) => t.status === 'running').length}
        </Text>
        <Space>
          <Tooltip title="刷新"><Button icon={<ReloadOutlined />} onClick={() => void load()} /></Tooltip>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>创建任务</Button>
        </Space>
      </div>

      {loading && tasks.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center' }}><Spin /></div>
      ) : tasks.length === 0 ? (
        <div style={{ padding: '60px 24px', textAlign: 'center', border: '1px dashed var(--border-subtle)', borderRadius: 14 }}>
          <Empty description={<span style={{ color: 'var(--ink-60)' }}>暂无调度任务</span>} />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 16 }}>
          {tasks.map((t) => {
            const s = STATUS_MAP[t.status] || STATUS_MAP.idle;
            const cfg = t.opencode_config || {};
            return (
              <div
                key={t.id}
                style={{
                  background: 'var(--paper-00)', border: '1px solid var(--border-subtle)',
                  borderRadius: 14, padding: 20, position: 'relative',
                  display: 'flex', flexDirection: 'column', gap: 8,
                  opacity: t.enabled ? 1 : 0.55,
                  transition: 'border-color .12s, box-shadow .12s',
                }}
                onMouseEnter={(ev) => { ev.currentTarget.style.borderColor = 'var(--border-default)'; }}
                onMouseLeave={(ev) => { ev.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
              >
                <span style={{
                  position: 'absolute', top: 16, right: 16,
                  fontSize: 11, color: s.color, fontWeight: 500,
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.color }} />
                  {s.label}
                </span>

                <div style={{ fontFamily: 'var(--font-serif)', fontSize: 17, fontWeight: 500, color: 'var(--ink-100)', letterSpacing: '-0.01em' }}>
                  {t.name}
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  <Tag style={{ fontSize: 10 }}>{t.schedule_type}</Tag>
                  {t.schedule_expr && <Tag style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{t.schedule_expr}</Tag>}
                  {String(cfg.agent || '') && <Tag style={{ fontSize: 10 }}>agent: {String(cfg.agent)}</Tag>}
                </div>

                <div style={{ fontSize: 11, color: 'var(--ink-40)', marginTop: 4 }}>
                  {t.total_runs > 0 ? `${t.total_runs} 次运行 · 成功 ${t.success_runs} · 失败 ${t.failed_runs}` : '暂未运行'}
                </div>

                <div style={{
                  marginTop: 'auto', display: 'flex', gap: 6, flexWrap: 'wrap',
                  paddingTop: 10, borderTop: '1px solid var(--border-hairline)',
                }}>
                  <Button type="primary" size="small" icon={<PlayCircleOutlined />}
                    onClick={() => void doTrigger(t)}>执行</Button>
                  <Button size="small" icon={<FileTextOutlined />}
                    onClick={() => openRuns(t)}>运行记录</Button>
                  <Button size="small" icon={<EditOutlined />}
                    onClick={() => openEdit(t)}>编辑</Button>
                  {t.schedule_type === 'interval' && (
                    t.enabled
                      ? <Button size="small" icon={<PauseCircleOutlined />}
                          onClick={() => void doToggle(t, false)}>暂停</Button>
                      : <Button size="small" icon={<CaretRightOutlined />}
                          onClick={() => void doToggle(t, true)}>启用</Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Drawer
        title={editing ? `编辑：${editing.name}` : '创建调度任务'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={560}
        footer={
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <div>
              {editing && (
                <Popconfirm title={`确认删除 ${editing.name}？`} onConfirm={() => void doDelete()}>
                  <Button danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              )}
            </div>
            <Space>
              <Button onClick={() => setDrawerOpen(false)}>取消</Button>
              <Button type="primary" onClick={() => void submitForm()}>保存</Button>
            </Space>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
            <Input placeholder="每日数据同步" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="schedule_type" label="调度类型" style={{ flex: 1, marginBottom: 12 }}>
              <Select>
                <Select.Option value="manual">手动 (manual)</Select.Option>
                <Select.Option value="once">一次 (once)</Select.Option>
                <Select.Option value="interval">间隔 (interval)</Select.Option>
                <Select.Option value="cron">Cron</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="schedule_expr" label="调度表达式" style={{ flex: 2, marginBottom: 12 }}
              tooltip="interval: 秒数; once: ISO 时间戳; cron: 标准 cron 表达式">
              <Input placeholder="*/5 * * * * / 600 / 2026-08-01T00:00:00Z" />
            </Form.Item>
          </Space>
          <Form.Item name="timeout_seconds" label="超时 (秒)">
            <InputNumber style={{ width: '100%' }} min={1} max={86400} />
          </Form.Item>
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: 13, fontWeight: 500,
            color: 'var(--ink-40)', textTransform: 'uppercase',
            letterSpacing: '0.06em', margin: '20px 0 12px',
          }}>OpenCode 调用配置</div>
          <Form.Item name="agent" label="Agent">
            <Input placeholder="build / data-analyst / product-manager" />
          </Form.Item>
          <Form.Item name="model" label="模型 (可选 provider/modelID)">
            <Input placeholder="agent-plan/ark-code-latest" />
          </Form.Item>
          <Form.Item name="system" label="System Prompt (可选)">
            <Input.TextArea rows={3}
              style={{ fontFamily: 'var(--font-sans)', fontSize: 13 }}
              placeholder="可选的专家 system prompt，为空则使用 agent 默认"
            />
          </Form.Item>
          <Form.Item name="prompt" label="消息内容" rules={[{ required: true, message: '请输入消息内容' }]}>
            <Input.TextArea rows={6}
              style={{ fontFamily: 'var(--font-sans)', fontSize: 13 }}
              placeholder="给 opencode 发送的消息内容"
            />
          </Form.Item>
        </Form>
      </Drawer>

      {/* 运行记录 Modal */}
      <Modal
        open={!!runsModal}
        onCancel={() => setRunsModal(null)}
        footer={null}
        title={`运行记录：${runsModal?.taskName}`}
        width={960}
      >
        <Table
          rowKey="id"
          columns={runColumns}
          dataSource={runs}
          loading={runsLoading}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Modal>

      {/* 日志 Modal */}
      <Modal
        open={!!logModal}
        onCancel={() => setLogModal(null)}
        footer={null}
        title={`运行日志 #${logModal?.runId}`}
        width={860}
        afterOpenChange={(open) => {
          if (open) { const t = setInterval(loadMoreLogs, 3000); return () => clearInterval(t); }
        }}
      >
        {logsLoading && logs.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div>
        ) : (
          <div style={{ maxHeight: 500, overflow: 'auto', background: 'var(--paper-02)', padding: 12, borderRadius: 6 }}>
            {logs.map((l) => (
              <div key={l.id} style={{
                fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.6,
                color: l.level === 'error' || l.level === 'stderr' ? '#a5361e'
                     : l.level === 'warn' ? '#a86e12'
                     : l.level === 'event' ? '#3b52af'
                     : 'var(--ink-80)',
              }}>
                <span style={{ color: 'var(--ink-40)', marginRight: 8 }}>
                  {String(l.sequence).padStart(4, ' ')}
                </span>
                {l.message}
              </div>
            ))}
            <div ref={logTailRef} />
          </div>
        )}
      </Modal>
    </div>
  );
}