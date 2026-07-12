/**
 * MCPDetailPage — MCP 详情页 (Wave 10 T52)
 *
 * 展示单个 MCP 的详情，提供：
 *   - 来源标识（opencode / manual）：根据 command / auto_discovery_url
 *     是否指向 `~/.config/opencode/opencode.json` 场景推断；
 *   - 编辑表单（Drawer）：修改名称、mcp_type、URL/command/args、
 *     env_vars、headers、auto_discovery_url、is_active；
 *   - 同步按钮：触发 auto-discover 或重新读取 tools_manifest（此处调用
 *     autoDiscoverMCP 端点，将 auto_discovery_url 作为 api_url 输入）；
 *   - 删除按钮：DangerConfirm 二次确认，成功后返回资源列表。
 */
import { useCallback, useEffect, useState } from 'react';
import {
  App,
  Breadcrumb,
  Button,
  Descriptions,
  Drawer,
  Form,
  Input,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  CloudSyncOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  DangerConfirm,
  GlassPanel,
  PageHeader,
  TagPill,
} from '../../components/common';
import { resourcesAPI } from '../../services';
import type { MCPConfig } from '../../types';

const { Paragraph, Text } = Typography;
const { TextArea } = Input;

const TYPE_LABELS: Record<MCPConfig['mcp_type'], string> = {
  sse: 'SSE',
  stdio: 'Stdio',
  http: 'HTTP',
};

const TYPE_COLORS: Record<
  MCPConfig['mcp_type'],
  'blue' | 'emerald' | 'amber'
> = {
  sse: 'blue',
  stdio: 'emerald',
  http: 'amber',
};

/** 根据 MCP 属性推断来源 */
function inferSource(mcp: MCPConfig): 'opencode' | 'manual' {
  const cmd = mcp.command ?? '';
  const discovery = mcp.auto_discovery_url ?? '';
  if (/opencode/i.test(cmd)) return 'opencode';
  if (/opencode/i.test(discovery)) return 'opencode';
  if (mcp.auto_discovery_enabled && discovery) return 'opencode';
  return 'manual';
}

interface EditFormValues {
  name: string;
  mcp_type: MCPConfig['mcp_type'];
  url?: string;
  command?: string;
  args?: string;
  headers?: string;
  env_vars?: string;
  auto_discovery_url?: string;
  auto_discovery_enabled: boolean;
  description?: string;
  is_active: boolean;
}

function stringifyJson(v: unknown): string {
  if (v == null) return '';
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

function parseJsonField(raw: string | undefined, field: string): Record<string, unknown> | null {
  const s = (raw ?? '').trim();
  if (!s) return null;
  try {
    const parsed = JSON.parse(s);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
    throw new Error(`${field} 必须是 JSON 对象`);
  } catch (err) {
    throw new Error(
      `${field} JSON 解析失败：${err instanceof Error ? err.message : String(err)}`,
    );
  }
}

export default function MCPDetailPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const id = Number(idParam);

  const [mcp, setMcp] = useState<MCPConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [form] = Form.useForm<EditFormValues>();

  const load = useCallback(async () => {
    if (!Number.isFinite(id)) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await resourcesAPI.getMCP(id);
      const data: MCPConfig = res.data?.data ?? res.data;
      setMcp(data);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 MCP 失败');
    } finally {
      setLoading(false);
    }
  }, [id, message]);

  useEffect(() => {
    load();
  }, [load]);

  const openEdit = () => {
    if (!mcp) return;
    form.setFieldsValue({
      name: mcp.name,
      mcp_type: mcp.mcp_type,
      url: mcp.url ?? '',
      command: mcp.command ?? '',
      args: (mcp.args ?? []).join(' '),
      headers: stringifyJson(mcp.headers),
      env_vars: stringifyJson(mcp.env_vars),
      auto_discovery_url: mcp.auto_discovery_url ?? '',
      auto_discovery_enabled: mcp.auto_discovery_enabled,
      description: mcp.description ?? '',
      is_active: mcp.is_active,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    if (!mcp) return;
    let values: EditFormValues;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    let headers: Record<string, unknown> | null;
    let envVars: Record<string, unknown> | null;
    try {
      headers = parseJsonField(values.headers, 'headers');
      envVars = parseJsonField(values.env_vars, 'env_vars');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '字段解析失败');
      return;
    }
    setSaving(true);
    try {
      const args = values.args
        ? values.args.split(/\s+/).filter(Boolean)
        : null;
      const payload: Partial<MCPConfig> = {
        name: values.name,
        mcp_type: values.mcp_type,
        url: values.url || undefined,
        command: values.command || undefined,
        args: args ?? undefined,
        headers: headers ?? undefined,
        env_vars: envVars ?? undefined,
        auto_discovery_url: values.auto_discovery_url || undefined,
        auto_discovery_enabled: values.auto_discovery_enabled,
        description: values.description || undefined,
        is_active: values.is_active,
      };
      await resourcesAPI.updateMCP(mcp.id, payload);
      message.success('保存成功');
      setEditOpen(false);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    if (!mcp) return;
    if (!mcp.auto_discovery_url) {
      message.warning('未配置 auto_discovery_url，无法同步');
      return;
    }
    setSyncing(true);
    try {
      await resourcesAPI.autoDiscoverMCP({
        api_url: mcp.auto_discovery_url,
        method: 'GET',
        description_text: mcp.description ?? undefined,
      });
      message.success('同步成功');
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = () => {
    if (!mcp) return;
    DangerConfirm({
      title: `确认删除 MCP “${mcp.name}”？`,
      content: '删除后不可恢复。',
      onOk: async () => {
        try {
          await resourcesAPI.deleteMCP(mcp.id);
          message.success('已删除');
          navigate('/resources');
        } catch (err) {
          message.error(err instanceof Error ? err.message : '删除失败');
        }
      },
    });
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  if (!mcp) {
    return (
      <GlassPanel>
        <Paragraph style={{ color: '#8895b4' }}>未找到该 MCP</Paragraph>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/resources')}
        >
          返回列表
        </Button>
      </GlassPanel>
    );
  }

  const source = inferSource(mcp);

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <Link to="/resources">资源管理</Link> },
          { title: 'MCP' },
          { title: mcp.name },
        ]}
      />
      <PageHeader
        title={mcp.name}
        subtitle={mcp.description ?? undefined}
        extra={
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/resources')}
            >
              返回列表
            </Button>
            <Button
              icon={<CloudSyncOutlined />}
              loading={syncing}
              onClick={handleSync}
              disabled={!mcp.auto_discovery_url}
            >
              同步
            </Button>
            <Button icon={<EditOutlined />} onClick={openEdit}>
              编辑
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDelete}
            >
              删除
            </Button>
          </Space>
        }
      />

      <GlassPanel>
        <Descriptions
          bordered
          size="small"
          column={2}
          styles={{ label: { width: 140 } }}
        >
          <Descriptions.Item label="来源">
            <TagPill color={source === 'opencode' ? 'purple' : 'blue'}>
              {source === 'opencode' ? 'opencode (自动同步)' : 'manual (手动)'}
            </TagPill>
          </Descriptions.Item>
          <Descriptions.Item label="类型">
            <TagPill color={TYPE_COLORS[mcp.mcp_type] ?? 'blue'}>
              {TYPE_LABELS[mcp.mcp_type] ?? mcp.mcp_type}
            </TagPill>
          </Descriptions.Item>
          <Descriptions.Item label="名称">{mcp.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {mcp.is_active ? (
              <Tag color="success">启用</Tag>
            ) : (
              <Tag>未启用</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="URL" span={2}>
            <Text
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
              }}
            >
              {mcp.url || '-'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="Command" span={2}>
            <Text
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
              }}
            >
              {mcp.command || '-'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="Args" span={2}>
            {mcp.args && mcp.args.length > 0 ? (
              <Space size={4} wrap>
                {mcp.args.map((a, i) => (
                  <Tag
                    key={`${i}-${a}`}
                    style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
                  >
                    {a}
                  </Tag>
                ))}
              </Space>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Headers" span={2}>
            <pre
              style={{
                margin: 0,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
                maxHeight: 160,
                overflow: 'auto',
              }}
            >
              {stringifyJson(mcp.headers) || '-'}
            </pre>
          </Descriptions.Item>
          <Descriptions.Item label="Env Vars" span={2}>
            <pre
              style={{
                margin: 0,
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
                maxHeight: 160,
                overflow: 'auto',
              }}
            >
              {stringifyJson(mcp.env_vars) || '-'}
            </pre>
          </Descriptions.Item>
          <Descriptions.Item label="Auto-Discovery URL" span={2}>
            <Text
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
              }}
            >
              {mcp.auto_discovery_url || '-'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="自动发现开关">
            {mcp.auto_discovery_enabled ? (
              <Tag color="processing">开启</Tag>
            ) : (
              <Tag>关闭</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="工具清单条目数">
            {mcp.tools_manifest
              ? Object.keys(mcp.tools_manifest).length
              : 0}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {mcp.description || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {mcp.created_at
              ? new Date(mcp.created_at).toLocaleString()
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {mcp.updated_at
              ? new Date(mcp.updated_at).toLocaleString()
              : '-'}
          </Descriptions.Item>
        </Descriptions>
      </GlassPanel>

      <Drawer
        title={
          <Space>
            <EditOutlined style={{ color: '#60a5fa' }} />
            编辑 MCP
          </Space>
        }
        open={editOpen}
        onClose={() => setEditOpen(false)}
        width={600}
        extra={
          <Space>
            <Button onClick={() => setEditOpen(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={handleSave}>
              保存
            </Button>
          </Space>
        }
      >
        <Form<EditFormValues> form={form} layout="vertical">
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="MCP 名称" />
          </Form.Item>
          <Form.Item
            label="类型"
            name="mcp_type"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select
              options={[
                { value: 'sse', label: 'SSE' },
                { value: 'stdio', label: 'Stdio' },
                { value: 'http', label: 'HTTP' },
              ]}
            />
          </Form.Item>
          <Form.Item label="URL" name="url">
            <Input placeholder="https://... 或 http://..." />
          </Form.Item>
          <Form.Item label="Command" name="command">
            <Input placeholder="e.g. npx some-mcp-server" />
          </Form.Item>
          <Form.Item label="Args" name="args" extra="以空格分隔多个参数">
            <Input placeholder="--flag value" />
          </Form.Item>
          <Form.Item
            label="Headers (JSON)"
            name="headers"
            extra="留空或输入合法 JSON 对象"
          >
            <TextArea
              rows={3}
              placeholder='{"Authorization": "Bearer ..."}'
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
            />
          </Form.Item>
          <Form.Item
            label="Env Vars (JSON)"
            name="env_vars"
            extra="留空或输入合法 JSON 对象"
          >
            <TextArea
              rows={3}
              placeholder='{"API_KEY": "..."}'
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
            />
          </Form.Item>
          <Form.Item label="Auto-Discovery URL" name="auto_discovery_url">
            <Input placeholder="https://.../.well-known/mcp" />
          </Form.Item>
          <Form.Item
            label="启用自动发现"
            name="auto_discovery_enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="用一句话描述这个 MCP" />
          </Form.Item>
          <Form.Item label="启用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}
