/**
 * SchedulerPanel — 调度运行.
 *
 * 双视图（顶部切换器）：任务管理 / 运行记录（全局）。
 * 每个视图均有搜索 + chips 勾选/下拉过滤。
 * 日志弹窗增量 GET /compute/runs/{id}/logs?since_line=…  3s 轮询。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Button, Drawer, Form, Input, Modal, Popconfirm, Radio,
  Select, Space, Switch, Table, Tag, Tooltip, message,
} from 'antd';
import {
  DeleteOutlined, FileTextOutlined, PlusOutlined,
  ReloadOutlined, SearchOutlined, ThunderboltOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import LogViewer from './LogViewer';
import type { LogLine, SchedulerTask, TaskRunRecord } from './types';
import { fmtDateTime, fmtDuration } from './mock';
import * as srv from '../../services/compute.service';

const TASK_STATUS_STYLE: Record<string, { color: string; dot: string; label: string }> = {
  idle:     { color: '#8f8b84', dot: '#bfbcb5', label: '空闲' },
  running:  { color: '#476a4b', dot: '#22c55e', label: '运行中' },
  paused:   { color: '#8f8b84', dot: '#bfbcb5', label: '已暂停' },
  disabled: { color: '#bfbcb5', dot: '#bfbcb5', label: '已停用' },
};
const RUN_STATUS_STYLE: Record<string, string> = {
  running: '#476a4b',
  success: '#476a4b',
  failed:  '#a5361e',
  canceled:'#8f8b84',
};

const VIEWS = ['tasks', 'runs'] as const;
type View = (typeof VIEWS)[number];

// --- 任务表单 ---
interface TaskFormValues {
  name: string; description?: string; command: string;
  logDir: string; scheduleType: string; scheduleExpr?: string; enabled: boolean;
}

const initTaskForm: TaskFormValues = {
  name: '', description: '', command: '',
  logDir: '/var/log/ontomind/tasks', scheduleType: 'manual',
  scheduleExpr: '', enabled: true,
};

const SCHEDULE_TYPE_LABEL: Record<string, string> = {
  manual: '手动', once: '一次性', interval: '间隔', cron: 'Cron',
};

// --- 获取/刷新任务的 hook ---
function useTasks() {
  const [list, setList] = useState<SchedulerTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async (params: srv.TaskListParams = {}) => {
    setLoading(true);
    setError(null);
    try {
      const tasks = await srv.fetchTasks(params);
      setList(tasks);
    } catch (e: any) {
      const msg = e?.response?.data?.message ?? e?.message ?? '获取任务失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return { list, loading, error, reload, setList };
}

// --- 获取/刷新运行记录的 hook ---
function useRuns() {
  const [list, setList] = useState<TaskRunRecord[]>([]);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async (params: srv.RunListParams = {}) => {
    setLoading(true);
    try {
      const runs = await srv.fetchRuns(params);
      setList(runs);
    } catch {
      // 静默
    } finally {
      setLoading(false);
    }
  }, []);

  return { list, loading, reload, setList };
}

// =========================================================================

export default function SchedulerPanel() {
  // -- 视图
  const [view, setView] = useState<View>('tasks');
  // -- 数据
  const { list: tasks, loading: tasksLoading, reload: reloadTasks, setList: setTasks } = useTasks();
  const { list: allRuns, loading: runsLoading, reload: reloadRuns, setList: setRuns } = useRuns();

  // -- 任务筛选
  const [taskSearch, setTaskSearch] = useState('');
  const [taskTypeFilter, setTaskTypeFilter] = useState<string[]>([]);
  // -- 运行记录筛选
  const [runSearch, setRunSearch] = useState('');
  const [runStatusChips, setRunStatusChips] = useState<Set<string>>(new Set());
  const [runTaskFilter, setRunTaskFilter] = useState<number | null>(null);
  const [runTriggerFilter, setRunTriggerFilter] = useState<string | null>(null);

  // -- 任务编辑抽屉
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<SchedulerTask | null>(null);
  const [taskForm] = Form.useForm<TaskFormValues>();

  // -- 日志 Modal
  const [logsModal, setLogsModal] = useState<{ taskName: string; runId: number; logFile: string; lines: LogLine[]; status: string } | null>(null);
  const logsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const logsSinceRef = useRef(0);

  // -- 操作中
  const [operating, setOperating] = useState<Set<number>>(new Set());

  // ===== 初始化加载 =====
  useEffect(() => { void reloadTasks(); void reloadRuns(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ===== 计算派生数据 =====
  const filteredTasks = useMemo(() => {
    let result = tasks;
    if (taskSearch) {
      const s = taskSearch.toLowerCase();
      result = result.filter((t) =>
        t.name.toLowerCase().includes(s) ||
        t.command.toLowerCase().includes(s) ||
        String(t.id).includes(s),
      );
    }
    if (taskTypeFilter.length > 0) {
      result = result.filter((t) => taskTypeFilter.includes(t.scheduleType));
    }
    return result;
  }, [tasks, taskSearch, taskTypeFilter]);

  const filteredRuns = useMemo(() => {
    let result = allRuns;
    if (runSearch) {
      const s = runSearch.toLowerCase();
      result = result.filter((r) =>
        r.logFile.toLowerCase().includes(s) ||
        String(r.id).includes(s),
      );
    }
    if (runStatusChips.size > 0) {
      result = result.filter((r) => runStatusChips.has(r.status));
    }
    if (runTaskFilter != null) {
      result = result.filter((r) => r.taskId === runTaskFilter);
    }
    if (runTriggerFilter) {
      result = result.filter((r) => r.trigger === runTriggerFilter);
    }
    return result;
  }, [allRuns, runSearch, runStatusChips, runTaskFilter, runTriggerFilter]);

  // 任务统计
  const taskStats = useMemo(() => {
    const total = tasks.length;
    const totalRunsSum = tasks.reduce((a, t) => a + (t.totalRuns ?? 0), 0);
    const successRunsSum = tasks.reduce((a, t) => a + (t.successRuns ?? 0), 0);
    const successRate = totalRunsSum > 0 ? Math.round((successRunsSum / totalRunsSum) * 100) : 0;
    return {
      total,
      running: tasks.filter((t) => t.status === 'running').length,
      scheduled: tasks.filter((t) => t.enabled).length,
      successRate,
    };
  }, [tasks]);

  // 运行记录 chips 计数
  const runStatusCounts = useMemo(() => {
    const map: Record<string, number> = { running: 0, success: 0, failed: 0, canceled: 0 };
    allRuns.forEach((r) => { if (map[r.status] !== undefined) map[r.status]++; });
    return map;
  }, [allRuns]);

  const taskIdMap = useMemo(() => {
    const map: Record<number, string> = {};
    tasks.forEach((t) => { map[t.id] = t.name; });
    return map;
  }, [tasks]);

  // ===== 任务 operations =====

  const busying = (id: number) => operating.has(id);
  const busyAdd = (id: number) => setOperating((s) => new Set(s).add(id));
  const busyDel = (id: number) => setOperating((s) => { const n = new Set(s); n.delete(id); return n; });

  const openNewDrawer = () => {
    setEditingTask(null);
    taskForm.setFieldsValue(initTaskForm);
    setDrawerOpen(true);
  };

  const openEditDrawer = (t: SchedulerTask) => {
    setEditingTask(t);
    taskForm.setFieldsValue({
      name: t.name,
      description: t.description ?? '',
      command: t.command,
      logDir: t.logDir,
      scheduleType: t.scheduleType,
      scheduleExpr: t.scheduleExpr ?? '',
      enabled: t.enabled,
    });
    setDrawerOpen(true);
  };

  const submitTask = async () => {
    const v = await taskForm.validateFields();
    try {
      if (editingTask) {
        const updated = await srv.updateTask(editingTask.id, v as unknown as Record<string, unknown>);
        setTasks((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
        message.success('已保存');
      } else {
        const created = await srv.createTask(v);
        setTasks((prev) => [created, ...prev]);
        message.success('任务已创建');
      }
      setDrawerOpen(false);
    } catch (e: any) {
      const msg = e?.response?.data?.message ?? e?.message ?? '保存失败';
      message.error(msg);
    }
  };

  const deleteTask = async (t: SchedulerTask) => {
    busyAdd(t.id);
    try {
      await srv.deleteTask(t.id);
      setTasks((prev) => prev.filter((x) => x.id !== t.id));
      message.success('任务已删除');
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '删除失败');
    } finally { busyDel(t.id); }
  };

  const toggleTask = async (t: SchedulerTask) => {
    busyAdd(t.id);
    try {
      const updated = await srv.toggleTask(t.id);
      setTasks((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      message.success(updated.enabled ? '已启用' : '已停用');
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '操作失败');
    } finally { busyDel(t.id); }
  };

  const triggerTask = async (t: SchedulerTask) => {
    busyAdd(t.id);
    try {
      await srv.triggerTask(t.id);
      message.success(`任务「${t.name}」已触发执行`);
      // 刷新列表（状态会变 running）
      setTimeout(() => { void reloadTasks(); void reloadRuns(); }, 1000);
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '触发失败');
    } finally { busyDel(t.id); }
  };

  // ===== 运行记录 operations =====

  const cancelRun = async (r: TaskRunRecord) => {
    busyAdd(r.id);
    try {
      const updated = await srv.cancelRun(r.id);
      setRuns((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      message.success('运行已取消');
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '取消失败');
    } finally { busyDel(r.id); }
  };

  // ===== 日志 =====

  const openRunLogs = (r: TaskRunRecord) => {
    setLogsModal({ taskName: taskIdMap[r.taskId] ?? `#${r.taskId}`, runId: r.id, logFile: r.logFile, lines: [], status: r.status });
    logsSinceRef.current = 0;
    void fetchLogs(r.id, 0, 200);
  };

  const fetchLogs = async (runId: number, sinceLine: number, tail: number) => {
    try {
      const result = await srv.fetchRunLogs(runId, sinceLine, tail);
      setLogsModal((prev) => {
        if (!prev) return prev;
        const merged = sinceLine > 0
          ? [...(prev.lines ?? []), ...result.lines]
          : result.lines;
        return { ...prev, lines: merged, status: result.runStatus };
      });
      logsSinceRef.current = sinceLine + result.lines.length;
      // 如果任务仍在运行，继续轮询
      if (result.runStatus === 'running') {
        if (logsTimerRef.current) clearInterval(logsTimerRef.current);
        logsTimerRef.current = setInterval(() => {
          void fetchLogs(runId, logsSinceRef.current, 0);
        }, 3000);
      } else {
        if (logsTimerRef.current) { clearInterval(logsTimerRef.current); logsTimerRef.current = null; }
        // 非 running 状态，最后再拉一次确保完整
        setTimeout(() => {
          void fetchLogs(runId, logsSinceRef.current, 0);
        }, 1500);
      }
    } catch {
      // 静默
    }
  };

  const closeLogsModal = () => {
    if (logsTimerRef.current) { clearInterval(logsTimerRef.current); logsTimerRef.current = null; }
    setLogsModal(null);
  };

  // 切换视图时清理日志定时器
  useEffect(() => {
    return () => { if (logsTimerRef.current) clearInterval(logsTimerRef.current); };
  }, []);

  // ===== 跳转到对应任务的运行记录 =====
  const jumpToRuns = (taskId: number) => {
    setView('runs');
    setRunTaskFilter(taskId);
  };

  // ===== 刷新所有 =====
  const refreshAll = () => {
    void reloadTasks();
    void reloadRuns();
  };

  // ===== 表格列 =====

  const taskColumns: ColumnsType<SchedulerTask> = [
    {
      title: 'ID', dataIndex: 'id', key: 'id', width: 60,
      render: (v: number) => <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, color: 'var(--ink-40)' }}>#{v}</span>,
    },
    {
      title: '名称', dataIndex: 'name', key: 'name',
      render: (v: string, r) => (
        <a style={{ fontWeight: 500, cursor: 'pointer' }} onClick={() => openEditDrawer(r)}>{v}</a>
      ),
    },
    {
      title: '命令', dataIndex: 'command', key: 'command',
      render: (v: string) => <span className="code-chip">{v}</span>,
    },
    {
      title: '调度', dataIndex: 'scheduleType', key: 'scheduleType', width: 110,
      render: (t: string, r) => (
        <Space size={4}>
          <Tag style={{ fontSize: 10 }}>{SCHEDULE_TYPE_LABEL[t] ?? t}</Tag>
          {r.scheduleExpr && (
            <Tooltip title={r.scheduleExpr}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--ink-40)' }}>
                {r.scheduleType === 'once' && r.scheduleExpr ? r.scheduleExpr.slice(0, 10) : r.scheduleExpr}
              </span>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: <span style={{ fontSize: 12 }}>启用</span>, dataIndex: 'enabled', key: 'enabled', width: 56, align: 'center',
      render: (_: boolean, r) => (
        <Switch size="small" checked={r.enabled} loading={busying(r.id)} onChange={() => toggleTask(r)} />
      ),
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => {
        const m = TASK_STATUS_STYLE[s] ?? TASK_STATUS_STYLE.idle;
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: m.color }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: m.dot,
              boxShadow: s === 'running' ? `0 0 0 3px ${m.dot}22` : 'none' }} />
            {m.label}
          </span>
        );
      },
    },
    {
      title: '统计', key: 'stats', width: 100,
      render: (_, r) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, color: 'var(--ink-40)' }}>
          {r.successRuns}/{r.totalRuns ?? 0}
          {r.failedRuns > 0 && <span style={{ color: '#a5361e' }}> (−{r.failedRuns})</span>}
        </span>
      ),
    },
    {
      title: '下次运行', dataIndex: 'nextRunAt', key: 'nextRunAt', width: 130,
      render: (v: Date | undefined) => v ? fmtDateTime(v) : <span style={{ color: 'var(--ink-40)' }}>-</span>,
    },
    {
      title: '操作', key: 'actions', width: 150,
      render: (_, r) => (
        <Space size={2}>
          <Tooltip title="立即执行">
            <Button size="small" type="text" loading={busying(r.id)}
                    icon={<ThunderboltOutlined />} onClick={() => triggerTask(r)} />
          </Tooltip>
          <Tooltip title="运行记录">
            <Button size="small" type="text" icon={<FileTextOutlined />} onClick={() => jumpToRuns(r.id)} />
          </Tooltip>
          <Popconfirm title={`删除任务「${r.name}」？已运行的记录会保留`} onConfirm={() => deleteTask(r)}>
            <Button size="small" type="text" danger loading={busying(r.id)} icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const runColumns: ColumnsType<TaskRunRecord> = [
    {
      title: 'Run #', dataIndex: 'id', key: 'id', width: 70,
      render: (v: number) => (
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, color: 'var(--ink-40)' }}>#{v}</span>
      ),
    },
    {
      title: '任务', dataIndex: 'taskId', key: 'taskId', width: 120,
      render: (tid: number) => (
        <span style={{ fontSize: 12.5 }}>{taskIdMap[tid] ?? `#${tid}`}</span>
      ),
    },
    {
      title: '触发', dataIndex: 'trigger', key: 'trigger', width: 80,
      render: (v: string) => v === 'schedule' ? <Tag style={{ fontSize: 10 }}>调度</Tag> : <Tag style={{ fontSize: 10 }}>手动</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => {
        const clr = RUN_STATUS_STYLE[s] ?? '#8f8b84';
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: clr }}>
            {s === 'running' && <span className="pulse-dot" style={{ color: '#22c55e', width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />}
            {s === 'running' ? '运行中' : s === 'success' ? '成功' : s === 'failed' ? '失败' : '已取消'}
          </span>
        );
      },
    },
    {
      title: '开始', dataIndex: 'startedAt', key: 'startedAt', width: 130,
      render: (v: Date) => <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>{fmtDateTime(v)}</span>,
    },
    {
      title: '结束', dataIndex: 'finishedAt', key: 'finishedAt', width: 130,
      render: (v: Date | undefined) => v ? <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>{fmtDateTime(v)}</span> : <span style={{ color: 'var(--ink-40)' }}>-</span>,
    },
    {
      title: '耗时', key: 'duration', width: 90,
      render: (_, r) => (r.durationMs != null ? fmtDuration(r.durationMs) : '-'),
    },
    {
      title: '退出码', dataIndex: 'exitCode', key: 'exitCode', width: 72,
      render: (v: number | undefined) => (v != null ? v : '-'),
    },
    {
      title: '日志', dataIndex: 'logFile', key: 'logFile', ellipsis: true,
      render: (f: string, r) => (
        <Tooltip title={f}>
          <Button size="small" type="link" icon={<FileTextOutlined />}
                  onClick={() => openRunLogs(r)}>
            {f.split('/').pop()}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: '', key: 'stop', width: 48,
      render: (_, r) =>
        r.status === 'running' ? (
          <Tooltip title="停止运行">
            <Button size="small" type="text" danger loading={busying(r.id)}
                    icon={<StopOutlined />} onClick={() => cancelRun(r)} />
          </Tooltip>
        ) : null,
    },
  ];

  // ===== 渲染 =====

  return (
    <div>
      {/* 视图切换 + 统计条 */}
      <div className="sched-head">
        <div className="sched-switch">
          <button className={view === 'tasks' ? 'on' : ''} onClick={() => setView('tasks')}>
            任务管理<span className="n">{tasks.length}</span>
          </button>
          <button className={view === 'runs' ? 'on' : ''} onClick={() => setView('runs')}>
            运行记录<span className="n">{allRuns.length}</span>
          </button>
        </div>
        <Button size="small" icon={<ReloadOutlined />} onClick={refreshAll} loading={tasksLoading || runsLoading}>
          刷新
        </Button>
        {view === 'tasks' && (
          <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openNewDrawer}>
            新建任务
          </Button>
        )}
      </div>

      {/* === 任务视图 === */}
      {view === 'tasks' && (
        <>
          <div className="sched-stats">
            <div className="sched-stat">
              <span className="sched-stat-num">{taskStats.total}</span>
              <span className="sched-stat-label">任务总数</span>
            </div>
            <div className="sched-stat">
              <span className="sched-stat-num">{taskStats.scheduled}</span>
              <span className="sched-stat-label">调度中</span>
            </div>
            <div className="sched-stat">
              <span className="sched-stat-num">{taskStats.running}</span>
              <span className="sched-stat-label">运行中</span>
            </div>
            <div className="sched-stat">
              <span className="sched-stat-num">{taskStats.successRate}%</span>
              <span className="sched-stat-label">成功率</span>
            </div>
          </div>

          <div className="sched-toolbar">
            <Input
              size="small" placeholder="搜索名称 / 命令 / #ID …" style={{ width: 260 }}
              prefix={<SearchOutlined style={{ color: 'var(--ink-40)' }} />}
              value={taskSearch} onChange={(e) => setTaskSearch(e.target.value)}
              allowClear
            />
            <Select
              size="small" mode="multiple" placeholder="调度类型" style={{ minWidth: 210 }}
              value={taskTypeFilter} onChange={setTaskTypeFilter}
              options={['manual', 'once', 'interval', 'cron'].map((v) => ({
                value: v, label: SCHEDULE_TYPE_LABEL[v],
              }))}
              allowClear
            />
            {(taskSearch || taskTypeFilter.length > 0) && (
              <span className="sched-result-count">
                {filteredTasks.length} 条结果 ·{' '}
                <a onClick={() => { setTaskSearch(''); setTaskTypeFilter([]); }}>清除筛选</a>
              </span>
            )}
          </div>

          <Table<SchedulerTask>
            rowKey="id"
            size="middle"
            loading={tasksLoading}
            columns={taskColumns}
            dataSource={filteredTasks}
            pagination={false}
            locale={{ emptyText: (
              <div className="sched-empty">
                <div className="sched-empty-title">暂无调度任务</div>
                <div className="sched-empty-hint">点「新建任务」创建第一个定时或手动执行任务</div>
              </div>
            ) }}
          />
        </>
      )}

      {/* === 运行记录视图 === */}
      {view === 'runs' && (
        <>
          <div className="sched-toolbar">
            <Input
              size="small" placeholder="搜索 #RunID / 日志文件 / …" style={{ width: 260 }}
              prefix={<SearchOutlined style={{ color: 'var(--ink-40)' }} />}
              value={runSearch} onChange={(e) => setRunSearch(e.target.value)}
              allowClear
            />
            <Select
              size="small" placeholder="任务" style={{ minWidth: 150 }} allowClear
              value={runTaskFilter} onChange={(v) => setRunTaskFilter(v ?? null)}
              options={tasks.map((t) => ({ value: t.id, label: t.name }))}
            />
            <Select
              size="small" placeholder="触发方式" style={{ minWidth: 100 }} allowClear
              value={runTriggerFilter} onChange={(v) => setRunTriggerFilter(v ?? null)}
              options={[
                { value: 'manual', label: '手动' },
                { value: 'schedule', label: '调度' },
              ]}
            />
          </div>

          <div className="sched-chips">
            {['running', 'success', 'failed', 'canceled'].map((st) => {
              const on = runStatusChips.has(st);
              const cnt = runStatusCounts[st] ?? 0;
              const dotMap: Record<string, string> = { running: '#22c55e', success: '#476a4b', failed: '#a5361e', canceled: '#8f8b84' };
              const labelMap: Record<string, string> = { running: '运行中', success: '成功', failed: '失败', canceled: '已取消' };
              return (
                <span
                  key={st}
                  className={`filter-chip${on ? ' filter-chip--on' : ''}`}
                  onClick={() => {
                    setRunStatusChips((prev) => {
                      const next = new Set(prev);
                      if (next.has(st)) next.delete(st); else next.add(st);
                      return next;
                    });
                  }}
                >
                  <span className="dot" style={{ background: dotMap[st] ?? '#8f8b84' }} />
                  {labelMap[st]}
                  <span className="cnt">{on ? cnt : cnt}</span>
                </span>
              );
            })}
            {(runSearch || runStatusChips.size > 0 || runTaskFilter != null || runTriggerFilter) && (
              <span className="sched-chips-total">
                {filteredRuns.length} 条 ·{' '}
                <a onClick={() => { setRunSearch(''); setRunStatusChips(new Set()); setRunTaskFilter(null); setRunTriggerFilter(null); }}>
                  清除筛选
                </a>
              </span>
            )}
          </div>

          <Table<TaskRunRecord>
            rowKey="id"
            size="middle"
            loading={runsLoading}
            columns={runColumns}
            dataSource={filteredRuns}
            rowClassName={(r) => {
              if (r.status === 'running') return 'run-row--running';
              if (r.status === 'failed') return 'run-row--failed';
              return '';
            }}
            pagination={false}
            locale={{ emptyText: (
              <div className="sched-empty">
                <div className="sched-empty-title">暂无运行记录</div>
                <div className="sched-empty-hint">
                  {runSearch || runStatusChips.size > 0 || runTaskFilter != null || runTriggerFilter
                    ? '当前筛选条件下无匹配记录'
                    : '在任务管理中手动执行或等待调度器自动触发'}
                </div>
                {runSearch || runStatusChips.size > 0 || runTaskFilter != null || runTriggerFilter ? (
                  <a style={{ marginTop: 8, display: 'inline-block', fontSize: 12 }}
                     onClick={() => { setRunSearch(''); setRunStatusChips(new Set()); setRunTaskFilter(null); setRunTriggerFilter(null); }}>
                    清除筛选
                  </a>
                ) : null}
              </div>
            ) }}
          />
        </>
      )}

      {/* ===== 任务编辑抽屉 ===== */}
      <Drawer
        title={editingTask ? `编辑任务 · ${editingTask.name}` : '新建调度任务'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={540}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => void submitTask()}>保存</Button>
          </Space>
        }
        destroyOnHidden
      >
        <Form form={taskForm} layout="vertical" initialValues={initTaskForm}>
          <Form.Item name="name" label="任务名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="数据导出任务" />
          </Form.Item>
          <Form.Item name="description" label="描述（可选）">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="command" label="执行命令（Shell）" rules={[{ required: true, message: '请输入命令' }]}>
            <Input.TextArea
              rows={3}
              style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              placeholder="docker run --rm my-image python script.py"
            />
          </Form.Item>
          <Form.Item name="logDir" label="日志目录（后端侧路径）">
            <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} />
          </Form.Item>
          <Form.Item name="scheduleType" label="调度方式" style={{ marginBottom: 8 }}>
            <Radio.Group>
              <Space direction="vertical" size={4}>
                <Radio value="manual">手动 — 仅在页面点击「立即执行」时运行</Radio>
                <Radio value="interval">间隔 — 每隔 N 秒重复执行</Radio>
                <Radio value="cron">Cron — 按 cron 表达式执行</Radio>
                <Radio value="once">一次性 — 指定时间执行一次</Radio>
              </Space>
            </Radio.Group>
          </Form.Item>
          <Form.Item name="scheduleExpr" label="调度表达式">
            <Input
              style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              placeholder={
                taskForm.getFieldValue('scheduleType') === 'interval' ? '60'
                : taskForm.getFieldValue('scheduleType') === 'cron' ? '0 */6 * * *'
                : '手动/一次性任务可留空'
              }
            />
          </Form.Item>
          <Form.Item name="enabled" label="启用调度" valuePropName="checked">
            <Switch />
          </Form.Item>

          {/* 日志路径预览 */}
          <div style={{
            marginTop: 8, padding: '8px 12px', background: 'var(--paper-02)',
            border: '1px solid var(--border-hairline)', borderRadius: 8,
            fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-60)',
            wordBreak: 'break-all',
          }}>
            <div>日志落盘规则：</div>
            <div>{taskForm.getFieldValue('logDir') ?? '/var/log/ontomind/tasks'}/{'{taskId}'}/{'{yyyyMMdd}'}/{'{taskId}-{HHmmss}-{seed}.log'}</div>
            <div style={{ marginTop: 4, color: 'var(--ink-40)' }}>
              实际执行：{taskForm.getFieldValue('command') || '<命令>'} {'>>'} {'<日志路径>'} 2&gt;&amp;1
            </div>
          </div>
        </Form>
      </Drawer>

      {/* ===== 日志 Modal ===== */}
      <Modal
        title={`运行日志 · ${logsModal?.taskName ?? ''} (Run #${logsModal?.runId})`}
        open={!!logsModal}
        onCancel={closeLogsModal}
        footer={null}
        width={860}
      >
        <div style={{ marginBottom: 8, fontSize: 12, color: 'var(--ink-40)', fontFamily: 'var(--font-mono)' }}>
          {logsModal?.logFile}
          {logsModal?.status === 'running' && (
            <Tag color="processing" style={{ marginLeft: 8, fontSize: 10 }}>运行中 · 实时刷新</Tag>
          )}
          {logsModal?.status !== 'running' && logsModal?.status && (
            <Tag style={{ marginLeft: 8, fontSize: 10 }}>
              {logsModal.status === 'success' ? '已完成' : logsModal.status === 'failed' ? '失败' : '已取消'}
            </Tag>
          )}
        </div>
        <LogViewer lines={logsModal?.lines ?? []} />
      </Modal>
    </div>
  );
}
