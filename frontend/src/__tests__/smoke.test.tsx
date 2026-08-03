/**
 * 基础冒烟测试 — 验证精简后的应用能挂载、路由与导航符合预期。
 *
 * 2026-08-03 深度精简后项目只剩 2 个模块（AIDE / 用户管理），
 * 原来的 15 个 e2e spec（测感知层/数据平台/知识库/资源管理等）已随模块删除。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';

import AppLayout from '../components/layout/AppLayout';

// 后端接口全部 mock，避免测试依赖真实服务
vi.mock('../services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { code: 'SUCCESS', data: {} } }),
    post: vi.fn().mockResolvedValue({ data: { code: 'SUCCESS', data: {} } }),
    put: vi.fn().mockResolvedValue({ data: { code: 'SUCCESS', data: {} } }),
    patch: vi.fn().mockResolvedValue({ data: { code: 'SUCCESS', data: {} } }),
    delete: vi.fn().mockResolvedValue({ data: { code: 'SUCCESS', data: {} } }),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

function renderAt(path: string) {
  return render(
    <ConfigProvider>
      <AntApp>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/aide" replace />} />
              <Route path="aide" element={<div data-testid="aide-page">AIDE PAGE</div>} />
              <Route path="users" element={<div data-testid="users-page">USERS PAGE</div>} />
              {/* 已删模块 → 重定向 */}
              <Route path="experts/*" element={<Navigate to="/aide" replace />} />
              <Route path="compute/*" element={<Navigate to="/aide" replace />} />
              <Route path="data-platform/*" element={<Navigate to="/aide" replace />} />
              <Route path="knowledge-base/*" element={<Navigate to="/aide" replace />} />
              <Route path="perception" element={<Navigate to="/aide" replace />} />
              <Route path="workspace" element={<Navigate to="/aide" replace />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AntApp>
    </ConfigProvider>,
  );
}

describe('AppLayout 导航', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
  });

  it('渲染品牌名', () => {
    renderAt('/aide');
    expect(screen.getByText('OntoMind')).toBeInTheDocument();
  });

  it('菜单只有 AIDE 和用户管理两项', () => {
    renderAt('/aide');
    expect(screen.getByText('AIDE')).toBeInTheDocument();
    expect(screen.getByText('用户管理')).toBeInTheDocument();
  });

  it.each([
    '专家团',
    '算力调度',
    '数据平台',
    '知识库',
    '感知层',
    '认知层',
    '决策层',
    '执行层',
    '对话工作台',
    '资源管理',
  ])('菜单不应再出现已删模块「%s」', (label) => {
    renderAt('/aide');
    expect(screen.queryByText(label)).not.toBeInTheDocument();
  });
});

describe('路由重定向', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
  });

  it('/aide 渲染 AIDE 页面', () => {
    renderAt('/aide');
    expect(screen.getByTestId('aide-page')).toBeInTheDocument();
  });

  it('/users 渲染用户管理页面', () => {
    renderAt('/users');
    expect(screen.getByTestId('users-page')).toBeInTheDocument();
  });

  it.each([
    '/experts',
    '/compute',
    '/data-platform',
    '/knowledge-base',
    '/perception',
    '/workspace',
  ])('已删路由 %s 重定向到 /aide', (path) => {
    renderAt(path);
    expect(screen.getByTestId('aide-page')).toBeInTheDocument();
  });
});
