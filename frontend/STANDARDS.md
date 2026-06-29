# OntoMind 前端开发规范

> **版本**: v1.0.0  
> **更新日期**: 2026-06-29  
> **适用范围**: OntoMind 项目前端开发

---

## 目录

1. [架构概览](#1-架构概览)
2. [代码组织规范](#2-代码组织规范)
3. [命名规范](#3-命名规范)
4. [TypeScript 类型定义规范](#4-typescript-类型定义规范)
5. [API 服务层规范](#5-api-服务层规范)
6. [状态管理规范](#6-状态管理规范)
7. [组件设计规范](#7-组件设计规范)
8. [错误处理规范](#8-错误处理规范)
9. [样式规范](#9-样式规范)
10. [测试规范](#10-测试规范)
11. [最佳实践](#11-最佳实践)

---

## 1. 架构概览

### 1.1 前端技术栈

- **框架**: React 19
- **语言**: TypeScript 5.x
- **UI 库**: Ant Design 6
- **状态管理**: Zustand
- **HTTP 客户端**: Axios
- **路由**: React Router 7
- **构建工具**: Vite
- **图表**: ECharts

### 1.2 目录结构

```
frontend/src/
├── types/              # TypeScript 类型定义
│   ├── user.ts         # 用户模块类型
│   ├── api.ts          # API 通用类型
│   └── index.ts        # 类型导出
├── services/           # API 服务层
│   ├── api.ts          # Axios 实例配置
│   ├── user.service.ts # 用户模块 API
│   └── index.ts        # 服务导出
├── stores/             # Zustand 状态管理
│   ├── appStore.ts     # 应用全局状态
│   ├── userStore.ts    # 用户状态
│   └── index.ts        # Store 导出
├── components/         # 可复用组件
│   ├── layout/         # 布局组件
│   ├── common/         # 通用组件
│   └── ...
├── pages/              # 页面组件
│   ├── dashboard/      # 仪表盘
│   ├── perception/     # 感知层
│   ├── cognition/      # 认知层
│   ├── decision/       # 决策层
│   ├── execution/      # 执行层
│   ├── application/    # 应用层
│   └── Login.tsx       # 登录页
├── utils/              # 工具函数
│   ├── request.ts      # 请求工具
│   ├── constants.ts    # 常量定义
│   └── helpers.ts      # 辅助函数
├── hooks/              # 自定义 Hooks
│   ├── useAuth.ts      # 认证 Hook
│   └── ...
├── assets/             # 静态资源
│   ├── images/         # 图片
│   ├── styles/         # 全局样式
│   └── ...
├── App.tsx             # 根组件
└── main.tsx            # 入口文件
```

---

## 2. 代码组织规范

### 2.1 模块组织原则

**按功能模块组织代码**，每个功能模块包含：
- 类型定义 (`types/{module}.ts`)
- API 服务 (`services/{module}.service.ts`)
- 状态管理 (`stores/{module}Store.ts`)
- 页面组件 (`pages/{module}/`)
- 专用组件 (`components/{module}/`)

**示例：用户模块**
```
frontend/src/
├── types/user.ts           # 用户类型定义
├── services/user.service.ts # 用户 API 服务
├── stores/userStore.ts     # 用户状态
└── pages/profile/          # 用户资料页面
```

### 2.2 导入顺序

```typescript
// 1. React 相关
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// 2. 第三方库
import { Button, Table, message } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import axios from 'axios';

// 3. 本地模块（按依赖顺序）
import api from '../services/api';
import { User } from '../types/user';
import { useUserStore } from '../stores/userStore';
import UserService from '../services/user.service';

// 4. 样式
import './UserPage.css';
```

---

## 3. 命名规范

### 3.1 文件命名

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| 页面组件 | `PascalCase` | `UserPage.tsx`, `Login.tsx` |
| 可复用组件 | `PascalCase` | `DataTable.tsx`, `UserForm.tsx` |
| 服务文件 | `camelCase.service.ts` | `user.service.ts`, `auth.service.ts` |
| 类型文件 | `camelCase.ts` | `user.ts`, `api.ts` |
| Store 文件 | `camelCaseStore.ts` | `userStore.ts`, `appStore.ts` |
| Hook 文件 | `usePascalCase.ts` | `useAuth.ts`, `useTable.ts` |
| 工具文件 | `camelCase.ts` | `request.ts`, `helpers.ts` |

### 3.2 变量/函数命名

| 类型 | 命名模式 | 示例 |
|------|---------|------|
| 变量/函数 | `camelCase` | `userName`, `getUserInfo()` |
| 组件 | `PascalCase` | `UserPage`, `DataTable` |
| 常量 | `UPPER_SNAKE_CASE` | `API_BASE_URL`, `DEFAULT_PAGE_SIZE` |
| 类型/接口 | `PascalCase` | `User`, `UserResponse`, `UserService` |
| 泛型参数 | `PascalCase` (单大写字母) | `T`, `TData`, `TResponse` |

### 3.3 CSS 类名命名

使用 **BEM 命名规范** (Block__Element--Modifier)：

```css
/* Block */
.user-card { }

/* Element */
.user-card__avatar { }
.user-card__name { }
.user-card__button { }

/* Modifier */
.user-card--active { }
.user-card__button--primary { }
```

---

## 4. TypeScript 类型定义规范

### 4.1 类型定义文件组织

**每个功能模块一个类型文件**，放在 `types/` 目录下。

### 4.2 类型定义示例

```typescript
// types/user.ts

// 基础用户类型
export interface User {
  id: number;
  username: string;
  email: string;
  fullName?: string;
  avatar?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

// 创建用户请求
export interface UserCreateRequest {
  username: string;
  email: string;
  password: string;
  fullName?: string;
}

// 更新用户请求
export interface UserUpdateRequest {
  username?: string;
  email?: string;
  password?: string;
  fullName?: string;
  isActive?: boolean;
}

// 用户响应
export interface UserResponse {
  code: string;
  message: string;
  data: User;
}

// 用户列表响应
export interface UserListResponse {
  code: string;
  message: string;
  data: User[];
  total: number;
}

// 用户登录请求
export interface UserLoginRequest {
  username: string;
  password: string;
}

// 用户登录响应
export interface UserLoginResponse {
  code: string;
  message: string;
  data: {
    accessToken: string;
    tokenType: string;
    user: User;
  };
}
```

### 4.3 类型定义最佳实践

1. ✅ 使用 `interface` 定义对象类型（更易扩展）
2. ✅ 使用 `type` 定义联合类型或交叉类型
3. ✅ 为 API 请求和响应分别定义类型
4. ✅ 使用可选属性 (`?`) 表示可能不存在的字段
5. ✅ 使用泛型提高代码复用性
6. ❌ 避免使用 `any` 类型
7. ❌ 避免重复定义类型（使用 `extends` 或交叉类型）

---

## 5. API 服务层规范

### 5.1 服务层职责

- 封装 API 调用
- 统一处理请求/响应
- 错误处理
- 类型安全

### 5.2 服务层示例

```typescript
// services/user.service.ts

import api from './api';
import type { 
  User, 
  UserCreateRequest, 
  UserUpdateRequest, 
  UserResponse, 
  UserListResponse,
  UserLoginRequest,
  UserLoginResponse 
} from '../types/user';

export const userService = {
  // 获取用户列表
  getUsers: async (params?: {
    skip?: number;
    limit?: number;
    activeOnly?: boolean;
  }): Promise<UserListResponse> => {
    const response = await api.get<UserListResponse>('/users', { params });
    return response.data;
  },

  // 获取用户详情
  getUser: async (id: number): Promise<UserResponse> => {
    const response = await api.get<UserResponse>(`/users/${id}`);
    return response.data;
  },

  // 创建用户
  createUser: async (data: UserCreateRequest): Promise<UserResponse> => {
    const response = await api.post<UserResponse>('/users', data);
    return response.data;
  },

  // 更新用户
  updateUser: async (id: number, data: UserUpdateRequest): Promise<UserResponse> => {
    const response = await api.put<UserResponse>(`/users/${id}`, data);
    return response.data;
  },

  // 删除用户
  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}`);
  },

  // 用户登录
  login: async (data: UserLoginRequest): Promise<UserLoginResponse> => {
    const response = await api.post<UserLoginResponse>('/users/login', data);
    return response.data;
  },
};

export default userService;
```

### 5.3 API 实例配置

```typescript
// services/api.ts

import axios, { type AxiosInstance, type AxiosResponse } from 'axios';
import type { ApiResponse } from '../types/api';

// 创建 Axios 实例
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 附加 JWT Token
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    // 统一处理响应
    return response;
  },
  (error) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      // Token 过期，跳转登录页
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    
    // 显示错误信息
    const message = error.response?.data?.message || '请求失败';
    // 可以使用 antd 的 message 组件显示错误
    // message.error(message);
    
    return Promise.reject(error);
  }
);

export default api;
```

---

## 6. 状态管理规范

### 6.1 Zustand Store 组织

**每个功能模块一个 Store 文件**，放在 `stores/` 目录下。

### 6.2 Store 示例

```typescript
// stores/userStore.ts

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
  createUser: (data: Parameters<typeof userService.createUser>[0]) => Promise<void>;
  updateUser: (id: number, data: Parameters<typeof userService.updateUser>[1]) => Promise<void>;
  deleteUser: (id: number) => Promise<void>;
  clearError: () => void;
}

export const useUserStore = create<UserState>((set, get) => ({
  // 初始状态
  currentUser: null,
  users: [],
  loading: false,
  error: null,

  // 操作方法
  setCurrentUser: (user) => set({ currentUser: user }),

  fetchCurrentUser: async () => {
    set({ loading: true, error: null });
    try {
      const response = await userService.getUser(1); // TODO: 获取当前登录用户 ID
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
        users: state.users.map((user) =>
          user.id === id ? response.data : user
        ),
        currentUser: state.currentUser?.id === id ? response.data : state.currentUser,
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
```

### 6.3 Store 最佳实践

1. ✅ 使用 TypeScript 定义 Store 接口
2. ✅ 将相关状态和方法组织在同一个 Store 中
3. ✅ 使用 `set` 函数更新状态
4. ✅ 使用 `get` 函数读取状态
5. ✅ 异步操作使用 `async/await`
6. ✅ 统一处理 loading 和 error 状态
7. ❌ 避免在 Store 中直接操作 DOM
8. ❌ 避免在 Store 中进行复杂的业务逻辑（应该放在 Service 层）

---

## 7. 组件设计规范

### 7.1 组件分类

1. **页面组件** (`pages/`): 对应路由的页面级组件
2. **容器组件** (`components/`): 包含业务逻辑的组件
3. **展示组件** (`components/`): 纯展示型组件，不依赖业务逻辑

### 7.2 组件设计原则

1. **单一职责**: 每个组件只做一件事
2. **可复用性**: 通用组件应该高度抽象
3. **受控组件**: 尽量使用受控组件（状态由父组件控制）
4. **PropTypes/TypeScript**: 使用 TypeScript 定义 Props 类型

### 7.3 组件示例

```typescript
// components/UserForm.tsx

import React, { useState } from 'react';
import { Form, Input, Button, message } from 'antd';
import type { UserCreateRequest } from '../types/user';
import userService from '../services/user.service';

interface UserFormProps {
  onSuccess?: (user: UserCreateRequest) => void;
  initialValues?: Partial<UserCreateRequest>;
}

const UserForm: React.FC<UserFormProps> = ({ onSuccess, initialValues }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: UserCreateRequest) => {
    setLoading(true);
    try {
      const response = await userService.createUser(values);
      message.success('用户创建成功');
      form.resetFields();
      onSuccess?.(response.data);
    } catch (error: any) {
      message.error(error.message || '用户创建失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      form={form}
      initialValues={initialValues}
      onFinish={handleSubmit}
      layout="vertical"
    >
      <Form.Item
        name="username"
        label="用户名"
        rules={[{ required: true, message: '请输入用户名' }]}
      >
        <Input placeholder="请输入用户名" />
      </Form.Item>

      <Form.Item
        name="email"
        label="邮箱"
        rules={[
          { required: true, message: '请输入邮箱' },
          { type: 'email', message: '请输入有效的邮箱地址' },
        ]}
      >
        <Input placeholder="请输入邮箱" />
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading}>
          提交
        </Button>
      </Form.Item>
    </Form>
  );
};

export default UserForm;
```

---

## 8. 错误处理规范

### 8.1 错误类型

1. **网络错误**: 请求超时、网络断开
2. **业务错误**: 后端返回的业务异常（如用户名已存在）
3. **认证错误**: Token 过期、权限不足
4. **前端错误**: 代码逻辑错误、类型错误

### 8.2 错误处理策略

```typescript
// utils/errorHandler.ts

import { message } from 'antd';
import type { AxiosError } from 'axios';

export const handleError = (error: unknown): void => {
  if (error instanceof AxiosError) {
    // Axios 错误
    const errorMessage = error.response?.data?.message || error.message;
    message.error(errorMessage);
  } else if (error instanceof Error) {
    // JavaScript 错误
    message.error(error.message);
  } else {
    // 未知错误
    message.error('发生未知错误');
  }
  
  // 可以在这里添加错误上报逻辑
  // errorReporting.captureException(error);
};
```

---

## 9. 样式规范

### 9.1 样式方案

**推荐使用 CSS Modules** 或 **Styled Components**，避免全局样式污染。

### 9.2 样式示例

```css
/* UserPage.module.css */

.container {
  padding: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.table {
  margin-top: 16px;
}

/* 使用 CSS 变量实现主题 */
:root {
  --primary-color: #1890ff;
  --success-color: #52c41a;
  --warning-color: #faad14;
  --error-color: #f5222d;
}
```

---

## 10. 测试规范

### 10.1 测试工具

- **单元测试**: Vitest
- **组件测试**: React Testing Library
- **E2E 测试**: Playwright

### 10.2 测试示例

```typescript
// __tests__/user.service.test.ts

import { describe, it, expect, vi } from 'vitest';
import axios from 'axios';
import { userService } from '../services/user.service';

vi.mock('axios');

describe('User Service', () => {
  it('should fetch users', async () => {
    const mockResponse = {
      data: {
        code: 'SUCCESS',
        message: '操作成功',
        data: [],
        total: 0,
      },
    };
    
    (axios.get as any).mockResolvedValue(mockResponse);
    
    const result = await userService.getUsers();
    expect(result.data).toEqual([]);
  });
});
```

---

## 11. 最佳实践

### 11.1 性能优化

1. **代码分割**: 使用 React.lazy 和 Suspense 实现路由级代码分割
2. **懒加载**: 图片、组件懒加载
3. **防抖/节流**: 搜索框、滚动事件使用防抖/节流
4. **虚拟列表**: 长列表使用虚拟滚动（如 react-window）

### 11.2 安全性

1. **XSS 防护**: 避免使用 `dangerouslySetInnerHTML`
2. **CSRF 防护**: 使用 CSRF Token
3. **敏感数据**: 不在前端存储敏感数据（如密码）
4. **Token 管理**: 使用 HttpOnly Cookie 或安全的 localStorage 管理 Token

### 11.3 可访问性

1. **语义化 HTML**: 使用正确的 HTML 标签
2. **ARIA 属性**: 为交互元素添加 ARIA 属性
3. **键盘导航**: 支持键盘导航
4. **焦点管理**: 合理的焦点管理

---

## 12. 检查清单

在提交代码前，请检查：

- [ ] 是否遵循了命名规范？
- [ ] 是否添加了必要的 TypeScript 类型定义？
- [ ] 是否处理了可能的错误？
- [ ] 是否编写了单元测试？
- [ ] 是否优化了性能（如需要）？
- [ ] 是否添加了必要的注释？
- [ ] 是否通过了 ESLint 和 Prettier 检查？

---

**本规范将随着项目发展不断更新和完善。如有疑问或建议，请提交 Issue 或 Pull Request。**
