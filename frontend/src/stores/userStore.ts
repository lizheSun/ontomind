import { create } from 'zustand';
import type { User } from '../types/user';
import userService from '../services/user.service';

interface UserState {
  // 状态
  currentUser: User | null;
  users: User[];
  loading: boolean;
  error: string | null;

  // 操作方法
  setCurrentUser: (user: User | null) => void;
  fetchCurrentUser: () => Promise<void>;
  fetchUsers: (params?: { skip?: number; limit?: number }) => Promise<void>;
  createUser: (data: Parameters<typeof userService.createUser>[0]) => Promise<User>;
  updateUser: (
    id: number,
    data: Parameters<typeof userService.updateUser>[1],
  ) => Promise<void>;
  deleteUser: (id: number) => Promise<void>;
  clearError: () => void;
}

export const useUserStore = create<UserState>((set, get) => ({
  // 初始状态
  currentUser: null,
  users: [],
  loading: false,
  error: null,

  setCurrentUser: (user) => set({ currentUser: user }),

  fetchCurrentUser: async () => {
    set({ loading: true, error: null });
    try {
      const response = await userService.getCurrentUser();
      set({ currentUser: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  fetchUsers: async (params) => {
    set({ loading: true, error: null });
    try {
      const response = await userService.getUsers(params);
      set({ users: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createUser: async (data) => {
    set({ loading: true, error: null });
    try {
      const response = await userService.createUser(data);
      set((state) => ({
        users: [...state.users, response.data],
        loading: false,
      }));
      return response.data;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  updateUser: async (id, data) => {
    set({ loading: true, error: null });
    try {
      const response = await userService.updateUser(id, data);
      set((state) => ({
        users: state.users.map((user) => (user.id === id ? response.data : user)),
        currentUser:
          state.currentUser?.id === id ? response.data : state.currentUser,
        loading: false,
      }));
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  deleteUser: async (id) => {
    set({ loading: true, error: null });
    try {
      await userService.deleteUser(id);
      set((state) => ({
        users: state.users.filter((user) => user.id !== id),
        currentUser: state.currentUser?.id === id ? null : state.currentUser,
        loading: false,
      }));
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
}));

export default useUserStore;
