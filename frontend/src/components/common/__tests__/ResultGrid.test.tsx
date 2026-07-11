import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ResultGrid } from '../ResultGrid';

const cols = ['id', 'name', 'created_at'];

function makeRows(n: number): unknown[][] {
  return Array.from({ length: n }, (_, i) => [i + 1, `alice-${i}`, `2025-01-${(i % 28) + 1}`]);
}

describe('ResultGrid virtualization', () => {
  it('renders header + counters when rows present', () => {
    render(<ResultGrid columns={cols} rows={makeRows(500)} elapsedMs={42} />);
    expect(screen.getByText(/500 行/)).toBeInTheDocument();
    expect(screen.getByText(/42 ms/)).toBeInTheDocument();
  });

  it('only renders a small window of rows for 500-row input (virtualization)', () => {
    render(<ResultGrid columns={cols} rows={makeRows(500)} height={320} />);
    const rowNodes = screen.queryAllByTestId('rg-row');
    // jsdom has no layout → useVirtualizer typically emits a very small window.
    // We assert well under the total to prove virtualization is engaged.
    expect(rowNodes.length).toBeLessThan(50);
  });

  it('shows EmptyState when rows are empty', () => {
    render(<ResultGrid columns={cols} rows={[]} />);
    expect(screen.getByText(/暂无查询结果/)).toBeInTheDocument();
  });
});
