/** 算力调度 — 原型类型定义（纯前端原型，后端未接入）. */

export type ConnType = 'local' | 'ssh' | 'docker-api';

/** 算力节点（挂载的服务器） */
export interface ComputeNode {
  id: number;
  name: string;
  address: string;
  connType: ConnType;
  online: boolean;
  cpu: string;
  mem: string;
  disk: string;
  remark?: string;
}

export type ContainerStatus = 'running' | 'exited' | 'created' | 'restarting' | 'paused' | 'unknown';

/** Docker 容器实例 */
export interface ContainerInstance {
  id: string;
  name: string;
  nodeId: number;
  /** 关联专家（opencode 容器场景） */
  expertSlug?: string;
  image: string;
  status: ContainerStatus;
  ports: string;
  createdAt: Date;
}

export type ScheduleType = 'manual' | 'once' | 'interval' | 'cron';

/** 调度任务定义（task 表） */
export interface SchedulerTask {
  id: number;
  name: string;
  description?: string;
  /** 执行命令，如 docker run … */
  command: string;
  /** 日志根目录，stdout/stderr 重定向落盘 */
  logDir: string;
  scheduleType: ScheduleType;
  /** cron 表达式 / interval 秒数 / once ISO 时间 */
  scheduleExpr?: string;
  enabled: boolean;
  /** 实时状态: idle / running / paused / disabled */
  status: string;
  createdAt: Date;
  lastRunAt?: Date;
  nextRunAt?: Date;
  totalRuns: number;
  successRuns: number;
  failedRuns: number;
}

export type RunStatus = 'running' | 'success' | 'failed' | 'canceled';

/** 任务运行记录（run 表，一个任务多条） */
export interface TaskRunRecord {
  id: number;
  taskId: number;
  trigger: 'manual' | 'schedule';
  status: RunStatus;
  startedAt: Date;
  finishedAt?: Date;
  durationMs?: number;
  exitCode?: number;
  errorMessage?: string;
  /** 日志文件完整路径 */
  logFile: string;
}

export type LogLevel = 'info' | 'warn' | 'error' | 'event';

export interface LogLine {
  seq: number;
  level: LogLevel;
  text: string;
}

/** Docker Hub 搜索结果项 */
export interface HubImage {
  name: string;
  description: string;
  stars: number;
  pulls: number;
  official: boolean;
}

/** 本地镜像条目 */
export interface ImageListItem {
  id: string;
  repository: string;
  tag: string;
  size: string;
  created_at: string;
}

/** OpenCode 安装状态 */
export interface OpenCodeStatus {
  installed: boolean;
  path: string;
  version: string;
  running_instances: OpenCodeWebInstance[];
}

/** 运行中的 OpenCode Web 实例 */
export interface OpenCodeWebInstance {
  pid: number;
  port: number;
  cors: string;
  url: string;
  started_at: number;
  cmdline: string;
}

/** OpenCode CLI 运行记录 */
export interface OpenCodeCliRun {
  id: number;
  prompt: string;
  model?: string;
  status: 'running' | 'done' | 'error' | 'cancelled';
  output: string;
  started_at: number;
  finished_at?: number;
}
