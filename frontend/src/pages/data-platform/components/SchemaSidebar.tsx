import { useEffect, useMemo } from 'react';
import { useDataPlatformStore } from '../../../stores/dataPlatformStore';
import { SchemaTree } from '../../../components/common';
import type { SchemaTreeData } from '../../../components/common';

interface Props {
  sourceId: number;
  onColumnClick?: (name: string) => void;
  height?: number;
}

export default function SchemaSidebar({ sourceId, onColumnClick, height }: Props) {
  const schemaCache = useDataPlatformStore((s) => s.schemaCache);
  const fetchSchema = useDataPlatformStore((s) => s.fetchSchema);

  useEffect(() => {
    fetchSchema(sourceId).catch(() => {});
  }, [sourceId, fetchSchema]);

  const schema = schemaCache[sourceId];
  const treeData = useMemo<SchemaTreeData | undefined>(
    () =>
      schema
        ? {
            databases: schema.databases.map((db) => ({
              name: db.name,
              tables: db.tables.map((t) => ({
                name: t.name,
                columns: t.columns.map((c) => ({ name: c.name, type: c.type })),
              })),
            })),
          }
        : undefined,
    [schema],
  );

  return (
    <SchemaTree
      data={treeData}
      loading={!schema}
      onColumnClick={(_db, _tbl, col) => onColumnClick?.(col.name)}
      height={height ?? Math.max(320, (typeof window !== 'undefined' ? window.innerHeight : 800) - 260)}
    />
  );
}
