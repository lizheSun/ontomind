import { useMemo } from 'react';
import { Tree, Empty, Typography, Space } from 'antd';
import type { TreeDataNode } from 'antd';
import {
  DatabaseOutlined,
  TableOutlined,
  FieldNumberOutlined,
} from '@ant-design/icons';
import { GlassPanel } from './GlassPanel';

const { Text } = Typography;

export interface SchemaColumn {
  name: string;
  type?: string;
}

export interface SchemaTable {
  name: string;
  columns: SchemaColumn[];
}

export interface SchemaDatabase {
  name: string;
  tables: SchemaTable[];
}

export interface SchemaTreeData {
  databases: SchemaDatabase[];
}

export interface SchemaTreeProps {
  data?: SchemaTreeData;
  loading?: boolean;
  onTableClick?: (dbName: string, table: SchemaTable) => void;
  onColumnClick?: (dbName: string, table: SchemaTable, column: SchemaColumn) => void;
  height?: number;
  className?: string;
  'data-testid'?: string;
}

function buildKeys(dbName: string, tableName?: string, columnName?: string): string {
  if (columnName && tableName) return `col::${dbName}::${tableName}::${columnName}`;
  if (tableName) return `tbl::${dbName}::${tableName}`;
  return `db::${dbName}`;
}

export const SchemaTree: React.FC<SchemaTreeProps> = ({
  data,
  loading,
  onTableClick,
  onColumnClick,
  height = 480,
  className,
  'data-testid': testId,
}) => {
  const treeData = useMemo<TreeDataNode[]>(() => {
    if (!data) return [];
    return data.databases.map((db) => ({
      key: buildKeys(db.name),
      title: (
        <Space size={8}>
          <Text style={{ fontWeight: 600, color: 'var(--text-primary, #e8eef5)' }}>
            {db.name}
          </Text>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary, #506080)' }}>
            {db.tables.length} 表
          </Text>
        </Space>
      ),
      icon: <DatabaseOutlined style={{ color: 'var(--accent, #3b82f6)' }} />,
      children: db.tables.map((tbl) => ({
        key: buildKeys(db.name, tbl.name),
        title: (
          <Space
            size={8}
            onClick={(e) => {
              e.stopPropagation();
              onTableClick?.(db.name, tbl);
            }}
            style={{ cursor: onTableClick ? 'pointer' : undefined }}
          >
            <Text style={{ color: 'var(--text-primary, #e8eef5)' }}>{tbl.name}</Text>
            <Text style={{ fontSize: 11, color: 'var(--text-tertiary, #506080)' }}>
              {tbl.columns.length} 列
            </Text>
          </Space>
        ),
        icon: <TableOutlined style={{ color: 'var(--accent-purple, #a78bfa)' }} />,
        children: tbl.columns.map((col) => ({
          key: buildKeys(db.name, tbl.name, col.name),
          title: (
            <Space
              size={6}
              onClick={(e) => {
                e.stopPropagation();
                onColumnClick?.(db.name, tbl, col);
              }}
              style={{ cursor: onColumnClick ? 'pointer' : undefined }}
            >
              <Text style={{ color: 'var(--text-primary, #e8eef5)' }}>{col.name}</Text>
              {col.type && (
                <Text style={{ fontSize: 11, color: 'var(--text-tertiary, #506080)' }}>
                  {col.type}
                </Text>
              )}
            </Space>
          ),
          icon: <FieldNumberOutlined style={{ color: 'var(--accent-cyan, #22d3ee)' }} />,
          isLeaf: true,
        })),
      })),
    }));
  }, [data, onColumnClick, onTableClick]);

  return (
    <GlassPanel padded={false} className={className}>
      <div
        data-testid={testId ?? 'schema-tree'}
        style={{ padding: 12, height, overflow: 'auto' }}
      >
        {loading ? (
          <Empty description="加载中…" />
        ) : treeData.length === 0 ? (
          <Empty description="未连接数据源或无可读元数据" />
        ) : (
          <Tree
            treeData={treeData}
            showIcon
            blockNode
            defaultExpandAll={false}
            style={{ background: 'transparent' }}
          />
        )}
      </div>
    </GlassPanel>
  );
};
