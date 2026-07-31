/**
 * TemplatesPanel — 容器模板管理。
 * 卡片网格展示模板（内置 + 自定义），支持新建/编辑/删除，
 * 点击「创建容器」通过 onUseTemplate 回调把模板配置回填到创建容器 Modal。
 * 内置模板展示详细使用说明（long_description），用户可展开查看。
 */
import { useCallback, useEffect, useState } from 'react';
import {
  App, Button, Collapse, Empty, Form, Input, Modal, Popconfirm, Space, Spin, Tag, Tooltip,
} from 'antd';
import {
  DeleteOutlined, DownOutlined, EditOutlined, InfoCircleOutlined, PlusOutlined, RocketOutlined,
} from '@ant-design/icons';
import * as srv from '../../services/compute.service';
import type { ContainerTemplate } from './types';

const { TextArea } = Input;

interface TemplateFormValues {
  name: string;
  image: string;
  description?: string;
  longDescriptionText?: string;
  icon?: string;
  category?: string;
  command?: string;
  portsText?: string;
  envText?: string;
  volumesText?: string;
  restart_policy?: string;
  extra_args?: string;
}

export default function TemplatesPanel({
  onUseTemplate,
}: {
  onUseTemplate: (t: ContainerTemplate) => void;
}) {
  const { message } = App.useApp();
  const [templates, setTemplates] = useState<ContainerTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ContainerTemplate | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<TemplateFormValues>();
  /** 跟踪哪些模板卡片的详情已展开 */
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTemplates(await srv.fetchTemplates());
    } catch {
      // 静默
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ restart_policy: 'no', icon: 'BoxOutlined' });
    setModalOpen(true);
  };

  const openEdit = (t: ContainerTemplate) => {
    setEditing(t);
    form.setFieldsValue({
      name: t.name,
      image: t.image,
      description: t.description,
      longDescriptionText: t.long_description,
      icon: t.icon,
      category: t.category,
      command: t.command,
      restart_policy: t.restart_policy || 'no',
      extra_args: t.extra_args,
      portsText: t.ports.join('\n'),
      envText: t.env_vars.join('\n'),
      volumesText: t.volumes.join('\n'),
    });
    setModalOpen(true);
  };

  const submit = async () => {
    const v = await form.validateFields();
    const payload = {
      name: v.name,
      image: v.image,
      description: v.description,
      long_description: v.longDescriptionText || undefined,
      icon: v.icon,
      category: v.category,
      command: v.command,
      restart_policy: v.restart_policy && v.restart_policy !== 'no' ? v.restart_policy : undefined,
      extra_args: v.extra_args,
      ports: (v.portsText || '').split('\n').map((s: string) => s.trim()).filter(Boolean),
      env_vars: (v.envText || '').split('\n').map((s: string) => s.trim()).filter(Boolean),
      volumes: (v.volumesText || '').split('\n').map((s: string) => s.trim()).filter(Boolean),
    };
    setSaving(true);
    try {
      if (editing) {
        const updated = await srv.updateTemplate(editing.id, payload);
        setTemplates((prev) => prev.map((t) => (t.id === editing.id ? updated : t)));
        message.success('模板已更新');
      } else {
        const created = await srv.createTemplate(payload);
        setTemplates((prev) => [...prev, created]);
        message.success('模板已创建');
      }
      setModalOpen(false);
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '操作失败');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (t: ContainerTemplate) => {
    try {
      await srv.deleteTemplate(t.id);
      setTemplates((prev) => prev.filter((x) => x.id !== t.id));
      message.success(`已删除 ${t.name}`);
    } catch (e: any) {
      message.error(e?.response?.data?.message ?? '删除失败');
    }
  };

  /** 渲染模板卡片的详细说明区（展开/收起） */
  const renderLongDesc = (t: ContainerTemplate) => {
    if (!t.long_description) return null;
    const expanded = expandedIds.has(t.id);
    return (
      <div className="tpl-long-desc">
        <Button
          type="link"
          size="small"
          icon={<InfoCircleOutlined />}
          onClick={() => toggleExpand(t.id)}
          className="tpl-long-desc-toggle"
        >
          {expanded ? '收起详情' : '查看详情'}
        </Button>
        {expanded && (
          <div className="tpl-long-desc-content">
            <pre className="tpl-long-desc-pre">{t.long_description}</pre>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 14,
      }}>
        <span style={{ color: 'var(--ink-40)', fontSize: 12 }}>
          共 {templates.length} 个模板 · 内置 {templates.filter((t) => t.is_builtin).length}
        </span>
        <Button size="small" icon={<PlusOutlined />} onClick={openCreate}>新建模板</Button>
      </div>

      {loading && templates.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div>
      ) : templates.length === 0 ? (
        <Empty description="暂无模板，点「新建模板」创建可复用的容器配置" />
      ) : (
        <div className="tpl-grid">
          {templates.map((t) => (
            <div key={t.id} className={`tpl-card${t.long_description ? ' tpl-card--has-detail' : ''}`}>
              {t.is_builtin && <span className="tpl-builtin-ribbon">内置</span>}
              <div className="tpl-card-head">
                <span className="tpl-name">{t.name}</span>
                {t.category && <Tag style={{ fontSize: 10 }}>{t.category}</Tag>}
              </div>
              <div className="tpl-image">{t.image}</div>
              {t.description && <div className="tpl-desc">{t.description}</div>}
              {t.command && (
                <div className="tpl-command">
                  <span className="tpl-command-prompt">$</span> {t.command}
                </div>
              )}
              <div className="tpl-meta">
                {t.ports.length > 0 && (
                  <Tag style={{ fontSize: 10 }}>{t.ports.join(' ')}</Tag>
                )}
                {t.env_vars.length > 0 && (
                  <Tooltip title={t.env_vars.join('\n')}>
                    <Tag style={{ fontSize: 10 }}>env × {t.env_vars.length}</Tag>
                  </Tooltip>
                )}
                {t.volumes.length > 0 && (
                  <Tooltip title={t.volumes.join('\n')}>
                    <Tag style={{ fontSize: 10 }}>vol × {t.volumes.length}</Tag>
                  </Tooltip>
                )}
                {t.restart_policy && t.restart_policy !== 'no' && (
                  <Tag style={{ fontSize: 10 }}>{t.restart_policy}</Tag>
                )}
              </div>

              {/* 详细说明（展开/收起） */}
              {renderLongDesc(t)}

              <div className="tpl-actions">
                <Button
                  size="small" type="primary" ghost
                  icon={<RocketOutlined />}
                  onClick={() => onUseTemplate(t)}
                >
                  创建容器
                </Button>
                <Space size={2}>
                  <Tooltip title="编辑">
                    <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openEdit(t)} />
                  </Tooltip>
                  {!t.is_builtin && (
                    <Popconfirm title={`删除模板「${t.name}」？`} onConfirm={() => remove(t)}>
                      <Tooltip title="删除">
                        <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                      </Tooltip>
                    </Popconfirm>
                  )}
                </Space>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 新建 / 编辑模板弹窗 */}
      <Modal
        title={editing ? `编辑模板${editing.is_builtin ? '（内置）' : ''}` : '新建模板'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void submit()}
        okText="保存"
        confirmLoading={saving}
        width={640}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" initialValues={{ restart_policy: 'no' }}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input placeholder="OpenCode / My Nginx" disabled={!!editing?.is_builtin} />
          </Form.Item>
          <Form.Item name="image" label="镜像" rules={[{ required: true, message: '请输入镜像名' }]}>
            <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }} placeholder="smanx/opencode" />
          </Form.Item>
          <Form.Item name="description" label="简短描述（卡片上展示）">
            <Input placeholder="模板用途一句话说明" />
          </Form.Item>
          <Form.Item name="command" label="启动命令（覆盖镜像 CMD）" tooltip="追加在镜像名之后，如 opencode web --port 4096">
            <Input style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }} placeholder="opencode web --port 4096" />
          </Form.Item>
          <Form.Item name="portsText" label="端口映射（一行一个，hostPort:containerPort）">
            <TextArea rows={2} style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} placeholder="4096:4096" />
          </Form.Item>
          <Form.Item name="envText" label="环境变量（一行一个，KEY=VALUE）">
            <TextArea rows={2} style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} placeholder="OPENCODE_LOG_LEVEL=info" />
          </Form.Item>
          <Form.Item name="volumesText" label="目录映射（一行一个，hostPath:containerPath）">
            <TextArea rows={2} style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }} placeholder="/data/app:/app" />
          </Form.Item>
          <Form.Item name="restart_policy" label="重启策略">
            <Input placeholder="unless-stopped / always / no" />
          </Form.Item>

          {/* 长描述（Markdown / 纯文本，展开查看） */}
          <Form.Item
            name="longDescriptionText"
            label="详细说明"
            tooltip="镜像的完整使用说明，支持 Markdown。用户可在卡片中展开查看。"
          >
            <TextArea
              rows={10}
              style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
              placeholder={`支持 Markdown 格式，例如：\n\n## 镜像简介\n\n一个开箱即用的 OpenCode Web 容器...\n\n### 运行命令\n\`\`\`bash\ndocker run -itd --name opencode -p 4096:4096 smanx/opencode\n\`\`\`\n\n### 环境变量\n- OPENCODE_HOSTNAME=0.0.0.0\n- OPENCODE_PORT=4096`}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
