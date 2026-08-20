import { useCallback, useEffect, useState } from 'react';
import {
  App as AntApp,
  Alert,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  applyLlmSetting,
  createLlmSetting,
  deleteLlmSetting,
  listLlmSettings,
  testLlmSettings,
  testSavedLlmSetting,
  updateLlmSetting,
} from '../../services/metadata.service';
import type { LlmSetting } from '../../types/metadata';

const { Title, Paragraph, Text } = Typography;

interface FormValues {
  name?: string;
  base_url: string;
  model: string;
  api_key?: string;
  timeout: number;
  max_concurrency: number;
  enabled: boolean;
  is_default: boolean;
}

function errMsg(e: unknown): string {
  const err = e as { response?: { data?: { detail?: { message?: string } | string } }; message?: string };
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) return String((detail as { message: unknown }).message);
  return err?.message || '操作失败';
}

export default function LlmSettingsPage() {
  const { message } = AntApp.useApp();
  const [form] = Form.useForm<FormValues>();
  const [rows, setRows] = useState<LlmSetting[]>([]);
  const [envFallback, setEnvFallback] = useState<LlmSetting | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<LlmSetting | null>(null);
  const [formTesting, setFormTesting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const all = await listLlmSettings();
      setRows(all.filter((r) => r.source === 'db'));
      setEnvFallback(all.find((r) => r.source !== 'db') ?? null);
    } catch (e: unknown) {
      message.error(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      base_url: 'https://api.deepseek.com',
      model: '',
      timeout: 120,
      max_concurrency: 4,
      enabled: true,
      is_default: false,
    });
    setModalOpen(true);
  };

  const openEdit = (row: LlmSetting) => {
    setEditing(row);
    form.resetFields();
    form.setFieldsValue({
      name: row.name,
      base_url: row.base_url,
      model: row.model,
      api_key: '',
      timeout: row.timeout,
      max_concurrency: row.max_concurrency,
      enabled: row.enabled,
      is_default: row.is_default,
    });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      const v = await form.validateFields();
      setSaving(true);
      const base = {
        name: v.name?.trim() || undefined,
        base_url: v.base_url.trim(),
        model: v.model.trim(),
        timeout: v.timeout,
        max_concurrency: v.max_concurrency,
        enabled: v.enabled,
        is_default: v.is_default,
      };
      const apiKey = v.api_key ? String(v.api_key).trim() : '';
      if (editing) {
        await updateLlmSetting(editing.id, apiKey ? { ...base, api_key: apiKey } : base);
        message.success('已保存');
      } else {
        if (!apiKey) {
          message.warning('请填写 API Key');
          return;
        }
        await createLlmSetting({ ...base, api_key: apiKey });
        message.success('已创建');
      }
      setModalOpen(false);
      await load();
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error(errMsg(e));
    } finally {
      setSaving(false);
    }
  };

  const testForm = async () => {
    try {
      const v = form.getFieldsValue();
      if (!String(v.api_key || '').trim()) {
        message.warning(editing ? '留空表示沿用已保存 Key，无法用表单测试；请填写新 Key 或从列表「测试」验证。' : '请填写 API Key 后再测试');
        return;
      }
      setFormTesting(true);
      const r = await testLlmSettings({
        base_url: v.base_url,
        model: v.model,
        api_key: v.api_key!,
        timeout: v.timeout,
      });
      message.success(`连通成功：${r.reply || 'OK'}（${r.latency_ms ?? '-'}ms）`);
    } catch (e: unknown) {
      message.error(errMsg(e));
    } finally {
      setFormTesting(false);
    }
  };

  const testRow = async (row: LlmSetting) => {
    setTestingId(row.id);
    try {
      const r = await testSavedLlmSetting(row.id);
      message.success(`「${row.name}」连通成功：${r.reply || 'OK'}（${r.latency_ms ?? '-'}ms）`);
    } catch (e: unknown) {
      message.error(errMsg(e));
    } finally {
      setTestingId(null);
    }
  };

  const apply = async (row: LlmSetting) => {
    try {
      await applyLlmSetting(row.id);
      message.success(`已应用「${row.name}」为当前生效配置`);
      await load();
    } catch (e: unknown) {
      message.error(errMsg(e));
    }
  };

  const remove = async (row: LlmSetting) => {
    try {
      await deleteLlmSetting(row.id);
      message.success('已删除');
      await load();
    } catch (e: unknown) {
      message.error(errMsg(e));
    }
  };

  const toggleEnabled = async (row: LlmSetting, enabled: boolean) => {
    try {
      await updateLlmSetting(row.id, { enabled });
      message.success(enabled ? '已启用' : '已停用');
      await load();
    } catch (e: unknown) {
      message.error(errMsg(e));
    }
  };

  const columns: ColumnsType<LlmSetting> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string, row) => (
        <Space size={6}>
          <Text strong={row.is_default}>{v || row.model}</Text>
          {row.is_default ? <Tag color="green">当前生效</Tag> : null}
        </Space>
      ),
    },
    { title: '模型', dataIndex: 'model', key: 'model', render: (v: string) => <Text code>{v}</Text> },
    { title: 'Base URL', dataIndex: 'base_url', key: 'base_url', ellipsis: true },
    {
      title: 'Key',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
      render: (v: string | null, row) => (row.has_api_key ? <Text type="secondary">{v ?? '已保存'}</Text> : <Tag color="orange">未保存</Tag>),
    },
    { title: '超时(s)', dataIndex: 'timeout', key: 'timeout', width: 80 },
    {
      title: '状态',
      key: 'enabled',
      width: 90,
      render: (_, row) => (
        <Switch
          size="small"
          checked={row.enabled}
          disabled={row.is_default}
          onChange={(c) => void toggleEnabled(row, c)}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_, row) => (
        <Space size={4} wrap>
          {!row.is_default ? (
            <Button size="small" type="link" onClick={() => void apply(row)}>
              设为默认
            </Button>
          ) : null}
          <Button size="small" type="link" loading={testingId === row.id} onClick={() => void testRow(row)}>
            测试
          </Button>
          <Button size="small" type="link" onClick={() => openEdit(row)}>
            编辑
          </Button>
          <Popconfirm
            title={`删除配置「${row.name || row.model}」？`}
            onConfirm={() => void remove(row)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" type="link" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="page-enter" style={{ padding: 24, maxWidth: 1080 }}>
      <Title level={4} style={{ marginTop: 0 }}>
        LLM 配置
      </Title>
      <Paragraph type="secondary">
        管理多套 LLM 配置（DeepSeek / 火山方舟 / 任意 OpenAI 兼容端点），用于元数据标注、本体生成等任务。
        配置写入 <Text code>MySQL</Text>（API Key 加密存储）；<Text strong>「设为默认」的那一条</Text>即当前生效配置，
        优先于 <Text code>backend/.env</Text>。
      </Paragraph>

      {envFallback && rows.length === 0 ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={`当前无数据库配置，使用 ${envFallback.source === 'env' ? '.env 兜底' : '无可用 LLM'}（${envFallback.model || '未设置模型'}）`}
        />
      ) : null}

      <Card
        title="配置列表"
        extra={
          <Button type="primary" onClick={openCreate}>
            新增配置
          </Button>
        }
      >
        <Table<LlmSetting>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={false}
          locale={{ emptyText: '暂无配置，点击「新增配置」添加' }}
        />
      </Card>

      <Modal
        title={editing ? '编辑 LLM 配置' : '新增 LLM 配置'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void save()}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width={560}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="name" label="名称" extra="便于区分多套配置，留空则用模型名">
            <Input placeholder="如：DeepSeek V4 Pro" />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL（OpenAI 格式）" rules={[{ required: true, message: '请填写 Base URL' }]}>
            <Input placeholder="https://api.deepseek.com" />
          </Form.Item>
          <Form.Item
            name="model"
            label="模型（API model 参数）"
            rules={[{ required: true, message: '请填写模型' }]}
            extra="填 API 实际接受的模型名，如 deepseek-v4-pro / deepseek-v4-flash"
          >
            <Input placeholder="deepseek-v4-pro" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="API Key"
            rules={editing ? [] : [{ required: true, message: '请填写 API Key' }]}
            extra={editing ? '留空则沿用已保存 Key；填写则覆盖' : undefined}
          >
            <Input.Password placeholder="sk-..." autoComplete="new-password" />
          </Form.Item>
          <Space size={24} wrap>
            <Form.Item name="timeout" label="超时(秒)">
              <InputNumber min={5} max={600} style={{ width: 130 }} />
            </Form.Item>
            <Form.Item name="max_concurrency" label="最大并发">
              <InputNumber min={1} max={32} style={{ width: 130 }} />
            </Form.Item>
            <Form.Item name="enabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="is_default" label="设为默认（当前生效）" valuePropName="checked" extra={editing?.is_default ? '取消勾选将不再作为当前生效配置' : undefined}>
              <Switch />
            </Form.Item>
          </Space>
          <Button loading={formTesting} onClick={() => void testForm()} block style={{ marginBottom: 4 }}>
            测试连通（当前表单）
          </Button>
        </Form>
      </Modal>
    </div>
  );
}
