/** 算力管理相关类型定义 */

export interface ComputeNode {
  id: number;
  name: string;
  description?: string;
  host: string;
  port: number;
  username: string;
  authType: string;
  isLocal: boolean;
  status: string;
  lastCheckedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ComputeNodeCreate {
  name: string;
  description?: string;
  host: string;
  port?: number;
  username: string;
  authType: string;
  password?: string;
  privateKey?: string;
}

export interface ComputeNodeUpdate {
  name?: string;
  description?: string;
  host?: string;
  port?: number;
  username?: string;
  authType?: string;
  password?: string;
  privateKey?: string;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  nodeId: number;
}

export interface ImageInfo {
  id: string;
  tags: string[];
  size: string;
  created: string;
}

// ---- 结构化容器配置 ----

/** 端口映射：宿主端口 → 容器端口 */
export interface PortMapping {
  host_port: number;
  container_port: number;
  protocol: 'tcp' | 'udp';
}

/** 卷挂载：宿主路径（或命名卷）→ 容器路径 */
export interface VolumeMapping {
  host_path: string;
  container_path: string;
  read_only: boolean;
}

/** 环境变量键值对 */
export interface EnvVar {
  key: string;
  value: string;
}

export type RestartPolicy = 'no' | 'always' | 'on-failure' | 'unless-stopped';

export interface ContainerInfo {
  id: string;
  name: string;
  image: string;
  status: string;
  /** 展示用摘要，如 "4096->14096" */
  ports: string;
  created: string;
  /** 结构化配置（表单回填用） */
  port_mappings: PortMapping[];
  volume_mappings: VolumeMapping[];
  env_vars: EnvVar[];
  command: string;
  restart: RestartPolicy;
  network: string;
  state_detail: string;
  exit_code: number | null;
  shells: string[];
}

export interface ContainerCreateData {
  image: string;
  name?: string;
  command?: string;
  entrypoint?: string[];
  ports: PortMapping[];
  envs: EnvVar[];
  volumes: VolumeMapping[];
  restart: RestartPolicy;
  network?: string;
  auto_pull?: boolean;
  start?: boolean;
}

export interface ContainerLogs {
  logs: string;
}

export interface ContainerInspectData {
  data: Record<string, unknown>;
}

/** 容器状态对应的颜色 */
export const containerStatusColor: Record<string, string> = {
  running: '#52c41a',
  exited: '#8c8c8c',
  paused: '#faad14',
  restarting: '#1890ff',
  dead: '#ff4d4f',
  created: '#8c8c8c',
  removing: '#ff4d4f',
  removed: '#8c8c8c',
};

/** 容器状态中文文案 */
export const containerStatusLabel: Record<string, string> = {
  running: '运行中',
  exited: '已退出',
  paused: '已暂停',
  restarting: '重启中',
  dead: '异常',
  created: '已创建',
  removing: '删除中',
  removed: '已删除',
};

// ---- 容器修改 ----

export interface ContainerUpdateRequest {
  image?: string;
  name?: string;
  command?: string;
  /** null/undefined = 沿用原值；[] = 清空 */
  ports?: PortMapping[];
  envs?: EnvVar[];
  volumes?: VolumeMapping[];
  restart?: RestartPolicy;
  network?: string;
}

// ---- 容器预设（新建时的「案例」） ----

export interface ContainerPreset {
  id: string;
  name: string;
  description: string;
  image: string;
  command?: string | null;
  ports: PortMapping[];
  envs: EnvVar[];
  volumes: VolumeMapping[];
  restart: RestartPolicy;
  network?: string | null;
}

// ---- 镜像拉取 ----

export interface ImagePullResponse {
  image: string;
  success: boolean;
  message: string;
}

// ---- shell 探测 ----

export interface ShellDetectResult {
  shells: string[];
  default: string | null;
}

// ---- 快速命令 ----

export interface CommandTemplateParam {
  type: string;
  default: unknown;
  label: string;
  example?: string;
}

export interface CommandTemplate {
  id: string;
  name: string;
  description: string;
  command: string;
  /** 'sync' 立即返回结果 / 'async' 后台跑 + 轮询日志 */
  mode?: 'sync' | 'async';
  params: Record<string, CommandTemplateParam>;
}

export interface ContainerExecRequest {
  command: string;
  params?: Record<string, unknown>;
  template_id?: string;
  mode?: 'sync' | 'async';
  workdir?: string;
  timeout?: number;
}

export interface ContainerExecResponse {
  exec_id: string;
  container_id: string;
  command: string;
  started: boolean;
  mode: 'sync' | 'async';
  logs: string;
  exit_code: number | null;
  running: boolean;
}

export interface ContainerExecLogsResponse {
  exec_id: string;
  logs: string;
  running: boolean;
  exit_code: number | null;
}

// ---- AIDE 容器源 ----

export interface AideContainerSource {
  node_id: number;
  node_name: string;
  container_id: string;
  container_name: string;
  port: number;
  container_port: number;
  image: string;
}

// ---- 容器服务登记（container_services 表） ----

export type ServiceKind = 'opencode_web' | 'opencode_serve' | 'dsh_web' | 'other';
export type ServiceStatus = 'running' | 'stopped' | 'unreachable' | 'unknown';

/**
 * 容器内常驻服务。
 *
 * ⚠️ `status` / `host_reachable` 是**后端最近一次探测的快照**，不是实时值。
 * UI 必须同时展示 `last_checked_at`，并提供「刷新」入口。
 */
export interface ContainerServiceInfo {
  id: number;
  node_id: number;
  node_name: string;
  container_id: string;
  container_name: string;
  image?: string | null;

  kind: ServiceKind;
  name: string;
  container_port: number;
  host_port?: number | null;
  access_url?: string | null;
  command?: string | null;
  log_path?: string | null;
  exec_id?: string | null;

  status: ServiceStatus;
  status_detail?: string | null;
  /** 容器内实际监听地址；127.0.0.1 表示宿主访问不到 */
  bind_address?: string | null;
  host_reachable: boolean;
  last_checked_at?: string | null;
  is_aide_source: boolean;

  created_at?: string | null;
  updated_at?: string | null;
}

export interface ServiceRefreshResult {
  total: number;
  running: number;
  stopped: number;
  unreachable: number;
  services: ContainerServiceInfo[];
}

export interface ServiceLaunchRequest {
  kind: 'opencode_web' | 'opencode_serve' | 'dsh_web';
  container_port: number;
  cors?: string;
  hostname?: string;
}

export interface ContainerServiceCreate {
  container_id: string;
  container_port: number;
  kind: ServiceKind;
  name?: string;
  command?: string;
  log_path?: string;
}

export const serviceStatusColor: Record<ServiceStatus, string> = {
  running: '#52c41a',
  stopped: '#faad14',
  unreachable: '#ff4d4f',
  unknown: '#8c8c8c',
};

export const serviceStatusLabel: Record<ServiceStatus, string> = {
  running: '运行中',
  stopped: '已停止',
  unreachable: '不可达',
  unknown: '未探测',
};

export const serviceKindLabel: Record<ServiceKind, string> = {
  opencode_web: 'opencode web',
  opencode_serve: 'opencode serve',
  dsh_web: 'DeepSeek Harness web',
  other: '其它服务',
};
