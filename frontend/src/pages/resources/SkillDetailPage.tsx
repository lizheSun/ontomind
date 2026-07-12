/**
 * SkillDetailPage — Skill 详情页 (Wave 10 T52)
 *
 * 展示单个 Skill 的详情，提供：
 *   - 来源标识（opencode / manual）：根据 entrypoint 是否指向
 *     `~/.config/opencode/skills/` 推断，供用户区分「一键发现」自动同步的
 *     Skill 与手动新建的 Skill；
 *   - 编辑表单（Drawer）：修改名称、描述、标签、is_active、entrypoint、
 *     docker_image、install_cmd 等；
 *   - 同步按钮：对未安装的 Skill 触发 installSkill，把 Skill 分发到实例；
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
import type { Skill } from '../../types';

const { Paragraph, Text } = Typography;
const { TextArea } = Input;

const TYPE_LABELS: Record<Skill['skill_type'], string> = {
  docker: 'Docker',
  mcp: 'MCP',
  script: '脚本',
  api: 'API',
};

const TYPE_COLORS: Record<
  Skill['skill_type'],
  'emerald' | 'purple' | 'amber' | 'blue'
> = {
  docker: 'emerald',
  mcp: 'purple',
  script: 'amber',
  api: 'blue',
};

/** 根据 Skill 属性推断来源 */
function inferSource(skill: Skill): 'opencode' | 'manual' {
  const ep = skill.entrypoint ?? '';
  const cmd = skill.install_cmd ?? '';
  if (/\.config\/opencode\/skills\//i.test(ep)) return 'opencode';
  if (/\.config\/opencode\//i.test(cmd)) return 'opencode';
  return 'manual';
}

interface EditFormValues {
  name: string;
  skill_type: Skill['skill_type'];
  description?: string;
  entrypoint?: string;
  docker_image?: string;
  install_cmd?: string;
  icon?: string;
  tags?: string;
  is_active: boolean;
}

export default function SkillDetailPage() {
  const { id: idParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const id = Number(idParam);

  const [skill, setSkill] = useState<Skill | null>(null);
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
      const res = await resourcesAPI.getSkill(id);
      const data: Skill = res.data?.data ?? res.data;
      setSkill(data);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 Skill 失败');
    } finally {
      setLoading(false);
    }
  }, [id, message]);

  useEffect(() => {
    load();
  }, [load]);

  const openEdit = () => {
    if (!skill) return;
    form.setFieldsValue({
      name: skill.name,
      skill_type: skill.skill_type,
      description: skill.description ?? '',
      entrypoint: skill.entrypoint ?? '',
      docker_image: skill.docker_image ?? '',
      install_cmd: skill.install_cmd ?? '',
      icon: skill.icon ?? '',
      tags: (skill.tags ?? []).join(', '),
      is_active: skill.is_active,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    if (!skill) return;
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload: Record<string, unknown> = {
        name: values.name,
        skill_type: values.skill_type,
        description: values.description || null,
        entrypoint: values.entrypoint || null,
        docker_image: values.docker_image || null,
        install_cmd: values.install_cmd || null,
        icon: values.icon || null,
        tags: values.tags
          ? values.tags
              .split(',')
              .map((t) => t.trim())
              .filter(Boolean)
          : null,
        is_active: values.is_active,
      };
      await resourcesAPI.updateSkill(skill.id, payload);
      message.success('保存成功');
      setEditOpen(false);
      await load();
    } catch (err) {
      if (err && typeof err === 'object' && 'errorFields' in err) {
        // form validation error — do nothing, Form will show inline errors
        return;
      }
      message.error(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    if (!skill) return;
    setSyncing(true);
    try {
      await resourcesAPI.installSkill(skill.id);
      message.success('同步成功');
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = () => {
    if (!skill) return;
    DangerConfirm({
      title: `确认删除 Skill “${skill.name}”？`,
      content: '删除后不可恢复。',
      onOk: async () => {
        try {
          await resourcesAPI.deleteSkill(skill.id);
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

  if (!skill) {
    return (
      <GlassPanel>
        <Paragraph style={{ color: '#8895b4' }}>未找到该 Skill</Paragraph>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/resources')}
        >
          返回列表
        </Button>
      </GlassPanel>
    );
  }

  const source = inferSource(skill);

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <Link to="/resources">资源管理</Link> },
          { title: 'Skill' },
          { title: skill.name },
        ]}
      />
      <PageHeader
        title={skill.name}
        subtitle={skill.description ?? undefined}
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
              disabled={skill.is_installed}
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
            <TagPill color={TYPE_COLORS[skill.skill_type] ?? 'blue'}>
              {TYPE_LABELS[skill.skill_type] ?? skill.skill_type}
            </TagPill>
          </Descriptions.Item>
          <Descriptions.Item label="名称">{skill.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {skill.is_active ? (
              <Tag color="success">启用</Tag>
            ) : (
              <Tag>未启用</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="安装状态">
            {skill.is_installed ? (
              <Tag color="success">已安装</Tag>
            ) : (
              <Tag>未安装</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="安装时间">
            {skill.installed_at
              ? new Date(skill.installed_at).toLocaleString()
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Docker 镜像">
            <Text
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
              }}
            >
              {skill.docker_image || '-'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="图标">{skill.icon || '-'}</Descriptions.Item>
          <Descriptions.Item label="入口 (entrypoint)" span={2}>
            <Text
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
              }}
            >
              {skill.entrypoint || '-'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="安装命令" span={2}>
            <Text
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12,
                color: '#c5cee0',
              }}
            >
              {skill.install_cmd || '-'}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="标签" span={2}>
            {skill.tags && skill.tags.length > 0 ? (
              <Space size={4} wrap>
                {skill.tags.map((t) => (
                  <Tag key={t}>{t}</Tag>
                ))}
              </Space>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {skill.description || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {skill.created_at
              ? new Date(skill.created_at).toLocaleString()
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {skill.updated_at
              ? new Date(skill.updated_at).toLocaleString()
              : '-'}
          </Descriptions.Item>
        </Descriptions>
      </GlassPanel>

      <Drawer
        title={
          <Space>
            <EditOutlined style={{ color: '#60a5fa' }} />
            编辑 Skill
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
            <Input placeholder="Skill 名称" />
          </Form.Item>
          <Form.Item
            label="类型"
            name="skill_type"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select
              options={[
                { value: 'docker', label: 'Docker' },
                { value: 'mcp', label: 'MCP' },
                { value: 'script', label: '脚本' },
                { value: 'api', label: 'API' },
              ]}
            />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <TextArea
              rows={3}
              placeholder="用一句话描述这个 Skill 的用途"
            />
          </Form.Item>
          <Form.Item label="入口 (entrypoint)" name="entrypoint">
            <TextArea
              rows={2}
              placeholder="例如 /path/to/script.py 或 python -m foo"
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
            />
          </Form.Item>
          <Form.Item label="Docker 镜像" name="docker_image">
            <Input placeholder="e.g. ghcr.io/org/skill:latest" />
          </Form.Item>
          <Form.Item label="安装命令" name="install_cmd">
            <TextArea
              rows={2}
              placeholder="e.g. pip install -e ."
              style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
            />
          </Form.Item>
          <Form.Item
            label="标签"
            name="tags"
            extra="使用英文逗号分隔多个标签"
          >
            <Input placeholder="research, ocr, tool" />
          </Form.Item>
          <Form.Item label="图标" name="icon">
            <Input placeholder="图标 key 或 URL" />
          </Form.Item>
          <Form.Item label="启用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
}
