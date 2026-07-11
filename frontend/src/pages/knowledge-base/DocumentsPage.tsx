import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Form,
  Input,
  message,
  Modal,
  Space,
  Upload,
  type UploadFile,
} from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { DataTable, TagPill, DangerConfirm } from '../../components/common';
import KbLibraryLayout from './KbLibraryLayout';
import { knowledgeBaseService } from '../../services/knowledgeBase.service';
import { useKnowledgeBaseStore } from '../../stores/knowledgeBaseStore';
import type { KbDocument } from '../../types/knowledgeBase';

interface UploadFormValues {
  titleZh: string;
  descriptionMd?: string;
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function DocumentsPage() {
  const libraries = useKnowledgeBaseStore((s) => s.libraries);
  const libraryId = useMemo(
    () => libraries.find((l) => l.code === 'document')?.id,
    [libraries],
  );

  const [entries, setEntries] = useState<KbDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQ, setSearchQ] = useState('');
  const [searchIds, setSearchIds] = useState<number[] | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm<UploadFormValues>();

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const list = await knowledgeBaseService.listDocuments();
      setEntries(list);
    } catch {
      message.error('加载文档列表失败');
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
          'document',
        );
        setSearchIds(grouped.document.map((r) => r.id));
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

  const openUpload = () => {
    setFile(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleDelete = (row: KbDocument) => {
    DangerConfirm({
      title: `确认删除“${row.titleZh}”？`,
      content: '此操作不可撤销，文件将从存储中移除',
      onOk: async () => {
        try {
          await knowledgeBaseService.deleteDocument(row.id);
          message.success('已删除');
          setEntries((cur) => cur.filter((e) => e.id !== row.id));
        } catch {
          message.error('删除失败');
        }
      },
    });
  };

  const handleDownload = async (row: KbDocument) => {
    try {
      const blob = await knowledgeBaseService.downloadDocument(row.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = row.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error('下载失败');
    }
  };

  const handleEdit = (row: KbDocument) => {
    let nextTitle = row.titleZh;
    let nextDesc = row.descriptionMd ?? '';
    Modal.confirm({
      title: `编辑“${row.titleZh}”`,
      centered: true,
      okText: '保存',
      cancelText: '取消',
      content: (
        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 12 }}>
            <div style={{ marginBottom: 6 }}>标题</div>
            <Input
              defaultValue={row.titleZh}
              onChange={(e) => {
                nextTitle = e.target.value;
              }}
            />
          </div>
          <div>
            <div style={{ marginBottom: 6 }}>描述</div>
            <Input.TextArea
              rows={4}
              defaultValue={row.descriptionMd ?? ''}
              onChange={(e) => {
                nextDesc = e.target.value;
              }}
            />
          </div>
        </div>
      ),
      onOk: async () => {
        try {
          const updated = await knowledgeBaseService.updateDocument(row.id, {
            title_zh: nextTitle,
            description_md: nextDesc || null,
          });
          setEntries((cur) => cur.map((e) => (e.id === updated.id ? updated : e)));
          message.success('已更新');
        } catch {
          message.error('更新失败');
        }
      },
    });
  };

  const handleUpload = async () => {
    if (!file) {
      message.warning('请先选择文件');
      return;
    }
    if (!libraryId) {
      message.error('知识库尚未加载，请稍后重试');
      return;
    }
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const created = await knowledgeBaseService.uploadDocument(file, {
        titleZh: values.titleZh,
        libraryId,
        descriptionMd: values.descriptionMd,
      });
      setEntries((cur) => [created, ...cur]);
      message.success('上传成功');
      setModalOpen(false);
      setFile(null);
      form.resetFields();
    } catch (err) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('上传失败');
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ColumnsType<KbDocument> = [
    { title: '标题', dataIndex: 'titleZh', key: 'titleZh' },
    { title: '文件名', dataIndex: 'filename', key: 'filename' },
    {
      title: '类型',
      dataIndex: 'mimeType',
      key: 'mimeType',
      width: 160,
      render: (v: string) => v || '-',
    },
    {
      title: '大小',
      dataIndex: 'sizeBytes',
      key: 'sizeBytes',
      width: 100,
      render: (v: number) => humanSize(v ?? 0),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[] | null) =>
        tags && tags.length > 0 ? (
          <Space size={4} wrap>
            {tags.map((t) => (
              <TagPill key={t} color="cyan">
                {t}
              </TagPill>
            ))}
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: '上传时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 170,
      render: (v: string | null) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, row: KbDocument) => (
        <Space size={4}>
          <Button type="link" size="small" onClick={() => handleDownload(row)}>
            下载
          </Button>
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

  const uploadFileList: UploadFile[] = file
    ? [{ uid: '-1', name: file.name, status: 'done' }]
    : [];

  return (
    <KbLibraryLayout
      libraryCode="document"
      title="文档库"
      subtitle="上传的文档、报告与手册"
      onSearchChange={setSearchQ}
      onCreate={openUpload}
    >
      <DataTable<KbDocument>
        rowKey="id"
        columns={columns}
        dataSource={visible}
        loading={loading}
        emptyTitle="暂无文档"
        emptyDescription="点击右上角“新建”上传第一份文档"
      />
      <Modal
        title="上传文档"
        open={modalOpen}
        onOk={handleUpload}
        onCancel={() => {
          setModalOpen(false);
          setFile(null);
          form.resetFields();
        }}
        confirmLoading={submitting}
        okText="上传"
        cancelText="取消"
        centered
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item label="文件" required>
            <Upload
              beforeUpload={(f) => {
                setFile(f);
                return false;
              }}
              maxCount={1}
              fileList={uploadFileList}
              onRemove={() => {
                setFile(null);
                return true;
              }}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
          <Form.Item
            name="titleZh"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="文档标题" />
          </Form.Item>
          <Form.Item name="descriptionMd" label="描述">
            <Input.TextArea rows={4} placeholder="可选：简要说明" />
          </Form.Item>
        </Form>
      </Modal>
    </KbLibraryLayout>
  );
}
