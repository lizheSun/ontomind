/** 算力调度原型 — mock 数据与小工具（无后端依赖）. */
import type {
  ComputeNode, ContainerInstance, HubImage, LogLevel, LogLine, SchedulerTask, TaskRunRecord,
} from './types';

/* ---------------- 格式化 ---------------- */
const pad2 = (n: number) => String(n).padStart(2, '0');

export const fmtDate = (d: Date) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
export const fmtDateTime = (d: Date) => `${fmtDate(d)} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
export const fmtDateCompact = (d: Date) => `${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}`;
export const fmtTimeCompact = (d: Date) => `${pad2(d.getHours())}${pad2(d.getMinutes())}${pad2(d.getSeconds())}`;
export const hhmmss = (d: Date) => `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;

export const randSeed = (len = 6) => Math.random().toString(36).slice(2, 2 + len);

let nodeSeq = 100;
let taskSeq = 100;
let runSeq = 1000;
export const nextNodeId = () => ++nodeSeq;
export const nextTaskId = () => ++taskSeq;
export const nextRunId = () => ++runSeq;

/** 日志落盘规则：{logDir}/{taskId}/{yyyyMMdd}/{taskId}-{HHmmss}-{seed}.log */
export const buildLogFile = (logDir: string, taskId: number, at: Date, seed = randSeed()) =>
  `${logDir.replace(/\/+$/, '')}/${taskId}/${fmtDateCompact(at)}/${taskId}-${fmtTimeCompact(at)}-${seed}.log`;

export const fmtCount = (n: number) =>
  n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n / 1_000).toFixed(1)}K` : String(n);

export function fmtDuration(ms: number): string {
  if (ms < 1_000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1_000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1_000);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

const daysAgo = (n: number, hour = 9, minute = 0) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  d.setHours(hour, minute, Math.floor(Math.random() * 50), 0);
  return d;
};
const hoursFromNow = (n: number) => new Date(Date.now() + n * 3_600_000);
const nextDaily = (hour: number) => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(hour, 0, 0, 0);
  return d;
};

/* ---------------- 日志模板 ---------------- */
const CONTAINER_LOG_POOL: Array<[LogLevel, string]> = [
  ['info', '[INFO] opencode serve listening on 0.0.0.0:4096'],
  ['info', '[INFO] loaded 4 agents from /root/.config/opencode/agent'],
  ['event', '[EVENT] session ses_3f9a2c opened (agent=data-analyst)'],
  ['info', '[INFO] GET /session 200 2ms'],
  ['info', '[INFO] POST /session/ses_3f9a2c/message 200 812ms'],
  ['warn', '[WARN] model latency high: p99=2.4s'],
  ['info', '[INFO] GET /event 200 (sse stream attached)'],
  ['info', '[INFO] tool bash executed in 340ms'],
  ['event', '[EVENT] session ses_3f9a2c idle'],
  ['info', '[INFO] config reloaded (provider=agent-plan)'],
  ['info', '[INFO] POST /session 201 5ms'],
  ['warn', '[WARN] disk usage 78% on /var/lib/docker'],
];

export const containerLogs = (seedText: string, n = 14): LogLine[] => {
  const seed = [...seedText].reduce((a, ch) => a + ch.charCodeAt(0), 0);
  const t0 = Date.now() - n * 4_000;
  return Array.from({ length: n }, (_, i) => {
    const [level, msg] = CONTAINER_LOG_POOL[(seed + i) % CONTAINER_LOG_POOL.length];
    return { seq: i + 1, level, text: `${hhmmss(new Date(t0 + i * 4_000))} ${msg}` };
  });
};

const RUN_LOG_HEAD = [
  '调度器派发任务，开始执行',
  'docker run --rm -v /data:/data sst/opencode:latest run "同步今日数仓"',
  'opencode v1.18.4 · agent=data-analyst',
  '读取配置 /root/.config/opencode/opencode.json',
  '连接数据源 mysql://10.0.0.8:3306/warehouse … OK',
];
const RUN_LOG_TAIL: Array<[LogLevel, string]> = [
  ['info', '同步完成: 1,842 行写入 · 0 冲突'],
  ['info', 'opencode session archived'],
  ['event', '任务成功，exit=0'],
];
const RUN_LOG_FAIL: Array<[LogLevel, string]> = [
  ['error', '拉取镜像 sst/opencode:latest 超时: dial tcp 10.0.0.2:443: i/o timeout'],
  ['error', 'exit status 125'],
  ['event', '任务失败，exit=1'],
];

export const mockRunLogs = (r: TaskRunRecord): LogLine[] => {
  const at = r.finishedAt ?? r.startedAt;
  if (r.status === 'running') {
    return RUN_LOG_HEAD.slice(0, 3).map((m, i) => ({
      seq: i + 1, level: 'info' as LogLevel, text: `${hhmmss(r.startedAt)} [INFO] ${m}`,
    }));
  }
  const lines: LogLine[] = RUN_LOG_HEAD.map((m, i) => ({
    seq: i + 1, level: 'info' as LogLevel, text: `${hhmmss(r.startedAt)} [INFO] ${m}`,
  }));
  if (r.status === 'failed') {
    RUN_LOG_FAIL.forEach(([level, m]) => {
      lines.push({ seq: lines.length + 1, level, text: `${hhmmss(at)} [${level.toUpperCase()}] ${m}` });
    });
  } else if (r.status === 'canceled') {
    lines.push({ seq: lines.length + 1, level: 'warn', text: `${hhmmss(at)} [WARN] 收到 SIGTERM，进程退出 (143)` });
  } else {
    RUN_LOG_TAIL.forEach(([level, m]) => {
      lines.push({ seq: lines.length + 1, level, text: `${hhmmss(at)} [${level.toUpperCase()}] ${m}` });
    });
  }
  return lines;
};

/* ---------------- 算力节点 ---------------- */
export const MOCK_NODES: ComputeNode[] = [
  {
    id: 1, name: '本地开发机', address: '127.0.0.1', connType: 'local', online: true,
    cpu: '8 核', mem: '16 GB', disk: '512 GB', remark: '本机 Docker（unix socket）',
  },
  {
    id: 2, name: '数据节点 01', address: '192.168.1.23', connType: 'ssh', online: true,
    cpu: '16 核', mem: '64 GB', disk: '2 TB', remark: 'SSH 免密 · docker 24.0.7',
  },
  {
    id: 3, name: 'GPU 训练节点', address: '192.168.1.45', connType: 'ssh', online: false,
    cpu: '32 核', mem: '128 GB', disk: '4 TB', remark: '上次心跳 3 天前',
  },
];

/* ---------------- 容器 ---------------- */
export const MOCK_CONTAINERS: ContainerInstance[] = [
  {
    id: 'a91f3c02', name: 'opencode-data-analyst', nodeId: 1, expertSlug: 'data-analyst',
    image: 'sst/opencode:latest', status: 'running', ports: '4096:4096', createdAt: daysAgo(6, 10),
  },
  {
    id: 'b72e4d18', name: 'opencode-frontend', nodeId: 1, expertSlug: 'frontend',
    image: 'sst/opencode:latest', status: 'running', ports: '4097:4096', createdAt: daysAgo(5, 15),
  },
  {
    id: 'c83a5e29', name: 'opencode-backend', nodeId: 2, expertSlug: 'backend',
    image: 'sst/opencode:latest', status: 'exited', ports: '4096:4096', createdAt: daysAgo(12, 9),
  },
  {
    id: 'd94b6f30', name: 'pg-etl', nodeId: 2,
    image: 'postgres:16-alpine', status: 'created', ports: '5433:5432', createdAt: daysAgo(1, 18),
  },
];

/* ---------------- 调度任务 ---------------- */
export const MOCK_TASKS: SchedulerTask[] = [
  {
    id: 12, name: '每日数仓同步', description: '业务库 → 数仓 ODS 层全量同步',
    command: 'docker run --rm -v /data:/data sst/opencode:latest run "同步今日数仓"',
    logDir: '/var/log/ontomind/tasks', status: 'idle',
    scheduleType: 'cron', scheduleExpr: '0 2 * * *', enabled: true,
    createdAt: daysAgo(9, 11), lastRunAt: daysAgo(0, 2), nextRunAt: nextDaily(2),
    totalRuns: 8, successRuns: 7, failedRuns: 1,
  },
  {
    id: 13, name: 'hourly 经营报表', description: '每小时生成一次经营快报并归档',
    command: 'docker exec opencode-data-analyst opencode run "生成经营快报"',
    logDir: '/var/log/ontomind/tasks', status: 'idle',
    scheduleType: 'interval', scheduleExpr: '3600', enabled: true,
    createdAt: daysAgo(4, 16), lastRunAt: daysAgo(0, 8), nextRunAt: hoursFromNow(1),
    totalRuns: 96, successRuns: 96, failedRuns: 0,
  },
  {
    id: 14, name: '清理悬空镜像', description: '清理各节点 dangling 镜像，释放磁盘',
    command: 'docker image prune -f',
    logDir: '/var/log/ontomind/tasks', status: 'disabled',
    scheduleType: 'manual', enabled: false,
    createdAt: daysAgo(2, 14), lastRunAt: daysAgo(1, 20),
    totalRuns: 3, successRuns: 3, failedRuns: 0,
  },
  {
    id: 15, name: '月度数据归档', description: '上月分区数据归档到冷存储',
    command: 'docker run --rm etl/archiver:latest --month prev',
    logDir: '/data/logs/archiver', status: 'disabled',
    scheduleType: 'once', scheduleExpr: '2026-08-01T03:00:00', enabled: false,
    createdAt: daysAgo(0, 10), nextRunAt: undefined,
    totalRuns: 0, successRuns: 0, failedRuns: 0,
  },
];

/* ---------------- 运行记录 ---------------- */
const mkRun = (
  taskId: number, trigger: 'manual' | 'schedule', startedAt: Date, durationMs: number,
  exitCode: number, errorMessage?: string,
): TaskRunRecord => ({
  id: nextRunId(), taskId, trigger,
  status: exitCode === 0 ? 'success' : 'failed',
  startedAt,
  finishedAt: new Date(startedAt.getTime() + durationMs),
  durationMs, exitCode, errorMessage,
  logFile: buildLogFile('/var/log/ontomind/tasks', taskId, startedAt),
});

export const MOCK_RUNS: TaskRunRecord[] = [
  {
    id: nextRunId(), taskId: 12, trigger: 'manual', status: 'running',
    startedAt: new Date(Date.now() - 26_000),
    logFile: buildLogFile('/var/log/ontomind/tasks', 12, new Date(Date.now() - 26_000)),
  },
  mkRun(12, 'schedule', daysAgo(0, 2), 4 * 60_000 + 12_000, 0),
  mkRun(12, 'schedule', daysAgo(1, 2), 58_000, 1, '镜像拉取超时'),
  mkRun(12, 'schedule', daysAgo(2, 2), 3 * 60_000 + 47_000, 0),
  mkRun(12, 'manual', daysAgo(3, 16), 2 * 60_000 + 5_000, 0),
  mkRun(13, 'schedule', daysAgo(0, 8), 41_000, 0),
  mkRun(13, 'schedule', daysAgo(0, 7), 39_000, 0),
  mkRun(14, 'manual', daysAgo(1, 20), 8_000, 0),
];

/* ---------------- Docker Hub（离线回退） ---------------- */
export const MOCK_IMAGE_RESULTS: HubImage[] = [
  { name: 'sst/opencode', description: 'AI coding agent — terminal native, multi-provider', stars: 421, pulls: 1_200_000, official: false },
  { name: 'nginx', description: 'Official build of Nginx.', stars: 20_300, pulls: 2_100_000_000, official: true },
  { name: 'postgres', description: 'The PostgreSQL object-relational database system.', stars: 12_800, pulls: 1_600_000_000, official: true },
  { name: 'redis', description: 'In-memory data structure store, used as database & cache.', stars: 12_100, pulls: 1_400_000_000, official: true },
  { name: 'python', description: 'Official Python runtime.', stars: 9_900, pulls: 1_900_000_000, official: true },
];
