/**
 * 基础冒烟测试 — 验证 Yao 风格壳层：图标轨 + 域导航。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';

import AppLayout from '../components/layout/AppLayout';

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
              <Route index element={<Navigate to="/overview" replace />} />
              <Route path="overview" element={<div data-testid="overview-page">OVERVIEW</div>} />
              <Route path="chat" element={<div data-testid="chat-page">CHAT PAGE</div>} />
              <Route path="board" element={<div data-testid="board-page">BOARD PAGE</div>} />
              <Route path="infra/aide" element={<div data-testid="aide-page">AIDE PAGE</div>} />
              <Route path="users" element={<div data-testid="users-page">USERS PAGE</div>} />
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

  it('渲染品牌入口', () => {
    renderAt('/overview');
    expect(screen.getByTitle('OntoMind')).toBeInTheDocument();
  });

  it('图标轨包含总览、会话与六域', () => {
    renderAt('/overview');
    expect(screen.getByLabelText('总览')).toBeInTheDocument();
    expect(screen.getByLabelText('会话')).toBeInTheDocument();
    expect(screen.getByLabelText('看板')).toBeInTheDocument();
    expect(screen.getByLabelText('CodeOps')).toBeInTheDocument();
    expect(screen.getByLabelText('DataOps')).toBeInTheDocument();
    expect(screen.getByLabelText('ModelOps')).toBeInTheDocument();
    expect(screen.getByLabelText('AgentOps')).toBeInTheDocument();
    expect(screen.getByLabelText('GovOps')).toBeInTheDocument();
    expect(screen.getByLabelText('Infra')).toBeInTheDocument();
  });
});

describe('路由', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
  });

  it('/overview 渲染总览', () => {
    renderAt('/overview');
    expect(screen.getByTestId('overview-page')).toBeInTheDocument();
  });

  it('/chat 渲染会话', () => {
    renderAt('/chat');
    expect(screen.getByTestId('chat-page')).toBeInTheDocument();
  });

  it('/board 渲染看板', () => {
    renderAt('/board');
    expect(screen.getByTestId('board-page')).toBeInTheDocument();
  });

  it('/infra/aide 渲染 AIDE', () => {
    renderAt('/infra/aide');
    expect(screen.getByTestId('aide-page')).toBeInTheDocument();
  });

  it('/users 渲染用户管理', () => {
    renderAt('/users');
    expect(screen.getByTestId('users-page')).toBeInTheDocument();
  });
});
