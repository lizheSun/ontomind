import api from './api';
import type { KanbanBoard, KanbanColumn, KanbanTask, PluginId, RunStatus } from '../types/kanban';

function asArray<T>(data: unknown): T[] {
  return Array.isArray(data) ? (data as T[]) : [];
}

export const kanbanService = {
  async listBoards(): Promise<KanbanBoard[]> {
    const res = await api.get('/kanban/boards');
    return asArray<KanbanBoard>(res.data);
  },

  async createBoard(name: string, fromTemplate = true): Promise<KanbanBoard> {
    const res = await api.post('/kanban/boards', { name, from_template: fromTemplate });
    return res.data as KanbanBoard;
  },

  async getBoard(id: number): Promise<KanbanBoard> {
    const res = await api.get(`/kanban/boards/${id}`);
    return res.data as KanbanBoard;
  },

  async deleteBoard(id: number): Promise<void> {
    await api.delete(`/kanban/boards/${id}`);
  },

  async createColumn(boardId: number, name: string): Promise<KanbanColumn> {
    const res = await api.post(`/kanban/boards/${boardId}/columns`, { name });
    return res.data as KanbanColumn;
  },

  async deleteColumn(columnId: number): Promise<void> {
    await api.delete(`/kanban/columns/${columnId}`);
  },

  async listTasks(boardId: number, runStatus?: string): Promise<KanbanTask[]> {
    const res = await api.get(`/kanban/boards/${boardId}/tasks`, {
      params: runStatus && runStatus !== 'all' ? { run_status: runStatus } : undefined,
    });
    return asArray<KanbanTask>(res.data);
  },

  async createTask(
    boardId: number,
    data: { title: string; plugin_id: PluginId; column_id?: number },
  ): Promise<KanbanTask> {
    const res = await api.post(`/kanban/boards/${boardId}/tasks`, data);
    return res.data as KanbanTask;
  },

  async moveTask(taskId: number, columnId: number, position: number): Promise<KanbanTask> {
    const res = await api.put(`/kanban/tasks/${taskId}/move`, { column_id: columnId, position });
    return res.data as KanbanTask;
  },

  async deleteTask(taskId: number): Promise<void> {
    await api.delete(`/kanban/tasks/${taskId}`);
  },

  async updateTask(taskId: number, data: { run_status?: RunStatus; title?: string }): Promise<KanbanTask> {
    const res = await api.patch(`/kanban/tasks/${taskId}`, data);
    return res.data as KanbanTask;
  },
};
