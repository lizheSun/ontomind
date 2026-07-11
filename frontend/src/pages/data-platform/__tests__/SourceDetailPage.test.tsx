import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import SourceDetailPage from '../SourceDetailPage';

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

vi.mock('../../../services/dataPlatform.service', () => ({
  dataPlatformService: {
    getSource: vi.fn().mockResolvedValue({
      id: 1,
      name: 'test-src',
      sourceType: 'sqlite',
      dialect: 'sqlite',
      database: ':memory:',
      charset: 'utf8mb4',
      status: 'active',
      readOnlyFlag: true,
      hasPassword: false,
      ownerUserId: 1,
      createdByUserId: 1,
      host: null,
      port: null,
      username: null,
      defaultSchema: null,
      description: null,
      extraParams: null,
      createdAt: null,
      updatedAt: null,
    }),
    describeSchema: vi.fn().mockResolvedValue({ databases: [] }),
    listSessions: vi.fn().mockResolvedValue([]),
    listHistory: vi.fn().mockResolvedValue([]),
    listSaved: vi.fn().mockResolvedValue([]),
    listSavedQueries: vi.fn().mockResolvedValue([]),
    listChatSessions: vi.fn().mockResolvedValue([]),
    listQueryHistory: vi.fn().mockResolvedValue([]),
    execute: vi.fn(),
    buildStreamUrl: vi.fn().mockReturnValue('http://x'),
  },
}));

vi.mock('../../../services/knowledgeBase.service', () => ({
  knowledgeBaseService: { search: vi.fn(), listLibraries: vi.fn() },
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/data-platform/sources/1']}>
      <Routes>
        <Route path="/data-platform/sources/:sid" element={<SourceDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SourceDetailPage', () => {
  it('renders the source name in header after loading', async () => {
    renderPage();
    const matches = await screen.findAllByText('test-src', {}, { timeout: 3000 });
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('renders all 4 tab labels', async () => {
    renderPage();
    expect(await screen.findByText('SQL 编辑器', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('AI 对话')).toBeInTheDocument();
    expect(screen.getByText('执行历史')).toBeInTheDocument();
    expect(screen.getByText('保存的查询')).toBeInTheDocument();
  });
});
