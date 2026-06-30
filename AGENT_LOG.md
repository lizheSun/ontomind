# Agent 操作记录

> **用途**: 多 Agent 协同开发时，记录每次操作的目的、内容和影响范围，方便其他 Agent 快速理解上下文。

---

## 2025-06-30

### Agent: 主开发 Agent（下午 — UI/UE 框架重构）

### 目标
将前端整体替换为**硅谷风格**设计系统，涵盖暗色主题、玻璃拟态、渐变光晕、点阵背景、精致排版。

### 设计决策
| 维度 | 选择 |
|------|------|
| 主题 | Ant Design `darkAlgorithm` + 自定义覆写 |
| 字体 | Plus Jakarta Sans（Google Fonts）+ JetBrains Mono |
| 主色 | 蓝 `#3b82f6` → 紫 `#8b5cf6` → 青 `#06b6d4` 三色渐变 |
| 背景 | `#060b14` 根背景，`32px` 间距点阵纹理 |
| 玻璃效果 | `backdrop-filter: blur(12-20px)` + 半透明渐变 |
| 动效 | `cubic-bezier(0.16, 1, 0.3, 1)` 弹性曲线 |

### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/styles/global.css` | 全局设计系统：CSS 变量（60+ Token）、动画关键帧（6 组）、点阵背景、玻璃拟态工具类、antd 组件 20+ 覆写 |

### 重写文件
| 文件 | 变更要点 |
|------|---------|
| `frontend/index.html` | 标题、lang、theme-color meta |
| `frontend/src/main.tsx` | 导入 global.css |
| `frontend/src/App.tsx` | `darkAlgorithm`、覆写全部 token、添加 `App` 包裹 |
| `frontend/src/components/layout/AppLayout.tsx` | 分组菜单（五层架构 group）、毛玻璃侧边栏、粘性顶栏、Logo 渐变图标、页面入场 `.page-enter` 错开动画 |
| `frontend/src/pages/Login.tsx` | 全屏暗色背景、双色模糊光球、玻璃拟态卡片、入场淡入 |
| `frontend/src/pages/dashboard/index.tsx` | 渐变色统计卡片、彩色图标容器、五层状态彩色指示灯 |
| `frontend/src/pages/perception/index.tsx` | Tag 颜色系统重构、Card 标题带图标 |
| `frontend/src/pages/cognition/index.tsx` | 图谱占位区渐变背景、语义搜索、实体/关系表格统一 Tag 风格 |
| `frontend/src/pages/decision/index.tsx` | 决策层 3 统计卡片、策略状态色彩映射表 |
| `frontend/src/pages/execution/index.tsx` | 监控指标彩色数字、目标系统在线 Tag、执行状态映射 |
| `frontend/src/pages/application/index.tsx` | AIbi 输入区渐变底层、数据集/仪表盘卡片 |
| `frontend/src/pages/users/index.tsx` | 用户表格外容器玻璃态、角色/状态彩色 Tag |

### Bug 修复
- 修复 `cognition/index.tsx` 缺少 `NodeIndexOutlined` 导入导致白屏
- 修复 `AppLayout.tsx` 误用 `useUserStore` 获取 sidebar 状态（改为 `useAppStore`）

### 验证
- TypeScript 编译零错误
- 20 个文件变更，+1646 / -267 行

---

### Agent: 主开发 Agent（上午 — 全链路打通）

### 目标
打通前后端全链路，实现用户注册/登录/删除完整功能，并使用本地 MySQL 数据库。

### 后端修复
| 文件 | 修复内容 |
|------|----------|
| `backend/app/core/exceptions.py` | 新增 `UnauthorizedException`（auth_service 之前引用但未定义） |
| `backend/app/api/v1/router.py` | 挂载 users 路由（之前遗漏） |
| `backend/app/api/v1/users.py` | 移除 router 内的 `prefix="/users"`（避免与 include_router 的 prefix 重复）；移除重复的 login 端点；路由重新排序避免 GET "" 与 GET "/{user_id}" 冲突 |
| `backend/app/api/v1/auth.py` | `/me` 端点从硬编码改为从 JWT Authorization Header 提取 user_id；`get_current_user_id` 依赖注入; register 改用 UserCreate Pydantic 校验 |
| `backend/app/services/auth_service.py` | 补充缺失的 `NotFoundException` 导入 |
| `backend/app/main.py` | 注册全局异常处理器 `add_exception_handlers(app)` |
| `backend/.env` | 新建：配置 DB_USER=root（无密码），匹配本地 MySQL |

### 数据库
- 创建 MySQL 数据库 `ontomind`（utf8mb4）
- SQLAlchemy `Base.metadata.create_all()` 初始化 `users` 表
- 注意：bcrypt 需用 4.x 版本（5.x 与 passlib 不兼容）

### 前端修复
| 文件 | 修复内容 |
|------|----------|
| `frontend/src/App.tsx` | 重写：移除循环引用，正确配置 react-router-dom Routes（公开 /login + 受保护路由 + 404 兜底） |
| `frontend/src/pages/Login.tsx` | 重写：真实对接 /auth/login 和 /auth/register API，支持登录+注册双 Tab |
| `frontend/src/services/user.service.ts` | login 改为 /auth/login，新增 getCurrentUser(/auth/me)；添加 snake_case→camelCase 映射 |
| `frontend/src/stores/userStore.ts` | fetchCurrentUser 调用 /auth/me |
| `frontend/src/components/layout/AppLayout.tsx` | 新增退出登录功能、当前用户显示、用户管理菜单项 |

### 新增文件
| 文件 | 说明 |
|------|------|
| `frontend/src/pages/users/index.tsx` | 用户管理页面（表格展示 + 新建 + 删除） |

### 验证结果
- ✅ 用户注册 POST /auth/register
- ✅ 用户登录 POST /auth/login → 返回 JWT Token
- ✅ 获取当前用户 GET /auth/me（JWT 认证）
- ✅ 用户列表 GET /users
- ✅ 用户删除 DELETE /users/{id}
- ✅ 后端运行在 :8000，前端运行在 :5173
- ✅ MySQL `ontomind` 数据库，root 无密码

### 已知问题
- 前端用户管理页面（/users）需手动登录后访问，登录/注册在 Login 页面的双 Tab 中

---

## 2025-06-29

### Agent: 主开发 Agent

### 目标
为 OntoMind 项目建立全栈开发规范和设计范式，实现后端三层架构（接口层/服务层/数据层）分层重构。

### 新增文件

#### 规范文档
| 文件 | 说明 |
|------|------|
| `backend/STANDARDS.md` | 后端开发规范：分层架构、事务控制、命名规范、错误处理、依赖注入 |
| `backend/DESIGN_STANDARDS.md` | API 设计标准（RESTful 规范、错误码）和数据库设计标准（表命名、字段命名、索引策略） |
| `backend/REFACTORING_GUIDE.md` | 现有代码重构指南，指导如何将旧代码迁移到三层架构 |
| `frontend/STANDARDS.md` | 前端开发规范：代码组织、TypeScript 类型、API 服务层、Zustand 状态管理 |

#### 后端基础架构
| 文件 | 说明 |
|------|------|
| `backend/app/db/models/base.py` | BaseModel - 所有 ORM 模型基类（含 id, created_at, updated_at） |
| `backend/app/db/repositories/base_repo.py` | BaseRepository - 数据层基类，封装通用 CRUD 方法 |
| `backend/app/services/base_service.py` | BaseService - 服务层基类，统一管理 db session 注入 |
| `backend/app/core/exceptions.py` | BusinessException - 统一业务异常类（含错误码 + HTTP 状态码） |
| `backend/app/core/decorators.py` | @transactional - 事务装饰器，自动管理 commit/rollback |

#### 安全工具（新增 + 重构）
| 文件 | 说明 |
|------|------|
| `backend/app/core/security.py` | 密码哈希（bcrypt）、JWT Token 生成/解码/验证 |

#### 用户模块示例（完整三层架构模板）
| 文件 | 层 | 说明 |
|------|------|------|
| `backend/app/db/models/user_model.py` | 数据层 | User ORM 模型 |
| `backend/app/db/repositories/user_repo.py` | 数据层 | UserRepository，含特有查询方法 |
| `backend/app/schemas/user_schema.py` | Schema | Pydantic 请求/响应校验模型 |
| `backend/app/services/user_service.py` | 服务层 | UserService，含事务控制、密码加密等业务逻辑 |
| `backend/app/api/v1/users.py` | 接口层 | User CRUD API 端点 |

#### 认证模块重构
| 文件 | 说明 |
|------|------|
| `backend/app/services/auth_service.py` | 新增 AuthService，处理登录/注册/获取当前用户逻辑 |
| `backend/app/api/v1/auth.py` | 重构：从占位代码改为调用 AuthService，统一响应格式 |

#### 前端示例
| 文件 | 说明 |
|------|------|
| `frontend/src/types/user.ts` | User 相关 TypeScript 类型定义 |
| `frontend/src/services/user.service.ts` | 用户 API 服务层封装 |
| `frontend/src/stores/userStore.ts` | Zustand Store，用户状态管理 |

### 修改文件
- `backend/app/api/v1/auth.py` - 重构为三层架构，注入 AuthService
- `backend/app/core/security.py` - 重构：新增 get_password_hash/get_current_user_id_from_token，返回类型改为 Dict

### 架构决策
1. **事务边界在服务层控制**：使用 `with self.db.begin()` 或 `@transactional` 装饰器
2. **接口层只做参数校验和响应格式化**：不包含任何业务逻辑
3. **数据层不处理业务逻辑**：只封装数据库查询操作
4. **统一异常体系**：所有业务异常抛出 `BusinessException`，由全局 handler 统一处理
5. **用户模块作为完整模板**：后续所有模块（perception/cognition 等）均参照此模式开发

### 后续待办
- [ ] 重构 `perception.py`、`cognition.py` 等其他 API 文件为三层架构
- [ ] 完善 JWT 认证中间件（当前 `/me` 端点临时硬编码 user_id=1）
- [ ] 创建 perceptions/cognitions 等模块的 Repository 和 Service
