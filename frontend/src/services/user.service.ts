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

/** 后端返回的用户数据（snake_case） */
interface BackendUser {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  display_name?: string;
  created_at?: string;
  updated_at?: string;
}

/** 将后端下划线字段转为前端驼峰 */
function mapUser(raw: BackendUser): User {
  return {
    id: raw.id,
    username: raw.username,
    email: raw.email,
    fullName: raw.full_name || '',
    isActive: raw.is_active,
    isSuperuser: raw.is_superuser,
    displayName: raw.display_name || raw.full_name || raw.username,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

/** 用户模块 API 服务 */
export const userService = {
  /** 获取用户列表 */
  getUsers: async (params?: {
    skip?: number;
    limit?: number;
    activeOnly?: boolean;
  }): Promise<UserListResponse> => {
    const response = await api.get('/users', {
      params: {
        skip: params?.skip,
        limit: params?.limit,
        active_only: params?.activeOnly,
      },
    });
    const body = response.data;
    return {
      code: body.code,
      message: body.message,
      data: (body.data || []).map(mapUser),
      total: body.total,
    };
  },

  /** 获取用户详情 */
  getUser: async (id: number): Promise<UserResponse> => {
    const response = await api.get(`/users/${id}`);
    const body = response.data;
    return { code: body.code, message: body.message, data: mapUser(body.data) };
  },

  /** 创建用户 */
  createUser: async (data: UserCreateRequest): Promise<UserResponse> => {
    const response = await api.post('/users', data);
    const body = response.data;
    return { code: body.code, message: body.message, data: mapUser(body.data) };
  },

  /** 更新用户 */
  updateUser: async (id: number, data: UserUpdateRequest): Promise<UserResponse> => {
    const response = await api.put(`/users/${id}`, data);
    const body = response.data;
    return { code: body.code, message: body.message, data: mapUser(body.data) };
  },

  /** 删除用户 */
  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}`);
  },

  /** 用户登录 - 调用 /auth/login */
  login: async (data: UserLoginRequest): Promise<UserLoginResponse> => {
    const response = await api.post('/auth/login', data);
    const body = response.data;
    const { access_token, token_type, user: rawUser } = body.data;
    return {
      code: body.code,
      message: body.message,
      data: {
        accessToken: access_token,
        tokenType: token_type,
        user: mapUser(rawUser),
      },
    };
  },

  /** 获取当前登录用户 - 调用 /auth/me */
  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await api.get('/auth/me');
    const body = response.data;
    return { code: body.code, message: body.message, data: mapUser(body.data) };
  },
};

export default userService;
