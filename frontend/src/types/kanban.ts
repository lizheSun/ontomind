export type RunStatus = 'pending' | 'running' | 'waiting' | 'completed' | 'failed';
export type PluginId = 'opencode' | 'dsh';

export interface KanbanColumn {
  id: number;
  board_id: number;
  name: string;
  icon?: string | null;
  color?: string | null;
  position: number;
  collapsed: boolean;
  task_count: number;
}

export interface KanbanTask {
  id: number;
  board_id: number;
  column_id: number | null;
  session_id: number | null;
  title: string;
  plugin_id: PluginId | string;
  run_status: RunStatus | string;
  position: number;
  summary?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface KanbanBoard {
  id: number;
  name: string;
  icon?: string | null;
  color?: string | null;
  position: number;
  task_count: number;
  columns: KanbanColumn[];
  created_at?: string | null;
  updated_at?: string | null;
}
