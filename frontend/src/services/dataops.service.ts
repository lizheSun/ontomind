/** DataOps API */
import api from './api';
import type {
  ColumnInfo,
  ConnectionTestResult,
  DataSource,
  DataSourceCreate,
  ExecuteSqlResult,
  SampleResult,
  TableInfo,
} from '../types/dataops';

const B = '/dataops';

export async function listDataSources(): Promise<DataSource[]> {
  const res = await api.get(`${B}/sources`);
  return res.data as DataSource[];
}

export async function createDataSource(data: DataSourceCreate): Promise<DataSource> {
  const res = await api.post(`${B}/sources`, data);
  return res.data as DataSource;
}

export async function deleteDataSource(id: number): Promise<void> {
  await api.delete(`${B}/sources/${id}`);
}

export async function testDataSource(payload: {
  source_id?: number;
  source_type?: string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  database?: string;
  charset?: string;
}): Promise<ConnectionTestResult> {
  const res = await api.post(`${B}/sources/test`, payload);
  return res.data as ConnectionTestResult;
}

export async function listDatabases(sourceId: number): Promise<string[]> {
  const res = await api.get(`${B}/sources/${sourceId}/databases`);
  return (res.data?.data ?? res.data) as string[];
}

export async function listTables(sourceId: number, database: string): Promise<TableInfo[]> {
  const res = await api.get(`${B}/sources/${sourceId}/tables`, { params: { database } });
  return (res.data?.data ?? res.data) as TableInfo[];
}

export async function listColumns(
  sourceId: number,
  database: string,
  table: string,
): Promise<ColumnInfo[]> {
  const res = await api.get(`${B}/sources/${sourceId}/columns`, {
    params: { database, table },
  });
  return (res.data?.data ?? res.data) as ColumnInfo[];
}

export async function sampleTable(
  sourceId: number,
  payload: { database?: string; table: string; limit?: number },
): Promise<SampleResult> {
  const res = await api.post(`${B}/sources/${sourceId}/sample`, payload);
  return res.data as SampleResult;
}

export async function executeSql(
  sourceId: number,
  payload: { sql: string; database?: string; max_rows?: number },
): Promise<ExecuteSqlResult> {
  const res = await api.post(`${B}/sources/${sourceId}/execute`, payload);
  return res.data as ExecuteSqlResult;
}
