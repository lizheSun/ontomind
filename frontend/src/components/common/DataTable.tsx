import { Table } from 'antd';
import type { TableProps } from 'antd';
import type { JSX, ReactNode } from 'react';
import { GlassPanel } from './GlassPanel';
import { EmptyState } from './EmptyState';

export interface DataTableProps<T> extends Omit<TableProps<T>, 'rowKey'> {
  /** Row key is REQUIRED — antd's default (index) causes re-render key collisions. */
  rowKey: TableProps<T>['rowKey'];
  /** Custom empty state; falls back to `<EmptyState>` when omitted. */
  emptyTitle?: ReactNode;
  emptyDescription?: ReactNode;
  emptyAction?: ReactNode;
  /** Wrap in GlassPanel (true by default). */
  panelWrapped?: boolean;
}

export function DataTable<T extends object>({
  rowKey,
  dataSource,
  loading,
  emptyTitle,
  emptyDescription,
  emptyAction,
  panelWrapped = true,
  pagination,
  ...rest
}: DataTableProps<T>): JSX.Element {
  const data = dataSource ?? [];
  const showCustomEmpty = data.length === 0 && !loading;

  const body = showCustomEmpty ? (
    <EmptyState
      title={emptyTitle ?? '暂无数据'}
      description={emptyDescription}
      action={emptyAction}
    />
  ) : (
    <Table<T>
      rowKey={rowKey}
      dataSource={data}
      loading={loading}
      pagination={
        pagination === false
          ? false
          : {
              size: 'small',
              showSizeChanger: true,
              pageSizeOptions: [10, 20, 50, 100],
              defaultPageSize: 20,
              ...(typeof pagination === 'object' ? pagination : {}),
            }
      }
      sticky
      scroll={rest.scroll ?? { x: 'max-content' }}
      {...rest}
    />
  );

  if (!panelWrapped) return body;
  return <GlassPanel padded={false} style={{ overflow: 'hidden' }}>{body}</GlassPanel>;
}
