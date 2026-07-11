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
  KbExperience,
  KbExperienceCreate,
  KbExperienceUpdate,
} from '../../types/knowledgeBase';

export default function ExperiencesPage() {
  const libraries = useKnowledgeBaseStore((s) => s.libraries);
  const libraryId = useMemo(
    () => libraries.find((l) => l.code === 'experience')?.id,
    [libraries],
  );

  const [entries, setEntries] = useState<KbExperience[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQ, setSearchQ] = useState('');
  const [searchIds, setSearchIds] = useState<number[] | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<KbExperience | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const list = await knowledgeBaseService.listExperiences();
      setEntries(list);
    } catch {
      message.error('加载业务经验列表失败');
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
          'experience',
        );
        setSearchIds(grouped.experience.map((r) => r.id));
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

  const handleEdit = (row: KbExperience) => {
    setEditing(row);
    setDrawerOpen(true);
  };

  const handleDelete = (row: KbExperience) => {
    DangerConfirm({
      title: `确认删除“${row.titleZh}”？`,
      content: '此操作不可撤销',
      onOk: async () => {
        try {
          await knowledgeBaseService.deleteExperience(row.id);
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
        const patch: KbExperienceUpdate = {
          title_zh: values.titleZh as string | undefined,
          scenario: (values.scenario as string | undefined) ?? null,
          content_md: values.contentMd as string | undefined,
          outcome: (values.outcome as string | undefined) ?? null,
          tags: tagsVal ?? null,
        };
        const updated = await knowledgeBaseService.updateExperience(
          editing.id,
          patch,
        );
        setEntries((cur) => cur.map((e) => (e.id === updated.id ? updated : e)));
        message.success('已更新');
      } else {
        const payload: KbExperienceCreate = {
          library_id: libraryId as number,
          title_zh: (values.titleZh as string) ?? '',
          scenario: (values.scenario as string | undefined) ?? null,
          content_md: (values.contentMd as string) ?? '',
          outcome: (values.outcome as string | undefined) ?? null,
          tags: tagsVal ?? null,
        };
        const created = await knowledgeBaseService.createExperience(payload);
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

  const columns: ColumnsType<KbExperience> = [
    { title: '标题', dataIndex: 'titleZh', key: 'titleZh' },
    {
      title: '场景',
      dataIndex: 'scenario',
      key: 'scenario',
      render: (v: string | null) => v || '-',
    },
    {
      title: '结果',
      dataIndex: 'outcome',
      key: 'outcome',
      render: (v: string | null) => v || '-',
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[] | null) =>
        tags && tags.length > 0 ? (
          <Space size={4} wrap>
            {tags.map((t) => (
              <TagPill key={t} color="emerald">
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
      render: (_: unknown, row: KbExperience) => (
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
        scenario: editing.scenario ?? undefined,
        contentMd: editing.contentMd,
        outcome: editing.outcome ?? undefined,
        tags: editing.tags ?? [],
      }
    : undefined;

  return (
    <KbLibraryLayout
      libraryCode="experience"
      title="业务经验库"
      subtitle="沉淀的业务复盘、方法与经验"
      onSearchChange={setSearchQ}
      onCreate={handleCreate}
    >
      <DataTable<KbExperience>
        rowKey="id"
        columns={columns}
        dataSource={visible}
        loading={loading}
        emptyTitle="暂无业务经验"
        emptyDescription="点击右上角“新建”记录第一条业务经验"
      />
      <EntryFormDrawer
        open={drawerOpen}
        schemaKey="experience"
        title={editing ? '编辑业务经验' : '新建业务经验'}
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
