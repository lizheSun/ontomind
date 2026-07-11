import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, message, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DataTable, TagPill, DangerConfirm } from '../../components/common';
import KbLibraryLayout from './KbLibraryLayout';
import EntryFormDrawer, {
  type EntryFormValues,
} from './components/EntryFormDrawer';
import { knowledgeBaseService } from '../../services/knowledgeBase.service';
import { useKnowledgeBaseStore } from '../../stores/knowledgeBaseStore';
import type {
  KbDataAsset,
  KbDataAssetCreate,
  KbDataAssetUpdate,
} from '../../types/knowledgeBase';

export default function DataAssetsPage() {
  const libraries = useKnowledgeBaseStore((s) => s.libraries);
  const libraryId = useMemo(
    () => libraries.find((l) => l.code === 'data_asset')?.id,
    [libraries],
  );

  const [entries, setEntries] = useState<KbDataAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQ, setSearchQ] = useState('');
  const [searchIds, setSearchIds] = useState<number[] | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<KbDataAsset | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const list = await knowledgeBaseService.listDataAssets();
      setEntries(list);
    } catch {
      message.error('加载数据资产列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!searchQ.trim()) {
      setSearchIds(null);
      return;
    }
    searchTimer.current = setTimeout(async () => {
      try {
        const grouped = await knowledgeBaseService.search(
          searchQ.trim(),
          'data_asset',
        );
        setSearchIds(grouped.dataAsset.map((r) => r.id));
      } catch {
        setSearchIds([]);
      }
    }, 300);
    return () => {
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, [searchQ]);

  const visible = useMemo(() => {
    if (searchIds === null) return entries;
    const set = new Set(searchIds);
    return entries.filter((e) => set.has(e.id));
  }, [entries, searchIds]);

  const handleCreate = () => {
    setEditing(null);
    setDrawerOpen(true);
  };

  const handleEdit = (row: KbDataAsset) => {
    setEditing(row);
    setDrawerOpen(true);
  };

  const handleDelete = (row: KbDataAsset) => {
    DangerConfirm({
      title: `确认删除“${row.titleZh}”？`,
      content: '此操作不可撤销',
      onOk: async () => {
        try {
          await knowledgeBaseService.deleteDataAsset(row.id);
          message.success('已删除');
          setEntries((cur) => cur.filter((e) => e.id !== row.id));
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const handleSubmit = async (values: EntryFormValues) => {
    if (!libraryId && !editing) {
      message.error('知识库尚未加载，请稍后重试');
      return;
    }
    setSubmitting(true);
    try {
      const tagsVal = Array.isArray(values.tags) ? values.tags : undefined;
      if (editing) {
        const patch: KbDataAssetUpdate = {
          title_zh: values.titleZh as string | undefined,
          title_en: (values.titleEn as string | undefined) ?? null,
          domain: (values.domain as string | undefined) ?? null,
          description_md: (values.descriptionMd as string | undefined) ?? null,
          tags: tagsVal ?? null,
        };
        const updated = await knowledgeBaseService.updateDataAsset(editing.id, patch);
        setEntries((cur) => cur.map((e) => (e.id === updated.id ? updated : e)));
        message.success('已更新');
      } else {
        const payload: KbDataAssetCreate = {
          library_id: libraryId as number,
          title_zh: (values.titleZh as string) ?? '',
          title_en: (values.titleEn as string | undefined) ?? null,
          domain: (values.domain as string | undefined) ?? null,
          description_md: (values.descriptionMd as string | undefined) ?? null,
          tags: tagsVal ?? null,
        };
        const created = await knowledgeBaseService.createDataAsset(payload);
        setEntries((cur) => [created, ...cur]);
        message.success('已创建');
      }
      setDrawerOpen(false);
      setEditing(null);
    } catch {
      message.error('保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ColumnsType<KbDataAsset> = [
    { title: '中文名', dataIndex: 'titleZh', key: 'titleZh' },
    {
      title: '英文名',
      dataIndex: 'titleEn',
      key: 'titleEn',
      render: (v: string | null) => v || '-',
    },
    {
      title: '业务域',
      dataIndex: 'domain',
      key: 'domain',
      render: (v: string | null) => v || '-',
    },
    { title: '拥有者', dataIndex: 'ownerUserId', key: 'ownerUserId', width: 90 },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[] | null) =>
        tags && tags.length > 0 ? (
          <Space size={4} wrap>
            {tags.map((t) => (
              <TagPill key={t} color="blue">
                {t}
              </TagPill>
            ))}
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 170,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_: unknown, row: KbDataAsset) => (
        <Space size={4}>
          <Button type="link" size="small" onClick={() => handleEdit(row)}>
            编辑
          </Button>
          <Button type="link" size="small" danger onClick={() => handleDelete(row)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const editingInitial: EntryFormValues | undefined = editing
    ? {
        titleZh: editing.titleZh,
        titleEn: editing.titleEn ?? undefined,
        domain: editing.domain ?? undefined,
        descriptionMd: editing.descriptionMd ?? undefined,
        tags: editing.tags ?? [],
      }
    : undefined;

  return (
    <KbLibraryLayout
      libraryCode="data_asset"
      title="数据资产"
      subtitle="按业务域整理的数据资产目录"
      onSearchChange={setSearchQ}
      onCreate={handleCreate}
    >
      <DataTable<KbDataAsset>
        rowKey="id"
        columns={columns}
        dataSource={visible}
        loading={loading}
        emptyTitle="暂无数据资产"
        emptyDescription="点击右上角“新建”创建第一条数据资产"
      />
      <EntryFormDrawer
        open={drawerOpen}
        schemaKey="dataAsset"
        title={editing ? '编辑数据资产' : '新建数据资产'}
        initialValues={editingInitial}
        submitting={submitting}
        onClose={() => {
          setDrawerOpen(false);
          setEditing(null);
        }}
        onSubmit={handleSubmit}
      />
    </KbLibraryLayout>
  );
}
