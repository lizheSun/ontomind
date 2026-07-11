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
  KbCodeRepo,
  KbCodeRepoCreate,
  KbCodeRepoUpdate,
} from '../../types/knowledgeBase';

export default function CodeReposPage() {
  const libraries = useKnowledgeBaseStore((s) => s.libraries);
  const libraryId = useMemo(
    () => libraries.find((l) => l.code === 'code_repo')?.id,
    [libraries],
  );

  const [entries, setEntries] = useState<KbCodeRepo[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQ, setSearchQ] = useState('');
  const [searchIds, setSearchIds] = useState<number[] | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<KbCodeRepo | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const list = await knowledgeBaseService.listCodeRepos();
      setEntries(list);
    } catch {
      message.error('加载代码库列表失败');
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
          'code_repo',
        );
        setSearchIds(grouped.codeRepo.map((r) => r.id));
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

  const handleEdit = (row: KbCodeRepo) => {
    setEditing(row);
    setDrawerOpen(true);
  };

  const handleDelete = (row: KbCodeRepo) => {
    DangerConfirm({
      title: `确认删除“${row.titleZh}”？`,
      content: '此操作不可撤销',
      onOk: async () => {
        try {
          await knowledgeBaseService.deleteCodeRepo(row.id);
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
        const patch: KbCodeRepoUpdate = {
          title_zh: values.titleZh as string | undefined,
          repo_url: values.repoUrl as string | undefined,
          branch: (values.branch as string | undefined) || undefined,
          language: (values.language as string | undefined) ?? null,
          description_md: (values.descriptionMd as string | undefined) ?? null,
          tags: tagsVal ?? null,
        };
        const updated = await knowledgeBaseService.updateCodeRepo(editing.id, patch);
        setEntries((cur) => cur.map((e) => (e.id === updated.id ? updated : e)));
        message.success('已更新');
      } else {
        const payload: KbCodeRepoCreate = {
          library_id: libraryId as number,
          title_zh: (values.titleZh as string) ?? '',
          repo_url: (values.repoUrl as string) ?? '',
          branch: (values.branch as string) || undefined,
          language: (values.language as string | undefined) ?? null,
          description_md: (values.descriptionMd as string | undefined) ?? null,
          tags: tagsVal ?? null,
        };
        const created = await knowledgeBaseService.createCodeRepo(payload);
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

  const columns: ColumnsType<KbCodeRepo> = [
    { title: '名称', dataIndex: 'titleZh', key: 'titleZh' },
    {
      title: '仓库 URL',
      dataIndex: 'repoUrl',
      key: 'repoUrl',
      render: (v: string) => (
        <a href={v} target="_blank" rel="noreferrer">
          {v}
        </a>
      ),
    },
    { title: '分支', dataIndex: 'branch', key: 'branch', width: 100 },
    {
      title: '语言',
      dataIndex: 'language',
      key: 'language',
      width: 100,
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
              <TagPill key={t} color="purple">
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
      render: (_: unknown, row: KbCodeRepo) => (
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
        repoUrl: editing.repoUrl,
        branch: editing.branch,
        language: editing.language ?? undefined,
        descriptionMd: editing.descriptionMd ?? undefined,
        tags: editing.tags ?? [],
      }
    : undefined;

  return (
    <KbLibraryLayout
      libraryCode="code_repo"
      title="代码库"
      subtitle="内外部代码仓库索引"
      onSearchChange={setSearchQ}
      onCreate={handleCreate}
    >
      <DataTable<KbCodeRepo>
        rowKey="id"
        columns={columns}
        dataSource={visible}
        loading={loading}
        emptyTitle="暂无代码库"
        emptyDescription="点击右上角“新建”添加第一个代码仓库"
      />
      <EntryFormDrawer
        open={drawerOpen}
        schemaKey="codeRepo"
        title={editing ? '编辑代码库' : '新建代码库'}
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
