/**
 * ExpertTeamPage — 专家团管理页面（Editorial Light 主题）
 *
 * 特性：
 * - 卡片网格：显示所有专家 + 实时状态点
 * - 启停：卡片上的按钮实时启动/关闭 opencode agent 文件
 * - 创建向导：模型 / Skill / MCP / SOP 结构化配置
 * - 编辑抽屉：修改任意字段，保存后立刻更新 agent md 文件
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App, Button, Drawer, Empty, Form, Input, InputNumber,
  Popconfirm, Select, Space, Spin, Tag, Tooltip, Typography,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, PoweroffOutlined,
  PlayCircleOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons';
import { expertService, type Expert } from '../../services/expert.service';

const { Text, Paragraph } = Typography;

const STATUS_META: Record<Expert['status'], { color: string; label: string; dot: string }> = {
  online:  { color: '#476a4b', label: '在线',   dot: '#22c55e' },
  offline: { color: '#8f8b84', label: '离线',   dot: '#bfbcb5' },
  error:   { color: '#a5361e', label: '错误',   dot: '#ef4444' },
};

// 常用 opencode skills
const SKILL_OPTIONS = [
  'byted-web-search', 'byted-supabase', 'doc-coauthoring',
  'frontend-design', 'web-artifacts-builder', 'canvas-design',
  'mcp-builder', 'skill-creator', 'xlsx', 'docx', 'pdf', 'pptx',
  'algorithmic-art', 'internal-comms', 'brand-guidelines',
  'slack-gif-creator', 'theme-factory', 'webapp-testing',
  'arkcli-shared', 'arkcli-chat', 'arkcli-usage',
];

interface FormValues {
  id?: number;
  name: string;
  slug: string;
  avatar?: string;
  description?: string;
  role?: string;
  sop?: string;
  provider?: string;
  model?: string;
  skills?: string[];
  mcps?: string[];
  host?: string;
  port?: number;
  allowRead?: boolean;
  allowWrite?: boolean;
  allowBash?: boolean;
  allowTodo?: boolean;
}

export default function ExpertTeamPage() {
  const { message } = App.useApp();
  const [experts, setExperts] = useState<Expert[]>([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [editing, setEditing] = useState<Expert | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [form] = Form.useForm<FormValues>();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setExperts(await expertService.list());
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void load();
    const t = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(t);
  }, [load]);

  const stats = useMemo(() => ({
    online: experts.filter((e) => e.status === 'online').length,
    total: experts.length,
    offline: experts.filter((e) => e.status !== 'online').length,
  }), [experts]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      host: '127.0.0.1', port: 4096,
      provider: 'agent-plan', model: 'ark-code-latest',
      skills: [], mcps: [],
      allowRead: true, allowWrite: true, allowBash: true, allowTodo: true,
    });
    setDrawerOpen(true);
  };

  const openEdit = (e: Expert) => {
    setEditing(e);
    form.resetFields();
    form.setFieldsValue({
      id: e.id, name: e.name, slug: e.slug,
      avatar: e.avatar ?? '',
      description: e.description ?? '',
      role: e.role ?? '',
      sop: e.sop ?? '',
      provider: e.provider ?? undefined,
      model: e.model ?? undefined,
      skills: e.skills ?? [],
      mcps: e.mcps ?? [],
      host: e.host, port: e.port,
      allowRead: e.tools?.read ?? true,
      allowWrite: e.tools?.write ?? true,
      allowBash: e.tools?.bash ?? true,
      allowTodo: e.tools?.todo ?? true,
    });
    setDrawerOpen(true);
  };

  const seed = async () => {
    setSeeding(true);
    try {
      const { added } = await expertService.seed();
      message.success(`已注入 ${added} 个内置专家`);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '初始化失败');
    } finally {
      setSeeding(false);
    }
  };

  const doStart = async (e: Expert) => {
    setBusyId(e.id);
    try {
      await expertService.start(e.id);
      message.success(`${e.name} 已启动 — agent 文件已生成`);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '启动失败');
    } finally { setBusyId(null); }
  };

  const doStop = async (e: Expert) => {
    setBusyId(e.id);
    try {
      await expertService.stop(e.id);
      message.success(`${e.name} 已关闭`);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '关闭失败');
    } finally { setBusyId(null); }
  };

  const doDelete = async () => {
    if (!editing) return;
    try {
      await expertService.remove(editing.id);
      message.success(`${editing.name} 已删除`);
      setDrawerOpen(false); setEditing(null);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const submitForm = async () => {
    const v = await form.validateFields();
    const tools: Record<string, boolean> = {};
    if (v.allowRead) tools.read = true;
    if (v.allowWrite) tools.write = true;
    if (v.allowBash) tools.bash = true;
    if (v.allowTodo) tools.todo = true;

    const payload = {
      name: v.name,
      avatar: v.avatar || null,
      description: v.description || null,
      role: v.role || null,
      sop: v.sop || null,
      provider: v.provider || null,
      model: v.model || null,
      skills: v.skills ?? [],
      mcps: v.mcps ?? [],
      tools,
      host: v.host,
      port: v.port,
    };
    try {
      if (editing) {
        await expertService.update(editing.id, payload);
        message.success('已更新');
      } else {
        await expertService.create({ ...payload, slug: v.slug });
        message.success('已创建 — opencode agent 文件已写入');
      }
      setDrawerOpen(false); setEditing(null);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败');
    }
  };

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '8px 16px 24px' }}>
      <div style={{
        display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
        gap: 24, padding: '24px 4px 20px',
        borderBottom: '1px solid var(--border-hairline)', marginBottom: 24,
      }}>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: 34, fontWeight: 500,
            letterSpacing: '-0.02em', margin: 0, color: 'var(--ink-100)', fontStyle: 'italic',
          }}>专家团</h1>
          <Text style={{ color: 'var(--ink-60)', fontSize: 13, marginTop: 6, display: 'block' }}>
            每位专家 = 一份 opencode agent 定义 + 模型 + Skill/MCP 组合。启动后可在对话工作台里选取。
          </Text>
          <Space size={16} style={{ marginTop: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>
              总数 <b style={{ color: 'var(--ink-100)' }}>{stats.total}</b>
            </span>
            <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>
              在线 <b style={{ color: '#22c55e' }}>{stats.online}</b>
            </span>
            <span style={{ fontSize: 12, color: 'var(--ink-40)' }}>
              离线 <b style={{ color: 'var(--ink-60)' }}>{stats.offline}</b>
            </span>
          </Space>
        </div>
        <Space>
          <Tooltip title="刷新">
            <Button icon={<ReloadOutlined />} onClick={() => void load()} />
          </Tooltip>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            添加专家
          </Button>
        </Space>
      </div>

      {loading && experts.length === 0 ? (
        <div style={{ padding: 80, textAlign: 'center' }}><Spin /></div>
      ) : experts.length === 0 ? (
        <div style={{
          padding: '80px 24px', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 14,
        }}>
          <Empty description={<span style={{ color: 'var(--ink-60)' }}>专家团为空</span>} />
          <Button type="primary" style={{ marginTop: 16 }} loading={seeding} onClick={seed}>
            注入 4 个内置专家
          </Button>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          gap: 16,
        }}>
          {experts.map((e) => {
            const meta = STATUS_META[e.status];
            return (
              <div
                key={e.id}
                onClick={() => openEdit(e)}
                style={{
                  background: 'var(--paper-00)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 14, padding: 20, cursor: 'pointer',
                  transition: 'border-color .12s, box-shadow .12s',
                  position: 'relative', display: 'flex', flexDirection: 'column',
                  gap: 12, minHeight: 200,
                }}
                onMouseEnter={(ev) => {
                  ev.currentTarget.style.borderColor = 'var(--border-default)';
                  ev.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                }}
                onMouseLeave={(ev) => {
                  ev.currentTarget.style.borderColor = 'var(--border-subtle)';
                  ev.currentTarget.style.boxShadow = 'none';
                }}
              >
                <span style={{
                  position: 'absolute', top: 16, right: 16,
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  fontSize: 11, color: meta.color, fontWeight: 500,
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: meta.dot,
                    boxShadow: e.status === 'online' ? `0 0 0 3px ${meta.dot}22` : 'none',
                  }} />
                  {meta.label}
                </span>

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 12,
                    background: 'var(--paper-02)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 24, lineHeight: 1, flexShrink: 0,
                  }}>{e.avatar || '🧑‍💼'}</div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{
                      fontFamily: 'var(--font-serif)', fontSize: 17, fontWeight: 500,
                      color: 'var(--ink-100)', letterSpacing: '-0.01em',
                    }}>{e.name}</div>
                    {e.description && (
                      <Text style={{
                        fontSize: 12.5, color: 'var(--ink-60)', display: 'block', marginTop: 2,
                        overflow: 'hidden', textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap', maxWidth: 220,
                      }} title={e.description}>{e.description}</Text>
                    )}
                  </div>
                </div>

                {e.role && (
                  <Paragraph ellipsis={{ rows: 2 }} style={{
                    margin: 0, fontSize: 12.5, color: 'var(--ink-60)', lineHeight: 1.6,
                  }}>{e.role.replace(/^#[^\n]*\n\n?/, '')}</Paragraph>
                )}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {e.model && (
                    <Tag style={{
                      fontFamily: 'var(--font-mono)', fontSize: 10,
                      color: 'var(--ink-80)', background: 'var(--paper-02)',
                      border: '1px solid var(--border-hairline)',
                    }}>{e.model}</Tag>
                  )}
                  {(e.skills || []).slice(0, 3).map((s) => (
                    <Tag key={s} style={{
                      fontSize: 10, color: 'var(--accent, #3b52af)',
                      background: 'rgba(59, 82, 175, 0.08)',
                      border: '1px solid rgba(59, 82, 175, 0.20)',
                    }}>{s}</Tag>
                  ))}
                  {e.skills && e.skills.length > 3 && (
                    <Tag style={{ fontSize: 10 }}>+{e.skills.length - 3}</Tag>
                  )}
                </div>

                <div style={{
                  marginTop: 'auto', display: 'flex', gap: 8,
                  paddingTop: 12, borderTop: '1px solid var(--border-hairline)',
                }} onClick={(ev) => ev.stopPropagation()}>
                  {e.status === 'online' ? (
                    <Button danger size="small" icon={<PoweroffOutlined />}
                      loading={busyId === e.id} onClick={() => void doStop(e)}>关闭</Button>
                  ) : (
                    <Button type="primary" size="small" icon={<PlayCircleOutlined />}
                      loading={busyId === e.id} onClick={() => void doStart(e)}>启动</Button>
                  )}
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(e)}>编辑</Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Drawer
        title={<span style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 500 }}>
          {editing ? `编辑：${editing.name}` : '添加专家'}
        </span>}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={640}
        footer={
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <div>
              {editing && (
                <Popconfirm title={`确认删除「${editing.name}」？`} onConfirm={() => void doDelete()}>
                  <Button danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              )}
            </div>
            <Space>
              <Button onClick={() => setDrawerOpen(false)}>取消</Button>
              <Button type="primary" onClick={() => void submitForm()}>保存</Button>
            </Space>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          {/* 基本信息 */}
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: 13, fontWeight: 500,
            color: 'var(--ink-40)', textTransform: 'uppercase',
            letterSpacing: '0.06em', marginBottom: 12,
          }}>基本信息</div>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="avatar" label="头像" style={{ width: 80, marginBottom: 12 }}>
              <Input placeholder="📊" maxLength={4} style={{ textAlign: 'center', fontSize: 18 }} />
            </Form.Item>
            <Form.Item name="name" label="名称" rules={[{ required: true }]} style={{ flex: 1, marginBottom: 12 }}>
              <Input placeholder="数据分析专家" />
            </Form.Item>
          </Space>
          <Form.Item name="slug" label="标识符 (slug — opencode agent 名)"
            tooltip="生成 ~/.config/opencode/agent/{slug}.md"
            rules={[
              { required: true },
              { pattern: /^[a-z0-9-]+$/, message: '仅允许小写字母、数字、连字符' },
            ]}
          >
            <Input placeholder="data-analyst" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="description" label="一句话描述">
            <Input placeholder="擅长 SQL、数据建模、指标定义与数据可视化" maxLength={200} />
          </Form.Item>

          {/* 角色 & SOP */}
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: 13, fontWeight: 500,
            color: 'var(--ink-40)', textTransform: 'uppercase',
            letterSpacing: '0.06em', margin: '20px 0 12px',
          }}>角色 & 工作流</div>
          <Form.Item name="role" label="角色定位 (system prompt)">
            <Input.TextArea rows={5}
              placeholder={`# 角色定位

你是一位资深数据分析师...`}
              style={{ fontFamily: 'var(--font-sans)', fontSize: 13 }}
            />
          </Form.Item>
          <Form.Item name="sop" label="SOP / 工作流程">
            <Input.TextArea rows={3}
              placeholder="1. 理解需求 → 2. 探查数据 → 3. 编写 SQL → 4. 验证 → 5. 出图"
              style={{ fontFamily: 'var(--font-sans)', fontSize: 13 }}
            />
          </Form.Item>

          {/* 模型 */}
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: 13, fontWeight: 500,
            color: 'var(--ink-40)', textTransform: 'uppercase',
            letterSpacing: '0.06em', margin: '20px 0 12px',
          }}>模型配置</div>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="provider" label="Provider" style={{ flex: 1, marginBottom: 12 }}>
              <Input placeholder="agent-plan" />
            </Form.Item>
            <Form.Item name="model" label="Model" style={{ flex: 2, marginBottom: 12 }}>
              <Input placeholder="ark-code-latest" />
            </Form.Item>
          </Space>

          {/* 能力 */}
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: 13, fontWeight: 500,
            color: 'var(--ink-40)', textTransform: 'uppercase',
            letterSpacing: '0.06em', margin: '20px 0 12px',
          }}>能力（Skills / MCPs / Tools）</div>
          <Form.Item name="skills" label="Skills">
            <Select mode="tags"
              placeholder="从常用中选或自己输入"
              options={SKILL_OPTIONS.map((s) => ({ value: s, label: s }))}
              tokenSeparators={[',', ' ']}
            />
          </Form.Item>
          <Form.Item name="mcps" label="MCPs">
            <Select mode="tags"
              placeholder="dataPro-search, byted-web-search 等"
              tokenSeparators={[',', ' ']}
            />
          </Form.Item>
          <Form.Item label="工具权限">
            <Space size={16} wrap>
              <Form.Item name="allowRead" valuePropName="checked" noStyle>
                <label><input type="checkbox" defaultChecked style={{ marginRight: 4 }} />read</label>
              </Form.Item>
              <Form.Item name="allowWrite" valuePropName="checked" noStyle>
                <label><input type="checkbox" defaultChecked style={{ marginRight: 4 }} />write</label>
              </Form.Item>
              <Form.Item name="allowBash" valuePropName="checked" noStyle>
                <label><input type="checkbox" defaultChecked style={{ marginRight: 4 }} />bash</label>
              </Form.Item>
              <Form.Item name="allowTodo" valuePropName="checked" noStyle>
                <label><input type="checkbox" defaultChecked style={{ marginRight: 4 }} />todo</label>
              </Form.Item>
            </Space>
          </Form.Item>

          {/* 部署 */}
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: 13, fontWeight: 500,
            color: 'var(--ink-40)', textTransform: 'uppercase',
            letterSpacing: '0.06em', margin: '20px 0 12px',
          }}>opencode 服务端点</div>
          <Space size={12} style={{ display: 'flex', width: '100%' }}>
            <Form.Item name="host" label="Host" style={{ flex: 2, marginBottom: 0 }}>
              <Input placeholder="127.0.0.1" />
            </Form.Item>
            <Form.Item name="port" label="Port" style={{ width: 120, marginBottom: 0 }}>
              <InputNumber style={{ width: '100%' }} min={1} max={65535} />
            </Form.Item>
          </Space>
        </Form>
      </Drawer>
    </div>
  );
}