/** 用户模块类型定义 */
export interface User {
  id: number;
  username: string;
  email: string;
  fullName?: string;
  isActive: boolean;
  isSuperuser: boolean;
  createdAt?: string;
  updatedAt?: string;
  displayName?: string;
}

/** 创建用户请求 */
export interface UserCreateRequest {
  username: string;
  email: string;
  password: string;
  fullName?: string;
}

/** 更新用户请求 */
export interface UserUpdateRequest {
  username?: string;
  email?: string;
  password?: string;
  fullName?: string;
  isActive?: boolean;
}

/** 用户响应 */
export interface UserResponse {
  code: string;
  message: string;
  data: User;
}

/** 用户列表响应 */
export interface UserListResponse {
  code: string;
  message: string;
  data: User[];
  total: number;
}

/** 用户登录请求 */
export interface UserLoginRequest {
  username: string;
  password: string;
}

/** 用户登录响应 */
export interface UserLoginResponse {
  code: string;
  message: string;
  data: {
    accessToken: string;
    tokenType: string;
    user: User;
  };
}
