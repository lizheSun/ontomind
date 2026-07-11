/**
 * Vitest smoke tests for AgentLooperListPage (Wave 9 W2 T38).
 *
 * These tests mock agentLooper.service and verify:
 *   1. Empty-state renders the discover / create actions.
 *   2. list() rows show up with model + strategy columns.
 *   3. Type + status pills render for each row.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import AgentLooperListPage from '../AgentLooperListPage';

beforeAll(() => {
  if (typeof globalThis.ResizeObserver === 'undefined') {
    class RO {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).ResizeObserver = RO;
  }
});

// ---- mocks --------------------------------------------------------

const listMock = vi.fn();
const discoverMock = vi.fn();
const deleteMock = vi.fn();

vi.mock('../../../services/agentLooper.service', () => ({
  agentLooperService: {
    list: (...args: unknown[]) => listMock(...args),
    discover: (...args: unknown[]) => discoverMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
  },
}));

// ---- tests --------------------------------------------------------

describe('AgentLooperListPage', () => {
  it('renders empty state with discover + create actions when list is empty', async () => {
    listMock.mockResolvedValueOnce([]);
    render(
      <MemoryRouter>
        <AgentLooperListPage />
      </MemoryRouter>,
    );

    // Header always visible
    expect(screen.getByText('Agent Looper')).toBeInTheDocument();
    expect(screen.getByText('AI Agent 定制与生命周期管理')).toBeInTheDocument();

    // Wait for empty state to appear
    await waitFor(
      () => {
        expect(screen.getByText('暂无 Agent 配置')).toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    // Buttons for discover + create should render (in header + empty state)
    expect(screen.getAllByText('发现本地 Agent').length).toBeGreaterThan(0);
    expect(screen.getAllByText('新建 Agent').length).toBeGreaterThan(0);
  });

  it('renders list rows with name, model and strategy labels', async () => {
    listMock.mockResolvedValueOnce([
      {
        id: 1,
        name: 'planner',
        type: 'custom_looper',
        description: '规划器',
        is_active: true,
        is_published: false,
        model: 'gpt-4o',
        loop_strategy: 'react',
        updated_at: '2026-07-01T00:00:00Z',
      },
      {
        id: 2,
        name: 'reviewer',
        type: 'opencode_native',
        description: null,
        is_active: false,
        is_published: true,
        model: 'claude-3-5-sonnet',
        loop_strategy: 'plan_execute',
        updated_at: '2026-07-02T00:00:00Z',
      },
    ]);

    render(
      <MemoryRouter>
        <AgentLooperListPage />
      </MemoryRouter>,
    );

    await waitFor(
      () => {
        expect(screen.getByText('planner')).toBeInTheDocument();
        expect(screen.getByText('reviewer')).toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    expect(screen.getByText('gpt-4o')).toBeInTheDocument();
    expect(screen.getByText('claude-3-5-sonnet')).toBeInTheDocument();
    expect(screen.getByText('ReAct')).toBeInTheDocument();
    expect(screen.getByText('Plan-Execute')).toBeInTheDocument();
  });

  it('renders type pills and published/active tags for each row', async () => {
    listMock.mockResolvedValueOnce([
      {
        id: 3,
        name: 'coder',
        type: 'custom_looper',
        description: null,
        is_active: true,
        is_published: true,
        model: 'gpt-4o',
        loop_strategy: 'react',
        updated_at: null,
      },
    ]);

    render(
      <MemoryRouter>
        <AgentLooperListPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText('coder')).toBeInTheDocument(), {
      timeout: 3000,
    });

    // Type label (from TYPE_LABELS[custom_looper])
    expect(screen.getByText('自定义 Loop')).toBeInTheDocument();
    // Active tag
    expect(screen.getByText('启用')).toBeInTheDocument();
    // Published tag (also appears as column header — expect at least 2)
    expect(screen.getAllByText('已发布').length).toBeGreaterThanOrEqual(2);
  });
});
