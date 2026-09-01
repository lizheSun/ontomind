import { create } from 'zustand';
import { kanbanService } from '../services/kanban.service';
import type { KanbanBoard, KanbanTask } from '../types/kanban';

interface KanbanState {
  boards: KanbanBoard[];
  board: KanbanBoard | null;
  tasks: KanbanTask[];
  loading: boolean;
  error: string;
  loadBoards: () => Promise<KanbanBoard[]>;
  loadBoard: (id: number, runStatus?: string) => Promise<void>;
  createBoard: (name: string) => Promise<KanbanBoard>;
}

export const useKanbanStore = create<KanbanState>((set) => ({
  boards: [],
  board: null,
  tasks: [],
  loading: false,
  error: '',

  loadBoards: async () => {
    try {
      const boards = await kanbanService.listBoards();
      set({ boards, error: '' });
      return boards;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '加载看板失败' });
      return [];
    }
  },

  loadBoard: async (id, runStatus) => {
    set({ loading: true, error: '' });
    try {
      const [board, tasks] = await Promise.all([
        kanbanService.getBoard(id),
        kanbanService.listTasks(id, runStatus),
      ]);
      set((s) => ({
        board,
        tasks,
        loading: false,
        boards: s.boards.some((b) => b.id === board.id)
          ? s.boards.map((b) => (b.id === board.id ? board : b))
          : [board, ...s.boards],
      }));
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : '加载失败' });
    }
  },

  createBoard: async (name) => {
    const board = await kanbanService.createBoard(name);
    set((s) => ({ boards: [...s.boards, board] }));
    return board;
  },
}));
