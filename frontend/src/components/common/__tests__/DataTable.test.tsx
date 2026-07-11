import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeAll } from 'vitest';
import { DataTable } from '../DataTable';

interface Row {
  id: number;
  name: string;
}

const columns = [
  { title: '姓名', dataIndex: 'name', key: 'name' },
];

beforeAll(() => {
  // jsdom lacks ResizeObserver — AntD Table's rc-resize-observer needs it.
  if (!('ResizeObserver' in globalThis)) {
    class ResizeObserverStub {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    }
    (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
      ResizeObserverStub;
  }
});

describe('DataTable', () => {
  it('renders EmptyState when dataSource is empty and not loading', () => {
    render(<DataTable<Row> rowKey="id" columns={columns} dataSource={[]} />);
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('renders AntD Table when dataSource has rows', () => {
    const rows: Row[] = [
      { id: 1, name: 'alice' },
      { id: 2, name: 'bob' },
    ];
    render(<DataTable<Row> rowKey="id" columns={columns} dataSource={rows} />);
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    // Empty state should NOT be present now.
    expect(screen.queryByText('暂无数据')).not.toBeInTheDocument();
  });

  it('supports custom emptyTitle', () => {
    render(
      <DataTable<Row>
        rowKey="id"
        columns={columns}
        dataSource={[]}
        emptyTitle="尚无数据源"
        emptyDescription="点击『新建数据源』开始"
      />,
    );
    expect(screen.getByText('尚无数据源')).toBeInTheDocument();
    expect(screen.getByText('点击『新建数据源』开始')).toBeInTheDocument();
  });
});
