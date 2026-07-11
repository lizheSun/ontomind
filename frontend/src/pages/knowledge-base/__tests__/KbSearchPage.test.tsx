import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import KbSearchPage from '../KbSearchPage';

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

vi.mock('../../../services/knowledgeBase.service', () => ({
  knowledgeBaseService: {
    search: vi.fn().mockResolvedValue({
      dataAsset: [
        {
          libraryCode: 'data_asset',
          id: 1,
          title: '订单主表',
          snippet: '核心订单表',
          score: 1,
        },
      ],
      codeRepo: [],
      document: [],
      experience: [],
    }),
  },
}));

describe('KbSearchPage', () => {
  it('renders pre-search empty state when no query', () => {
    render(
      <MemoryRouter>
        <KbSearchPage />
      </MemoryRouter>,
    );
    expect(screen.getByText(/输入关键词开始搜索/)).toBeInTheDocument();
  });

  it('triggers search when URL has q= and shows result title', async () => {
    render(
      <MemoryRouter initialEntries={['/knowledge-base/search?q=%E8%AE%A2%E5%8D%95']}>
        <KbSearchPage />
      </MemoryRouter>,
    );
    await waitFor(
      () => {
        expect(screen.getByText('主表')).toBeInTheDocument();
        expect(screen.getAllByText('订单').length).toBeGreaterThan(0);
      },
      { timeout: 3000 },
    );
  });

  it('renders TagPill filter chips including 全部 + 4 library names', () => {
    render(
      <MemoryRouter>
        <KbSearchPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('全部')).toBeInTheDocument();
    expect(screen.getByText('数据资产')).toBeInTheDocument();
    expect(screen.getByText('代码库')).toBeInTheDocument();
    expect(screen.getByText('文档库')).toBeInTheDocument();
    expect(screen.getByText('业务经验')).toBeInTheDocument();
  });
});
