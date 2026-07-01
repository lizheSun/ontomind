import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card, Button, Modal, Form, Input, Select, Tag, Typography, Space, Popconfirm,
  message, Empty, Tooltip, Badge, Segmented, App, Progress, Divider,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, RocketOutlined,
  ThunderboltOutlined, PartitionOutlined, FileTextOutlined,
  AuditOutlined, EyeOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ReloadOutlined, ArrowRightOutlined,
  HolderOutlined, CalendarOutlined, ProfileOutlined,
  AppstoreOutlined, FlagOutlined,
} from '@ant-design/icons';
import { projectsAPI } from '../../services/index';
import type { Project, Requirement, Plan, Task, KanbanData } from '../../types/index';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// ===================== 项目选择器 =====================

function ProjectSelector({
  projects, selectedId, loading, onSelect, onRefresh, onCreate,
}: {
  projects: Project[];
  selectedId: number | null;
  loading: boolean;
  onSelect: (id: number) => void;
  onRefresh: () => void;
  onCreate: () => void;
}) {
  if (!projects.length && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <Empty description={<span style={{ color: '#506380' }}>暂无项目，请先创建</span>}>
          <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>创建项目</Button>
        </Empty>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
      {projects.map(p => (
        <button
          key={p.id}
          onClick={() => onSelect(p.id)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 16px', borderRadius: 12, border: 'none', cursor: 'pointer',
            background: selectedId === p.id
              ? 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(139,92,246,0.15))'
              : 'rgba(255,255,255,0.03)',
            borderColor: selectedId === p.id ? 'rgba(59,130,246,0.4)' : 'rgba(255,255,255,0.06)',
            borderStyle: 'solid', borderWidth: 1,
            transition: 'all 0.2s',
            color: selectedId === p.id ? '#e8eef5' : '#7b8ea8',
          }}
          onMouseEnter={e => {
            if (selectedId !== p.id) {
              e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
              e.currentTarget.style.color = '#e8eef5';
            }
          }}
          onMouseLeave={e => {
            if (selectedId !== p.id) {
              e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
              e.currentTarget.style.color = '#7b8ea8';
            }
          }}
        >
          <span style={{ fontSize: 18 }}>{p.icon || '📁'}</span>
          <span style={{ fontSize: 13, fontWeight: 600 }}>{p.name}</span>
          {p.status === 'archived' && <Tag color="default" style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>已归档</Tag>}
        </button>
      ))}
      <Button size="small" icon={<PlusOutlined />} onClick={onCreate} style={{ borderRadius: 10 }}>
        新建
      </Button>
      <Button size="small" icon={<ReloadOutlined />} onClick={onRefresh} style={{ borderRadius: 10 }} />
    </div>
  );
}

// ===================== 需求卡片 =====================

const reqTypeLabel: Record<string, { color: string; text: string }> = {
  feature: { color: 'blue', text: '功能' },
  bug: { color: 'red', text: 'Bug' },
  improvement: { color: 'purple', text: '改进' },
  performance: { color: 'orange', text: '性能' },
};

const reqStatusLabel: Record<string, { color: string; icon: React.ReactNode }> = {
  pending_review: { color: 'default', icon: <AuditOutlined /> },
  passed: { color: 'green', icon: <CheckCircleOutlined /> },
  rejected: { color: 'red', icon: <CloseCircleOutlined /> },
  in_progress: { color: 'blue', icon: <ThunderboltOutlined /> },
  done: { color: 'green', icon: <CheckCircleOutlined /> },
};

function RequirementCard({
  req, onAnalyze, onDecompose, onEdit, onDelete, analyzing, decomposing,
}: {
  req: Requirement;
  onAnalyze: (id: number) => void;
  onDecompose: (id: number) => void;
  onEdit: (req: Requirement) => void;
  onDelete: (id: number) => void;
  analyzing: number | null;
  decomposing: number | null;
}) {
  const type = reqTypeLabel[req.req_type] || { color: 'default', text: req.req_type };
  const st = reqStatusLabel[req.status] || { color: 'default', icon: null };

  return (
    <Card
      size="small"
      style={{
        background: 'rgba(255,255,255,0.02)', borderRadius: 14,
        border: '1px solid rgba(255,255,255,0.05)',
        marginBottom: 12, transition: 'all 0.2s',
      }}
      styles={{ body: { padding: '14px 16px' } }}
      className="card-hover"
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)'; }}
    >
      {/* 标题行 */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Tag color={type.color} style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}>{type.text}</Tag>
            <Tag color={req.priority === 'P0' ? 'red' : req.priority === 'P1' ? 'orange' : req.priority === 'P2' ? 'blue' : 'default'}
              style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}>{req.priority}</Tag>
            {st.icon && <Tag color={st.color} style={{ fontSize: 11, lineHeight: '18px', margin: 0 }} icon={st.icon}>{req.status}</Tag>}
          </div>
          <Text strong style={{ fontSize: 14, color: '#e8eef5', lineHeight: 1.5 }}>{req.title}</Text>
        </div>
      </div>

      {/* 描述 */}
      {req.description && (
        <Paragraph style={{ color: '#506380', fontSize: 12, marginBottom: 10, lineHeight: 1.6 }}
          ellipsis={{ rows: 2 }}>{req.description}</Paragraph>
      )}

      {/* 评分 */}
      {req.score_total != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 10, padding: '8px 12px', background: 'rgba(255,255,255,0.02)', borderRadius: 8 }}>
          <Tooltip title="清晰度">
            <span style={{ fontSize: 11, color: '#506380' }}>清晰度 <Text style={{ color: '#e8eef5', fontWeight: 600 }}>{req.score_clarity}</Text></span>
          </Tooltip>
          <Tooltip title="可行性">
            <span style={{ fontSize: 11, color: '#506380' }}>可行性 <Text style={{ color: '#e8eef5', fontWeight: 600 }}>{req.score_feasibility}</Text></span>
          </Tooltip>
          <Tooltip title="业务价值">
            <span style={{ fontSize: 11, color: '#506380' }}>价值 <Text style={{ color: '#e8eef5', fontWeight: 600 }}>{req.score_value}</Text></span>
          </Tooltip>
          <Tooltip title="综合评分">
            <Progress
              size={20} type="circle" percent={req.score_total * 10}
              format={() => req.score_total?.toFixed(1)}
              status={req.score_total >= 5 ? 'success' : 'exception'}
            />
          </Tooltip>
        </div>
      )}

      {/* 评审意见 */}
      {req.review_comment && (
        <Text style={{ fontSize: 11, color: '#7b8ea8', display: 'block', marginBottom: 10, lineHeight: 1.5 }}>
          💬 {req.review_comment}
        </Text>
      )}

      {/* 操作 */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {req.status === 'pending_review' && (
          <Button size="small" type="primary" ghost icon={<AuditOutlined />}
            loading={analyzing === req.id}
            onClick={() => onAnalyze(req.id)}
            style={{ borderRadius: 8, fontSize: 12 }}>Agent 评审</Button>
        )}
        {req.status === 'passed' && !req.is_decomposed && (
          <Button size="small" style={{ borderRadius: 8, fontSize: 12, color: '#34d399', borderColor: '#34d399' }}
            icon={<PartitionOutlined />}
            loading={decomposing === req.id}
            onClick={() => onDecompose(req.id)}>拆解为任务</Button>
        )}
        {req.is_decomposed && (
          <Tag icon={<CheckCircleOutlined />} color="blue" style={{ fontSize: 11 }}>已拆解 {req.status === 'in_progress' ? '· 进行中' : ''}</Tag>
        )}
        <div style={{ flex: 1 }} />
        <Button type="text" size="small" icon={<EditOutlined />} onClick={() => onEdit(req)} style={{ color: '#7b8ea8' }} />
        <Popconfirm title="确定删除？" onConfirm={() => onDelete(req.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      </div>
    </Card>
  );
}

// ===================== 需求表单弹窗 =====================

function RequirementModal({
  open, editing, projectId, onClose, onSuccess,
}: {
  open: boolean;
  editing: Requirement | null;
  projectId: number | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { notification } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      if (editing) form.setFieldsValue(editing);
      else form.resetFields();
    }
  }, [open, editing]);

  const handleSubmit = async () => {
    if (!projectId) return;
    try {
      const values = await form.validateFields();
      setLoading(true);
      if (editing) {
        await projectsAPI.updateRequirement(projectId, editing.id, values);
        message.success('更新成功');
      } else {
        await projectsAPI.createRequirement(projectId, values);
        message.success('创建成功，请点击「Agent 评审」进行分析');
      }
      onClose();
      onSuccess();
    } catch (err: any) {
      if (err?.errorFields) return;
      notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setLoading(false); }
  };

  return (
    <Modal
      title={<Space>{editing ? <EditOutlined /> : <PlusOutlined />}{editing ? '编辑需求' : '创建需求'}</Space>}
      open={open} onCancel={onClose} width={640}
      footer={[<Button key="cancel" onClick={onClose}>取消</Button>, <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>保存</Button>]}
    >
      <Form form={form} layout="vertical" size="large" initialValues={{ req_type: 'feature', priority: 'P2' }}>
        <Form.Item name="title" label="需求标题" rules={[{ required: true, message: '请输入标题' }]}>
          <Input placeholder="简洁描述需求目标" />
        </Form.Item>
        <Space size={16} style={{ width: '100%' }}>
          <Form.Item name="req_type" label="需求类型" rules={[{ required: true }]} style={{ width: 180 }}>
            <Select>
              <Select.Option value="feature">功能需求</Select.Option>
              <Select.Option value="bug">Bug 修复</Select.Option>
              <Select.Option value="improvement">技术改进</Select.Option>
              <Select.Option value="performance">性能优化</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="priority" label="优先级" rules={[{ required: true }]} style={{ width: 120 }}>
            <Select>
              <Select.Option value="P0">P0 紧急</Select.Option>
              <Select.Option value="P1">P1 高</Select.Option>
              <Select.Option value="P2">P2 中</Select.Option>
              <Select.Option value="P3">P3 低</Select.Option>
            </Select>
          </Form.Item>
        </Space>
        <Form.Item name="description" label="详细描述">
          <TextArea rows={4} placeholder="背景、目标、详细说明…" />
        </Form.Item>
        <Form.Item name="acceptance_criteria" label="验收标准">
          <TextArea rows={2} placeholder="明确可衡量的完成标准…" />
        </Form.Item>
        <Form.Item name="impact_scope" label="影响范围">
          <Input placeholder="涉及的系统、模块或团队" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ===================== 项目表单弹窗 =====================

function ProjectModal({
  open, editing, onClose, onSuccess,
}: {
  open: boolean;
  editing: Project | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { notification } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      if (editing) form.setFieldsValue(editing);
      else form.resetFields();
    }
  }, [open, editing]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      if (editing) {
        await projectsAPI.updateProject(editing.id, values);
        message.success('更新成功');
      } else {
        await projectsAPI.createProject(values);
        message.success('创建成功');
      }
      onClose();
      onSuccess();
    } catch (err: any) {
      if (err?.errorFields) return;
      notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setLoading(false); }
  };

  return (
    <Modal
      title={<Space>{editing ? <EditOutlined /> : <PlusOutlined />}{editing ? '编辑项目' : '新建项目'}</Space>}
      open={open} onCancel={onClose} width={520}
      footer={[<Button key="cancel" onClick={onClose}>取消</Button>, <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>保存</Button>]}
    >
      <Form form={form} layout="vertical" size="large">
        <Space size={16} style={{ width: '100%' }}>
          <Form.Item name="icon" label="图标" style={{ width: 100 }}>
            <Input placeholder="📁" maxLength={4} style={{ fontSize: 18 }} />
          </Form.Item>
          <Form.Item name="key" label="标识" rules={[{ required: true, message: '请输入' }, { pattern: /^[A-Z0-9]+$/, message: '大写字母+数字' }]} style={{ width: 140 }}>
            <Input placeholder="PROJ" maxLength={16} style={{ textTransform: 'uppercase' }} />
          </Form.Item>
        </Space>
        <Form.Item name="name" label="项目名称" rules={[{ required: true, message: '请输入' }]}>
          <Input placeholder="我的项目" />
        </Form.Item>
        <Form.Item name="description" label="项目描述">
          <TextArea rows={2} placeholder="项目的目标与范围…" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ===================== 计划表单弹窗 =====================

function PlanModal({
  open, editing, projectId, onClose, onSuccess,
}: {
  open: boolean;
  editing: Plan | null;
  projectId: number | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { notification } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      if (editing) form.setFieldsValue(editing);
      else form.resetFields();
    }
  }, [open, editing]);

  const handleSubmit = async () => {
    if (!projectId) return;
    try {
      const values = await form.validateFields();
      setLoading(true);
      if (editing) {
        await projectsAPI.updatePlan(projectId, editing.id, values);
        message.success('更新成功');
      } else {
        await projectsAPI.createPlan(projectId, values);
        message.success('创建成功');
      }
      onClose();
      onSuccess();
    } catch (err: any) {
      if (err?.errorFields) return;
      notification.error({ title: '操作失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setLoading(false); }
  };

  return (
    <Modal
      title={<Space>{editing ? <EditOutlined /> : <PlusOutlined />}{editing ? '编辑计划' : '新建计划'}</Space>}
      open={open} onCancel={onClose} width={520}
      footer={[<Button key="cancel" onClick={onClose}>取消</Button>, <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>保存</Button>]}
    >
      <Form form={form} layout="vertical" size="large" initialValues={{ plan_type: 'sprint' }}>
        <Form.Item name="name" label="计划名称" rules={[{ required: true }]}>
          <Input placeholder="Sprint 1 / V1.0 发布" />
        </Form.Item>
        <Space size={16} style={{ width: '100%' }}>
          <Form.Item name="plan_type" label="类型" rules={[{ required: true }]} style={{ width: 180 }}>
            <Select>
              <Select.Option value="sprint">Sprint</Select.Option>
              <Select.Option value="release">Release</Select.Option>
              <Select.Option value="milestone">Milestone</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="status" label="状态" style={{ width: 140 }} initialValue="planned">
            <Select>
              <Select.Option value="planned">规划中</Select.Option>
              <Select.Option value="active">进行中</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
              <Select.Option value="cancelled">已取消</Select.Option>
            </Select>
          </Form.Item>
        </Space>
        <Space size={16} style={{ width: '100%' }}>
          <Form.Item name="start_date" label="开始日期" style={{ flex: 1 }}><Input type="date" /></Form.Item>
          <Form.Item name="end_date" label="结束日期" style={{ flex: 1 }}><Input type="date" /></Form.Item>
        </Space>
        <Form.Item name="goal" label="目标"><TextArea rows={2} placeholder="本迭代的目标…" /></Form.Item>
      </Form>
    </Modal>
  );
}

// ===================== 敏捷看板 =====================

function KanbanBoard({ projectId }: { projectId: number | null }) {
  const [kanban, setKanban] = useState<KanbanData>({ todo: [], in_progress: [], review: [], done: [] });
  const [loading, setLoading] = useState(false);
  const { notification } = App.useApp();
  const dragItem = useRef<{ id: number; status: string } | null>(null);

  const fetchKanban = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await projectsAPI.getKanban(projectId);
      setKanban(res.data?.data || { todo: [], in_progress: [], review: [], done: [] });
    } catch { notification.error({ title: '加载看板失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { fetchKanban(); }, [fetchKanban]);

  const handleDrop = async (targetStatus: string) => {
    const item = dragItem.current;
    if (!item || !projectId || item.status === targetStatus) return;
    try {
      await projectsAPI.moveTask(projectId, item.id, { status: targetStatus });
      fetchKanban();
      message.success('已移动');
    } catch (err: any) {
      notification.error({ title: '移动失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    }
  };

  const priorityColor = (p: string) =>
    p === 'P0' ? '#f87171' : p === 'P1' ? '#fbbf24' : p === 'P2' ? '#60a5fa' : '#7b8ea8';

  const columns: { key: string; title: string; icon: React.ReactNode; color: string; tasks: Task[] }[] = [
    { key: 'todo', title: '待开始', icon: <FileTextOutlined />, color: '#506380', tasks: kanban.todo },
    { key: 'in_progress', title: '进行中', icon: <ThunderboltOutlined />, color: '#3b82f6', tasks: kanban.in_progress },
    { key: 'review', title: '评审中', icon: <AuditOutlined />, color: '#f59e0b', tasks: kanban.review },
    { key: 'done', title: '已完成', icon: <CheckCircleOutlined />, color: '#34d399', tasks: kanban.done },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={fetchKanban} size="small" style={{ borderRadius: 8 }}>刷新看板</Button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {columns.map(col => (
          <div key={col.key}
            onDragOver={e => { e.preventDefault(); e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
            onDragLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.01)'; }}
            onDrop={e => { e.preventDefault(); e.currentTarget.style.background = 'rgba(255,255,255,0.01)'; handleDrop(col.key); }}
            style={{
              background: 'rgba(255,255,255,0.01)', borderRadius: 14,
              border: '1px solid rgba(255,255,255,0.06)',
              minHeight: 300, padding: 12,
              transition: 'background 0.2s',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, padding: '0 4px' }}>
              <Space>
                <span style={{ color: col.color, fontSize: 14 }}>{col.icon}</span>
                <Text strong style={{ fontSize: 13, color: '#c8d6e5' }}>{col.title}</Text>
              </Space>
              <Tag style={{ fontSize: 11 }}>{col.tasks.length}</Tag>
            </div>

            {col.tasks.length === 0 && (
              <div style={{ textAlign: 'center', padding: '30px 10px', color: '#3d5170', fontSize: 12 }}>
                拖拽任务到此处
              </div>
            )}

            {col.tasks.map(task => (
              <div key={task.id}
                draggable
                onDragStart={() => { dragItem.current = { id: task.id, status: task.status }; }}
                onDragEnd={() => { dragItem.current = null; }}
                style={{
                  background: 'rgba(255,255,255,0.03)', borderRadius: 10,
                  border: '1px solid rgba(255,255,255,0.05)',
                  padding: '10px 12px', marginBottom: 8,
                  cursor: 'grab', transition: 'all 0.15s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6, marginBottom: 6 }}>
                  <HolderOutlined style={{ color: '#3d5170', fontSize: 12, marginTop: 2, flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <Text style={{ fontSize: 13, color: '#e8eef5', lineHeight: 1.4, display: 'block', marginBottom: 6 }}>
                      {task.title}
                    </Text>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Tag color={priorityColor(task.priority) === '#f87171' ? 'red' : priorityColor(task.priority) === '#fbbf24' ? 'orange' : priorityColor(task.priority) === '#60a5fa' ? 'blue' : 'default'}
                        style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>{task.priority}</Tag>
                      {task.assignee_agent_type && (
                        <Tag style={{ fontSize: 10, lineHeight: '16px', margin: 0, background: 'rgba(139,92,246,0.1)', color: '#a78bfa', border: 'none' }}>
                          {task.assignee_agent_type}
                        </Tag>
                      )}
                      {task.estimated_hours != null && (
                        <Text style={{ fontSize: 10, color: '#506380' }}>{task.estimated_hours}h</Text>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ===================== 计划列表 =====================

const planStatusMap: Record<string, { color: string; text: string }> = {
  planned: { color: 'default', text: '规划中' },
  active: { color: 'blue', text: '进行中' },
  completed: { color: 'green', text: '已完成' },
  cancelled: { color: 'default', text: '已取消' },
};

function PlanList({ projectId }: { projectId: number | null }) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Plan | null>(null);
  const { notification } = App.useApp();

  const fetchPlans = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await projectsAPI.listPlans(projectId);
      setPlans(res.data?.data || []);
    } catch { notification.error({ title: '加载计划失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { fetchPlans(); }, [fetchPlans]);

  const handleDelete = async (id: number) => {
    if (!projectId) return;
    try { await projectsAPI.deletePlan(projectId, id); message.success('删除成功'); fetchPlans(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setModalOpen(true); }} style={{ borderRadius: 8 }}>新建计划</Button>
      </div>

      {plans.length === 0 && !loading ? (
        <Empty description={<span style={{ color: '#506380' }}>暂无计划，创建第一个 Sprint</span>} style={{ padding: 40 }} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {plans.map(plan => {
            const st = planStatusMap[plan.status] || planStatusMap.planned;
            return (
              <Card key={plan.id} size="small"
                style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.05)' }}
                styles={{ body: { padding: '14px 18px' } }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 4, height: 40, borderRadius: 2,
                    background: plan.status === 'active' ? '#3b82f6' : plan.status === 'completed' ? '#34d399' : '#506380',
                    flexShrink: 0,
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                      <Text strong style={{ fontSize: 14, color: '#e8eef5' }}>{plan.name}</Text>
                      <Tag icon={<FlagOutlined />} style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>
                        {plan.plan_type === 'sprint' ? 'Sprint' : plan.plan_type === 'release' ? 'Release' : 'Milestone'}
                      </Tag>
                      <Badge status={st.color === 'blue' ? 'processing' : st.color === 'green' ? 'success' : 'default'} text={st.text} />
                    </div>
                    {plan.goal && <Text style={{ fontSize: 12, color: '#506380' }}>{plan.goal}</Text>}
                  </div>
                  <Space size={4}>
                    {(plan.start_date || plan.end_date) && (
                      <Tag style={{ fontSize: 11 }} icon={<CalendarOutlined />}>
                        {plan.start_date || '?'} → {plan.end_date || '?'}
                      </Tag>
                    )}
                    <Button type="text" size="small" icon={<EditOutlined />} style={{ color: '#7b8ea8' }}
                      onClick={() => { setEditing(plan); setModalOpen(true); }} />
                    <Popconfirm title="确定删除？" onConfirm={() => handleDelete(plan.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
                      <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </Space>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <PlanModal open={modalOpen} editing={editing} projectId={projectId}
        onClose={() => setModalOpen(false)} onSuccess={fetchPlans} />
    </div>
  );
}

// ===================== 主页面 =====================

export default function ProjectsPage() {
  const { notification } = App.useApp();

  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);

  const [tab, setTab] = useState<string>('requirements');
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [reqLoading, setReqLoading] = useState(false);

  const [reqModalOpen, setReqModalOpen] = useState(false);
  const [editingReq, setEditingReq] = useState<Requirement | null>(null);

  const [analyzing, setAnalyzing] = useState<number | null>(null);
  const [decomposing, setDecomposing] = useState<number | null>(null);

  // Fetch projects
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await projectsAPI.listProjects({ skip: 0, limit: 50 });
      setProjects(res.data?.data || []);
    } catch { notification.error({ title: '加载项目失败', placement: 'top' }); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  // Fetch requirements when project changes
  const fetchRequirements = useCallback(async () => {
    if (!selectedId) { setRequirements([]); return; }
    setReqLoading(true);
    try {
      const res = await projectsAPI.listRequirements(selectedId);
      setRequirements(res.data?.data || []);
    } catch { notification.error({ title: '加载需求失败', placement: 'top' }); }
    finally { setReqLoading(false); }
  }, [selectedId]);

  useEffect(() => { fetchRequirements(); }, [fetchRequirements]);

  // Actions
  const handleAnalyze = async (reqId: number) => {
    if (!selectedId) return;
    setAnalyzing(reqId);
    try {
      const res = await projectsAPI.analyzeRequirement(selectedId, reqId);
      const data = res.data?.data;
      const a = data?.analysis;
      if (a?.passed) {
        message.success(`评审通过 · 综合 ${a.score_total} 分 — ${a.comment}`);
      } else {
        message.warning(`评审未通过 · 综合 ${a.score_total} 分 — ${a.comment}`);
      }
      fetchRequirements();
    } catch (err: any) {
      notification.error({ title: '评审失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setAnalyzing(null); }
  };

  const handleDecompose = async (reqId: number) => {
    if (!selectedId) return;
    setDecomposing(reqId);
    try {
      const res = await projectsAPI.decomposeRequirement(selectedId, reqId);
      const count = res.data?.data?.count;
      message.success(`拆解完成 · 生成 ${count} 个任务，已加入看板`);
      fetchRequirements();
    } catch (err: any) {
      notification.error({ title: '拆解失败', description: err?.response?.data?.detail || err?.message, placement: 'top' });
    } finally { setDecomposing(null); }
  };

  const handleDeleteReq = async (reqId: number) => {
    if (!selectedId) return;
    try { await projectsAPI.deleteRequirement(selectedId, reqId); message.success('删除成功'); fetchRequirements(); }
    catch (err: any) { notification.error({ title: '删除失败', description: err?.response?.data?.detail || err?.message, placement: 'top' }); }
  };

  const selectedProject = projects.find(p => p.id === selectedId);

  return (
    <div style={{ maxWidth: 1400 }}>
      {/* 标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ color: '#e8eef5', marginBottom: 4 }}>
          <AppstoreOutlined style={{ marginRight: 10 }} />
          需求项目管理
        </Title>
        <Paragraph style={{ color: '#506380', marginBottom: 0 }}>
          Agent 驱动的需求评审、任务拆解与敏捷看板
        </Paragraph>
      </div>

      {/* 项目选择器 */}
      <Card
        size="small"
        style={{ background: 'rgba(255,255,255,0.015)', borderRadius: 16, border: '1px solid rgba(255,255,255,0.06)', marginBottom: 20 }}
        styles={{ body: { padding: '16px 20px' } }}
      >
        <ProjectSelector
          projects={projects} selectedId={selectedId} loading={loading}
          onSelect={setSelectedId} onRefresh={fetchProjects}
          onCreate={() => { setEditingProject(null); setProjectModalOpen(true); }}
        />
        {selectedProject && (
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <EditOutlined style={{ color: '#506380', fontSize: 12 }} />
            <Text style={{ fontSize: 12, color: '#506380' }}>{selectedProject.description || '暂无描述'}</Text>
            <div style={{ flex: 1 }} />
            <Button size="small" onClick={() => { setEditingProject(selectedProject); setProjectModalOpen(true); }}
              style={{ borderRadius: 8, fontSize: 12 }}>编辑项目</Button>
          </div>
        )}
      </Card>

      {/* 内容区 */}
      {!selectedId ? (
        <Card style={{ background: 'rgba(255,255,255,0.015)', borderRadius: 16, border: '1px solid rgba(255,255,255,0.06)' }}>
          <Empty description={<span style={{ color: '#506380' }}>请选择一个项目开始工作</span>} style={{ padding: 60 }} />
        </Card>
      ) : (
        <>
          <div style={{ marginBottom: 16 }}>
            <Segmented
              size="large"
              value={tab}
              onChange={v => setTab(v as string)}
              options={[
                { label: <span><FileTextOutlined /> 需求池</span>, value: 'requirements' },
                { label: <span><AppstoreOutlined /> 敏捷看板</span>, value: 'kanban' },
                { label: <span><CalendarOutlined /> 计划</span>, value: 'plans' },
              ]}
              style={{ background: 'rgba(255,255,255,0.03)', padding: 3, borderRadius: 12 }}
            />
          </div>

          {tab === 'requirements' && (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingReq(null); setReqModalOpen(true); }}
                  style={{ borderRadius: 8 }}>新建需求</Button>
              </div>
              {requirements.length === 0 && !reqLoading ? (
                <Card style={{ background: 'rgba(255,255,255,0.015)', borderRadius: 16, border: '1px solid rgba(255,255,255,0.06)' }}>
                  <Empty description={<span style={{ color: '#506380' }}>暂无需求，创建第一个需求后使用 Agent 自动评审</span>} style={{ padding: 40 }} />
                </Card>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 12 }}>
                  {requirements.map(req => (
                    <RequirementCard key={req.id} req={req}
                      onAnalyze={handleAnalyze} onDecompose={handleDecompose}
                      onEdit={(r) => { setEditingReq(r); setReqModalOpen(true); }}
                      onDelete={handleDeleteReq}
                      analyzing={analyzing} decomposing={decomposing} />
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === 'kanban' && <KanbanBoard projectId={selectedId} />}

          {tab === 'plans' && <PlanList projectId={selectedId} />}

          <Divider style={{ margin: '24px 0', borderColor: 'rgba(255,255,255,0.05)' }} />

          {/* Agent 工作流说明 */}
          <Card size="small" style={{
            background: 'rgba(139,92,246,0.04)', borderRadius: 14,
            border: '1px solid rgba(139,92,246,0.1)', marginTop: 8,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
              <RocketOutlined style={{ color: '#8b5cf6', fontSize: 20 }} />
              <div style={{ flex: 1 }}>
                <Text strong style={{ color: '#a78bfa', fontSize: 13 }}>Agent 工作流</Text>
                <Text style={{ color: '#506380', fontSize: 12, display: 'block', marginTop: 2 }}>
                  1. 创建需求 → 2. 「Agent 评审」自动打分 → 3. 通过后「拆解为任务」→ 4. 在「敏捷看板」跟踪任务进展
                </Text>
              </div>
              <Space size={4}>
                {[1, 2, 3, 4].map(i => (
                  <span key={i} style={{
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    width: 24, height: 24, borderRadius: 12,
                    background: 'rgba(139,92,246,0.2)', color: '#a78bfa',
                    fontSize: 11, fontWeight: 700,
                  }}>{i}</span>
                ))}
                <ArrowRightOutlined style={{ color: '#506380' }} />
                <CheckCircleOutlined style={{ color: '#34d399' }} />
              </Space>
            </div>
          </Card>
        </>
      )}

      {/* 弹窗 */}
      <ProjectModal open={projectModalOpen} editing={editingProject}
        onClose={() => setProjectModalOpen(false)} onSuccess={fetchProjects} />
      <RequirementModal open={reqModalOpen} editing={editingReq} projectId={selectedId}
        onClose={() => setReqModalOpen(false)} onSuccess={fetchRequirements} />
    </div>
  );
}
