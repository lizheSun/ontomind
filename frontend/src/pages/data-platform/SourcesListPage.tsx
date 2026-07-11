import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Space, Tag, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  PageHeader,
  StatCard,
  DataTable,
  TagPill,
  DangerConfirm,
} from '../../components/common';
import useDataPlatformStore from '../../stores/dataPlatformStore';
import { dataPlatformService } from '../../services/dataPlatform.service';
import type { DpDataSource, DpStatus } from '../../types/dataPlatform';
import SourceFormDrawer from './components/SourceFormDrawer';

const STATUS_STYLE: Record<
  DpStatus,
  { label: string; bg: string; fg: string }
> = {
  active: {
    label: '已激活',
    bg: 'rgba(52,211,153,0.14)',
    fg: '#34d399',
  },
  inactive: {
    label: '未激活',
    bg: 'rgba(100,116,139,0.14)',
    fg: '#94a3b8',
  },
  error: {
    label: '异常',
    bg: 'rgba(251,113,133,0.14)',
    fg: '#fb7185',
  },
};

const TYPE_COLOR_MAP: Record<
  string,
  'blue' | 'purple' | 'cyan' | 'emerald' | 'amber' | 'rose'
> = {
  mysql: 'blue',
  postgresql: 'purple',
  sqlite: 'cyan',
};

function formatDateTime(v: string | null | undefined): string {
  if (!v) return '-';
  const d = dayjs(v);
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : '-';
}

export default function SourcesListPage() {
  const navigate = useNavigate();
  const sources = useDataPlatformStore((s) => s.sources);
  const loading = useDataPlatformStore((s) => s.loading);
  const fetchSources = useDataPlatformStore((s) => s.fetchSources);
  const deleteSource = useDataPlatformStore((s) => s.deleteSource);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<'create' | 'edit'>('create');
  const [editing, setEditing] = useState<DpDataSource | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);

  useEffect(() => {
    if (sources.length === 0 && !loading) {
      void fetchSources();
    }
    // Only run on mount — subsequent fetches are user-driven.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreate = useCallback(() => {
    setDrawerMode('create');
    setEditing(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((row: DpDataSource) => {
    setDrawerMode('edit');
    setEditing(row);
    setDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    setEditing(null);
  }, []);

  const handleTest = useCallback(async (row: DpDataSource) => {
    setTestingId(row.id);
    try {
      const res = await dataPlatformService.testConnection(row.id);
      if (res.ok) {
        const versionText = res.serverVersion ?? '未知版本';
        message.success(
          `连接成功 · ${versionText} · ${res.elapsedMs}ms`,
        );
      } else {
        message.error(res.error ?? '连接失败');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '连接失败';
      message.error(msg);
    } finally {
      setTestingId(null);
    }
  }, []);

  const handleDelete = useCallback(
    (row: DpDataSource) => {
      DangerConfirm({
        title: `确认删除数据源 ${row.name}？`,
        content: '所有关联查询历史/保存查询将级联删除。',
        onOk: async () => {
          try {
            await deleteSource(row.id);
            message.success('已删除');
          } catch (err) {
            const msg = err instanceof Error ? err.message : '删除失败';
            message.error(msg);
          }
        },
      });
    },
    [deleteSource],
  );

  const columns = useMemo<ColumnsType<DpDataSource>>(() => {
    return [
      {
        title: '名称',
        dataIndex: 'name',
        key: 'name',
        render: (name: string, row) => {
          const inactive = row.status === 'inactive';
          const errored = row.status === 'error';
          const dotColor = errored
            ? 'var(--kb-tag-rose, #fb7185)'
            : inactive
              ? 'var(--kb-tag-slate, #94a3b8)'
              : 'transparent';
          return (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                color: 'var(--text-primary, #e8eef5)',
                fontWeight: 500,
              }}
            >
              {row.status !== 'active' && (
                <span
                  aria-hidden
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: dotColor,
                    display: 'inline-block',
                  }}
                />
              )}
              {name}
            </span>
          );
        },
      },
      {
        title: '类型',
        dataIndex: 'sourceType',
        key: 'sourceType',
        width: 130,
        render: (t: string) => {
          const key = (t ?? '').toLowerCase();
          const color = TYPE_COLOR_MAP[key] ?? 'blue';
          return <TagPill color={color}>{t?.toUpperCase() ?? '-'}</TagPill>;
        },
      },
      {
        title: '数据库',
        dataIndex: 'database',
        key: 'database',
        ellipsis: true,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 100,
        render: (s: DpStatus) => {
          const meta = STATUS_STYLE[s] ?? STATUS_STYLE.inactive;
          return (
            <Tag
              style={{
                borderRadius: 6,
                background: meta.bg,
                color: meta.fg,
                border: 'none',
              }}
            >
              {meta.label}
            </Tag>
          );
        },
      },
      {
        title: '拥有者',
        dataIndex: 'ownerUserId',
        key: 'ownerUserId',
        width: 100,
        render: (v: number) => `#${v}`,
      },
      {
        title: '更新时间',
        dataIndex: 'updatedAt',
        key: 'updatedAt',
        width: 170,
        render: (v: string | null) => (
          <span style={{ color: 'var(--text-secondary, #8895b4)' }}>
            {formatDateTime(v)}
          </span>
        ),
      },
      {
        title: '操作',
        key: 'actions',
        width: 280,
        render: (_: unknown, row: DpDataSource) => (
          <Space size={4} wrap>
            <Button
              type="link"
              size="small"
              loading={testingId === row.id}
              onClick={() => handleTest(row)}
            >
              测试连接
            </Button>
            <Button
              type="link"
              size="small"
              onClick={() => navigate(`/data-platform/sources/${row.id}`)}
            >
              详情
            </Button>
            <Button type="link" size="small" onClick={() => openEdit(row)}>
              编辑
            </Button>
            <Button
              type="link"
              size="small"
              danger
              onClick={() => handleDelete(row)}
            >
              删除
            </Button>
          </Space>
        ),
      },
    ];
  }, [handleDelete, handleTest, navigate, openEdit, testingId]);

  const activeCount = useMemo(
    () => sources.filter((s) => s.status === 'active').length,
    [sources],
  );

  return (
    <div>
      <PageHeader
        title="数据平台 · 数据源"
        subtitle="连接、探查、并对话你的数据资产"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={openCreate}
          >
            新建数据源
          </Button>
        }
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: 16,
          marginBottom: 20,
        }}
      >
        <StatCard
          icon={<DatabaseOutlined />}
          label="数据源总数"
          value={sources.length}
          accent="blue"
        />
        <StatCard
          icon={<ApiOutlined />}
          label="已激活"
          value={activeCount}
          accent="emerald"
        />
        <StatCard
          icon={<ThunderboltOutlined />}
          label="最近 7 天查询数"
          value={0}
          accent="purple"
        />
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          marginBottom: 12,
        }}
      >
        <Button
          icon={<ReloadOutlined />}
          onClick={() => fetchSources()}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      <DataTable<DpDataSource>
        rowKey="id"
        columns={columns}
        dataSource={sources}
        loading={loading}
        emptyTitle="暂无数据源"
        emptyDescription="点击右上角『新建数据源』开始接入"
        emptyAction={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建数据源
          </Button>
        }
      />

      <SourceFormDrawer
        open={drawerOpen}
        mode={drawerMode}
        initial={editing}
        onClose={closeDrawer}
      />
    </div>
  );
}
