import { useEffect, useState } from 'react';
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Tooltip,
  Typography,
  message,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  StarFilled,
  StarOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { DataTable } from '../../../components/common';
import type { DpSavedQuery } from '../../../types/dataPlatform';
import { dataPlatformService } from '../../../services/dataPlatform.service';

const { Text } = Typography;

interface Props {
  sourceId: number;
  onRun: (sql: string) => void;
}

interface FormValues {
  name: string;
  sqlText: string;
  isFavorite: boolean;
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

export default function SavedQueriesTab({ sourceId, onRun }: Props) {
  const [rows, setRows] = useState<DpSavedQuery[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DpSavedQuery | null>(null);
  const [form] = Form.useForm<FormValues>();

  const load = async (): Promise<void> => {
    setLoading(true);
    try {
      const list = await dataPlatformService.listSaved(sourceId);
      setRows(list);
    } catch (err: unknown) {
      const anyErr = err as { message?: string };
      message.error(anyErr.message ?? '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceId]);

  const openCreate = (): void => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ name: '', sqlText: '', isFavorite: false });
    setModalOpen(true);
  };

  const openEdit = (row: DpSavedQuery): void => {
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      sqlText: row.sqlText,
      isFavorite: row.isFavorite,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (): Promise<void> => {
    try {
      const values = await form.validateFields();
      if (editing) {
        const updated = await dataPlatformService.updateSaved(editing.id, {
          name: values.name,
          sqlText: values.sqlText,
          isFavorite: values.isFavorite,
        });
        setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
        message.success('已更新');
      } else {
        const created = await dataPlatformService.createSaved({
          name: values.name,
          sourceId,
          sqlText: values.sqlText,
          isFavorite: values.isFavorite,
        });
        setRows((prev) => [created, ...prev]);
        message.success('已保存');
      }
      setModalOpen(false);
    } catch (err: unknown) {
      const anyErr = err as { errorFields?: unknown; message?: string };
      if (anyErr.errorFields) return;
      message.error(anyErr.message ?? '保存失败');
    }
  };

  const handleDelete = async (id: number): Promise<void> => {
    try {
      await dataPlatformService.deleteSaved(id);
      setRows((prev) => prev.filter((r) => r.id !== id));
      message.success('已删除');
    } catch (err: unknown) {
      const anyErr = err as { message?: string };
      message.error(anyErr.message ?? '删除失败');
    }
  };

  const handleToggleFavorite = async (row: DpSavedQuery): Promise<void> => {
    try {
      const updated = await dataPlatformService.updateSaved(row.id, {
        isFavorite: !row.isFavorite,
      });
      setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch (err: unknown) {
      const anyErr = err as { message?: string };
      message.error(anyErr.message ?? '操作失败');
    }
  };

  const columns: ColumnsType<DpSavedQuery> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (v: string) => <Text style={{ fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: 'SQL 摘要',
      dataIndex: 'sqlText',
      key: 'sqlText',
      render: (sql: string) => (
        <Tooltip title={<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{sql}</pre>}>
          <Text style={{ fontFamily: 'var(--font-mono, ui-monospace, monospace)', fontSize: 12.5 }}>
            {truncate(sql, 60)}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '收藏',
      dataIndex: 'isFavorite',
      key: 'isFavorite',
      width: 80,
      render: (fav: boolean, record: DpSavedQuery) => (
        <Button
          type="text"
          size="small"
          icon={
            fav ? (
              <StarFilled style={{ color: '#fbbf24' }} />
            ) : (
              <StarOutlined style={{ color: 'var(--text-tertiary, #506080)' }} />
            )
          }
          onClick={() => void handleToggleFavorite(record)}
        />
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 170,
      render: (v: string | null) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_: unknown, record: DpSavedQuery) => (
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => onRun(record.sqlText)}
          >
            运行
          </Button>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除？"
            description={`确定删除 "${record.name}" 吗？`}
            onConfirm={() => void handleDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: 'var(--text-secondary, #8895b4)', fontSize: 13 }}>
          常用查询集合
        </Text>
        <Space size={8}>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => void load()}>
            刷新
          </Button>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建
          </Button>
        </Space>
      </div>

      <DataTable<DpSavedQuery>
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        emptyTitle="暂无保存的查询"
        emptyDescription="将常用 SQL 保存下来，方便复用"
      />

      <Modal
        open={modalOpen}
        title={editing ? '编辑查询' : '新建查询'}
        onOk={() => void handleSubmit()}
        onCancel={() => setModalOpen(false)}
        okText={editing ? '保存' : '创建'}
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="例如：今日订单 Top 10" />
          </Form.Item>
          <Form.Item
            name="sqlText"
            label="SQL"
            rules={[{ required: true, message: '请输入 SQL' }]}
          >
            <Input.TextArea
              autoSize={{ minRows: 5, maxRows: 12 }}
              style={{ fontFamily: 'var(--font-mono, ui-monospace, monospace)', fontSize: 12.5 }}
              placeholder="SELECT ..."
            />
          </Form.Item>
          <Form.Item name="isFavorite" label="收藏" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
