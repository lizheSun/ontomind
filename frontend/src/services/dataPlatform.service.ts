import api from './api';
import type {
  DpDataSource,
  DpDataSourceCreate,
  DpDataSourceUpdate,
  DpDialect,
  DpTestResult,
  DpSchemaResponse,
  DpExecuteResponse,
  DpSavedQuery,
  DpQueryHistory,
  DpChatSession,
  DpChatMessage,
} from '../types/dataPlatform';

export interface ParseConfigParsed {
  name: string;
  source_type: string;
  dialect: DpDialect;
  host: string | null;
  port: number | null;
  username: string | null;
  password: string; // always empty (backend enforces)
  database: string;
  default_schema: string | null;
  charset: string;
  description: string | null;
  read_only_flag: boolean;
  extra_params?: Record<string, unknown> | null;
}

export interface ParseConfigResult {
  parsed: ParseConfigParsed;
  model_used: string;
  warnings: string[];
}

interface Envelope<T> {
  code: string;
  message: string;
  data: T;
  total?: number;
}

function unwrap<T>(res: { data: Envelope<T> }): T {
  if (res.data?.code !== 'SUCCESS') {
    throw new Error(res.data?.message ?? 'API error');
  }
  return res.data.data;
}

// -- snake→camel mappers ----------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapDataSource(raw: any): DpDataSource {
  return {
    id: raw.id,
    name: raw.name,
    sourceType: raw.source_type,
    dialect: raw.dialect,
    host: raw.host,
    port: raw.port,
    username: raw.username,
    database: raw.database,
    defaultSchema: raw.default_schema,
    charset: raw.charset,
    description: raw.description,
    status: raw.status,
    readOnlyFlag: raw.read_only_flag,
    hasPassword: raw.has_password,
    ownerUserId: raw.owner_user_id,
    createdByUserId: raw.created_by_user_id,
    extraParams: raw.extra_params,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapTestResult(raw: any): DpTestResult {
  return {
    ok: raw.ok,
    elapsedMs: raw.elapsed_ms,
    serverVersion: raw.server_version,
    error: raw.error,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapExecuteResponse(raw: any): DpExecuteResponse {
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    columns: (raw.columns ?? []).map((c: any) => ({
      name: c.name,
      dbType: c.db_type ?? null,
      genericType: c.generic_type ?? null,
    })),
    rows: raw.rows ?? [],
    rowCount: raw.row_count,
    elapsedMs: raw.elapsed_ms,
    truncated: raw.truncated ?? false,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapSavedQuery(raw: any): DpSavedQuery {
  return {
    id: raw.id,
    name: raw.name,
    sourceId: raw.source_id,
    sqlText: raw.sql_text,
    isFavorite: raw.is_favorite,
    ownerUserId: raw.owner_user_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapHistory(raw: any): DpQueryHistory {
  return {
    id: raw.id,
    sourceId: raw.source_id,
    userId: raw.user_id,
    sqlText: raw.sql_text,
    status: raw.status,
    rowCount: raw.row_count,
    elapsedMs: raw.elapsed_ms,
    errorMessage: raw.error_message,
    columnsJson: raw.columns_json,
    startedAt: raw.started_at,
    finishedAt: raw.finished_at,
    createdAt: raw.created_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapChatSession(raw: any): DpChatSession {
  return {
    id: raw.id,
    name: raw.name,
    sourceId: raw.source_id,
    userId: raw.user_id,
    modelConfigId: raw.model_config_id,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapChatMessage(raw: any): DpChatMessage {
  return {
    id: raw.id,
    sessionId: raw.session_id,
    role: raw.role,
    content: raw.content,
    generatedSql: raw.generated_sql,
    executed: raw.executed,
    createdAt: raw.created_at,
  };
}

// -- service ----------------------------------------------------

export const dataPlatformService = {
  async listSources(): Promise<DpDataSource[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/data-platform/sources'));
    return list.map(mapDataSource);
  },

  async getSource(id: number): Promise<DpDataSource> {
    return mapDataSource(unwrap(await api.get(`/data-platform/sources/${id}`)));
  },

  async createSource(payload: DpDataSourceCreate): Promise<DpDataSource> {
    return mapDataSource(unwrap(await api.post('/data-platform/sources', payload)));
  },

  async updateSource(id: number, payload: DpDataSourceUpdate): Promise<DpDataSource> {
    return mapDataSource(unwrap(await api.put(`/data-platform/sources/${id}`, payload)));
  },

  async deleteSource(id: number): Promise<void> {
    unwrap(await api.delete(`/data-platform/sources/${id}`));
  },

  async parseConfig(rawText: string): Promise<ParseConfigResult> {
    const data = unwrap<{
      parsed: ParseConfigParsed;
      model_used: string;
      warnings: string[] | null;
    }>(
      await api.post('/data-platform/sources/parse-config', {
        raw_text: rawText,
      }),
    );
    return {
      parsed: { ...data.parsed, password: '' }, // double safety
      model_used: data.model_used,
      warnings: data.warnings ?? [],
    };
  },

  async testConnection(id: number): Promise<DpTestResult> {
    return mapTestResult(unwrap(await api.post(`/data-platform/sources/${id}/test`)));
  },

  async describeSchema(id: number): Promise<DpSchemaResponse> {
    return unwrap<DpSchemaResponse>(await api.get(`/data-platform/sources/${id}/schema`));
  },

  // execute
  async executeSync(sourceId: number, sql: string, maxRows = 1000): Promise<DpExecuteResponse> {
    return mapExecuteResponse(
      unwrap(
        await api.post(`/data-platform/sources/${sourceId}/execute`, {
          sql,
          max_rows: maxRows,
        }),
      ),
    );
  },

  buildStreamUrl(sourceId: number, sql: string, maxRows = 100_000): string {
    const base = api.defaults.baseURL ?? 'http://localhost:8000/api/v1';
    // Use form-urlencoded encoding (space -> '+', reserved chars like '*' -> %XX)
    // to match backend `urllib.parse.parse_qs` expectation.
    const enc = (v: string): string =>
      encodeURIComponent(v)
        .replace(/%20/g, '+')
        .replace(/[!'()*]/g, (c) => '%' + c.charCodeAt(0).toString(16).toUpperCase());
    const qs = `sql=${enc(sql)}&max_rows=${enc(String(maxRows))}`;
    return `${base}/data-platform/sources/${sourceId}/execute/stream?${qs}`;
  },

  // saved queries
  async listSaved(sourceId?: number): Promise<DpSavedQuery[]> {
    const params = sourceId ? { source_id: sourceId } : undefined;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/data-platform/saved-queries', { params }));
    return list.map(mapSavedQuery);
  },

  async createSaved(payload: {
    name: string;
    sourceId: number;
    sqlText: string;
    isFavorite?: boolean;
  }): Promise<DpSavedQuery> {
    return mapSavedQuery(
      unwrap(
        await api.post('/data-platform/saved-queries', {
          name: payload.name,
          source_id: payload.sourceId,
          sql_text: payload.sqlText,
          is_favorite: payload.isFavorite ?? false,
        }),
      ),
    );
  },

  async updateSaved(
    id: number,
    patch: { name?: string; sqlText?: string; isFavorite?: boolean },
  ): Promise<DpSavedQuery> {
    return mapSavedQuery(
      unwrap(
        await api.put(`/data-platform/saved-queries/${id}`, {
          name: patch.name,
          sql_text: patch.sqlText,
          is_favorite: patch.isFavorite,
        }),
      ),
    );
  },

  async deleteSaved(id: number): Promise<void> {
    unwrap(await api.delete(`/data-platform/saved-queries/${id}`));
  },

  // history
  async listHistory(sourceId?: number, limit = 50): Promise<DpQueryHistory[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const params: any = { limit };
    if (sourceId) params.source_id = sourceId;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/data-platform/history', { params }));
    return list.map(mapHistory);
  },

  // chat
  async listSessions(): Promise<DpChatSession[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(await api.get('/data-platform/chat/sessions'));
    return list.map(mapChatSession);
  },

  async createSession(payload: {
    name: string;
    sourceId: number;
    modelConfigId?: number | null;
  }): Promise<DpChatSession> {
    return mapChatSession(
      unwrap(
        await api.post('/data-platform/chat/sessions', {
          name: payload.name,
          source_id: payload.sourceId,
          model_config_id: payload.modelConfigId ?? null,
        }),
      ),
    );
  },

  async getSession(id: number): Promise<DpChatSession> {
    return mapChatSession(unwrap(await api.get(`/data-platform/chat/sessions/${id}`)));
  },

  async deleteSession(id: number): Promise<void> {
    unwrap(await api.delete(`/data-platform/chat/sessions/${id}`));
  },

  async listMessages(sessionId: number): Promise<DpChatMessage[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const list = unwrap<any[]>(
      await api.get(`/data-platform/chat/sessions/${sessionId}/messages`),
    );
    return list.map(mapChatMessage);
  },

  async sendMessage(sessionId: number, content: string): Promise<DpChatMessage> {
    return mapChatMessage(
      unwrap(
        await api.post(`/data-platform/chat/sessions/${sessionId}/messages`, { content }),
      ),
    );
  },

  async applyMessage(sessionId: number, messageId: number): Promise<DpExecuteResponse> {
    return mapExecuteResponse(
      unwrap(
        await api.post(`/data-platform/chat/sessions/${sessionId}/apply/${messageId}`),
      ),
    );
  },
};

export default dataPlatformService;
