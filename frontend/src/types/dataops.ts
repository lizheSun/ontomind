/** DataOps 数据仓库类型 */
export type DataSourceType = 'doris' | 'mysql' | 'hive';
export type DataSourceStatus = 'unknown' | 'online' | 'offline';

export interface DataSource {
  id: number;
  name: string;
  source_type: DataSourceType;
  host: string;
  port: number;
  username: string;
  database?: string | null;
  charset: string;
  description?: string | null;
  status: DataSourceStatus;
  is_default: boolean;
  has_password: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DataSourceCreate {
  name: string;
  source_type: DataSourceType;
  host: string;
  port: number;
  username: string;
  password?: string;
  database?: string;
  charset?: string;
  description?: string;
}

export interface ConnectionTestResult {
  ok: boolean;
  message: string;
  latency_ms?: number | null;
  server_info?: string | null;
}

export interface TableInfo {
  name: string;
  type: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  key: string;
  default: unknown;
  extra: string;
}

export interface SampleResult {
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
  sql: string;
}

export interface ExecuteSqlLog {
  level: 'info' | 'success' | 'error' | 'warn';
  message: string;
}

export interface ExecuteSqlResult {
  ok: boolean;
  columns: string[];
  rows: unknown[][];
  truncated: boolean;
  affected_rows?: number | null;
  sql: string;
  latency_ms?: number | null;
  logs: ExecuteSqlLog[];
  message?: string | null;
}
