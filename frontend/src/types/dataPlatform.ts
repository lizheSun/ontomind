export type DpDialect = 'mysql' | 'postgresql' | 'sqlite' | 'mysql_readonly';
export type DpStatus = 'active' | 'inactive' | 'error';
export type DpHistoryStatus = 'running' | 'success' | 'error' | 'canceled' | 'timeout';
export type ChatRole = 'user' | 'assistant' | 'system';

export interface DpDataSource {
  id: number;
  name: string;
  sourceType: string;
  dialect: DpDialect;
  host: string | null;
  port: number | null;
  username: string | null;
  database: string;
  defaultSchema: string | null;
  charset: string;
  description: string | null;
  status: DpStatus;
  readOnlyFlag: boolean;
  hasPassword: boolean;
  ownerUserId: number;
  createdByUserId: number;
  extraParams: Record<string, unknown> | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface DpDataSourceCreate {
  name: string;
  source_type: string;
  dialect: DpDialect;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  password?: string;
  database: string;
  default_schema?: string | null;
  charset?: string;
  description?: string | null;
  read_only_flag?: boolean;
  extra_params?: Record<string, unknown> | null;
}

export interface DpDataSourceUpdate {
  name?: string;
  source_type?: string;
  dialect?: DpDialect;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  password?: string;
  database?: string;
  default_schema?: string | null;
  charset?: string;
  description?: string | null;
  status?: DpStatus;
  read_only_flag?: boolean;
  extra_params?: Record<string, unknown> | null;
}

export interface DpTestResult {
  ok: boolean;
  elapsedMs: number;
  serverVersion: string | null;
  error: string | null;
}

export interface DpSchemaColumn {
  name: string;
  type?: string;
}

export interface DpSchemaTable {
  name: string;
  columns: DpSchemaColumn[];
}

export interface DpSchemaDatabase {
  name: string;
  tables: DpSchemaTable[];
}

export interface DpSchemaResponse {
  databases: DpSchemaDatabase[];
}

export interface DpColumnMeta {
  name: string;
  dbType: string | null;
  genericType: string | null;
}

export interface DpExecuteResponse {
  columns: DpColumnMeta[];
  rows: unknown[][];
  rowCount: number;
  elapsedMs: number;
  truncated: boolean;
}

export interface DpSavedQuery {
  id: number;
  name: string;
  sourceId: number;
  sqlText: string;
  isFavorite: boolean;
  ownerUserId: number;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface DpQueryHistory {
  id: number;
  sourceId: number;
  userId: number;
  sqlText: string;
  status: DpHistoryStatus;
  rowCount: number | null;
  elapsedMs: number | null;
  errorMessage: string | null;
  columnsJson: unknown;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string | null;
}

export interface DpChatSession {
  id: number;
  name: string;
  sourceId: number;
  userId: number;
  modelConfigId: number | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface DpChatMessage {
  id: number;
  sessionId: number;
  role: ChatRole;
  content: string;
  generatedSql: string | null;
  executed: boolean;
  createdAt: string | null;
}
