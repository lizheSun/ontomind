import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { SchemaTree } from '../SchemaTree';

beforeAll(() => {
  // jsdom lacks ResizeObserver; AntD Tree uses rc-virtual-list which requires it.
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

const data = {
  databases: [
    {
      name: 'ontomind',
      tables: [
        { name: 'users', columns: [{ name: 'id', type: 'INTEGER' }, { name: 'name', type: 'TEXT' }] },
        { name: 'orders', columns: [{ name: 'id', type: 'INTEGER' }] },
      ],
    },
  ],
};

describe('SchemaTree', () => {
  it('renders empty state when no data', () => {
    render(<SchemaTree data={undefined} />);
    expect(screen.getByText(/未连接|无可读元数据/)).toBeInTheDocument();
  });

  it('renders loading state', () => {
    render(<SchemaTree data={undefined} loading={true} />);
    expect(screen.getByText(/加载中/)).toBeInTheDocument();
  });

  it('renders database node when data provided', () => {
    render(<SchemaTree data={data} />);
    expect(screen.getByText('ontomind')).toBeInTheDocument();
    // Root-level table count label rendered as "N 表"
    expect(screen.getByText(/2 表/)).toBeInTheDocument();
  });

  it('mounts without crashing when onColumnClick handler is provided', () => {
    const onColumnClick = vi.fn();
    render(<SchemaTree data={data} onColumnClick={onColumnClick} />);
    expect(screen.getByText('ontomind')).toBeInTheDocument();
  });
});
