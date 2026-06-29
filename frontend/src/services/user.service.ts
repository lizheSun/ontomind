import api from './api';
import type {
  User,
  UserCreateRequest,
  UserUpdateRequest,
  UserResponse,
  UserListResponse,
  UserLoginRequest,
  UserLoginResponse,
} from '../types/user';

/** 用户模块 API 服务 */
export const userService = {
  /** 获取用户列表 */
  getUsers: async (params?: {
    skip?: number;
    limit?: number;
    activeOnly?: boolean;
  }): Promise<UserListResponse> => {
    const response = await api.get<UserListResponse>('/users', { params });
    return response.data;
  },

  /** 获取用户详情 */
  getUser: async (id: number): Promise<UserResponse> => {
    const response = await api.get<UserResponse>(`/users/${id}`);
    return response.data;
  },

  /** 创建用户 */
  createUser: async (data: UserCreateRequest): Promise<UserResponse> => {
    const response = await api.post<UserResponse>('/users', data);
    return response.data;
  },

  /** 更新用户 */
  updateUser: async (id: number, data: UserUpdateRequest): Promise<UserResponse> => {
    const response = await api.put<UserResponse>(`/users/${id}`, data);
    return response.data;
  },

  /** 删除用户 */
  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}`);
  },

  /** 用户登录 */
  login: async (data: UserLoginRequest): Promise<UserLoginResponse> => {
    const response = await api.post<UserLoginResponse>('/users/login', data);
    return response.data;
  },
};

export default userService;
