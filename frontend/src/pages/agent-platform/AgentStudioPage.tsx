import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Collapse,
  Descriptions,
  Divider,
  Flex,
  Form,
  Input,
  InputNumber,
  Progress,
  Radio,
  Segmented,
  Select,
  Slider,
  Space,
  Steps,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  AppstoreOutlined,
  AuditOutlined,
  CodeOutlined,
  ExperimentOutlined,
  MessageOutlined,
  NodeIndexOutlined,
  ReloadOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { agentPlatformService } from '../../services/agentPlatform.service';
import type { AgentStudioConfig, ComputeNode, NodeInventory } from './types';
import { defaultStudioConfig, normalizeStudioConfig } from './types';
import { evaluateDraftSave, evaluateStudioCompleteness } from './domain';
import { PlatformPageHeader } from './components';

const { Text, Paragraph, Title } = Typography;

const studioSteps = [
  { title: '目标', description: '目标与成功标准', icon: <AuditOutlined /> },
  { title: '角色', description: '指令与输出格式', icon: <MessageOutlined /> },
  { title: '模型', description: '模型与上下文', icon: <AppstoreOutlined /> },
  { title: '能力', description: '运行环境、Skill 与 MCP', icon: <ToolOutlined /> },
  { title: '协作', description: '子 Agent 拓扑', icon: <NodeIndexOutlined /> },
  { title: 'Loop', description: 'Loop 与 SOP', icon: <ReloadOutlined /> },
  { title: 'Hook', description: '生命周期扩展点', icon: <CodeOutlined /> },
  { title: 'Eval', description: '评估与发布门禁', icon: <ExperimentOutlined /> },
  { title: '护栏', description: '边界与审批', icon: <SafetyCertificateOutlined /> },
  { title: '发布', description: '确认配置并发布上线', icon: <RocketOutlined /> },
];

/** 快速模式只走核心 5 步，其余使用默认配置 */
const QUICK_STEP_FLOW = [0, 1, 2, 3, 9];

const lines = (value: string) => value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);

export interface AgentStudioPageProps {
  agentId?: number;
  initialConfig?: AgentStudioConfig;
  onVersionSaved?: (agentId: number, versionId: number) => void;
}

export default function AgentStudioPage({
  agentId: agentIdProp,
  initialConfig,
  onVersionSaved,
}: AgentStudioPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const routeAgentId = id && id !== 'new' ? Number(id) : undefined;
  const agentId = agentIdProp ?? (Number.isFinite(routeAgentId) ? routeAgentId : undefined);
  const [current, setCurrent] = useState(0);
  const [mode, setMode] = useState<'quick' | 'expert'>('quick');
  const [config, setConfig] = useState<AgentStudioConfig>(initialConfig ?? defaultStudioConfig());
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [savedAgentId, setSavedAgentId] = useState<number | null>(agentId ?? null);
  const [savedVersionId, setSavedVersionId] = useState<number | null>(null);
  const [publishedVersion, setPublishedVersion] = useState<number | null>(null);
  const [isPublished, setIsPublished] = useState(false);
  const [nodes, setNodes] = useState<ComputeNode[]>([]);
  const [runtimeInventory, setRuntimeInventory] = useState<NodeInventory | null>(null);
  const completeness = useMemo(() => evaluateStudioCompleteness(config), [config]);
  const stepFlow = useMemo(
    () => (mode === 'quick' ? QUICK_STEP_FLOW : studioSteps.map((_, index) => index)),
    [mode],
  );
  const flowIndex = Math.max(0, stepFlow.indexOf(current));
  const isLastStep = flowIndex >= stepFlow.length - 1;

  useEffect(() => {
    setCurrent((prev) => (stepFlow.includes(prev) ? prev : stepFlow[0] ?? 0));
  }, [mode, stepFlow]);

  const goNext = () => {
    if (current === 0 && !config.objective.name.trim()) {
      message.warning('请先填写 Agent 名称');
      return;
    }
    if (isLastStep) return;
    setCurrent(stepFlow[flowIndex + 1] ?? current);
  };

  const goToPublishStep = () => {
    setCurrent(9);
  };

  const goPrev = () => {
    if (flowIndex <= 0) return;
    setCurrent(stepFlow[flowIndex - 1] ?? 0);
  };

  useEffect(() => {
    if (!agentId) return;
    void agentPlatformService.getAgent(agentId).then((agent) => {
      setSavedAgentId(agent.id);
      setIsPublished(agent.is_published);
      setPublishedVersion(agent.is_published ? agent.version : null);
    }).catch(() => undefined);
  }, [agentId]);

  useEffect(() => {
    void (async () => {
      try {
        await agentPlatformService.registerLocalNode();
        const nodeList = await agentPlatformService.listNodes();
        setNodes(nodeList);
        if (!config.runtime.node_id) {
          const localNode =
            nodeList.find((node) => node.connection.connector_type === 'local') ?? nodeList[0];
          if (localNode) {
            setConfig((previous) => ({
              ...previous,
              runtime: { ...previous.runtime, node_id: localNode.id },
            }));
          }
        }
      } catch {
        // 节点列表失败不阻塞 Studio 编辑
      }
    })();
  }, []);

  useEffect(() => {
    if (!config.runtime.node_id) {
      setRuntimeInventory(null);
      return;
    }
    void agentPlatformService
      .getNodeInventory(config.runtime.node_id, false)
      .then(setRuntimeInventory)
      .catch(() => setRuntimeInventory(null));
  }, [config.runtime.node_id]);

  useEffect(() => {
    if (!runtimeInventory?.containers[0] || config.runtime.container_id) return;
    const container = runtimeInventory.containers[0];
    setConfig((previous) => ({
      ...previous,
      runtime: {
        ...previous.runtime,
        container_id: container.id,
        managed_root: container.managed_roots[0] ?? null,
        config_path: container.config_path,
      },
    }));
  }, [runtimeInventory, config.runtime.container_id]);

  const patch = <K extends keyof AgentStudioConfig>(
    section: K,
    value: Partial<AgentStudioConfig[K]>,
  ) => setConfig((previous) => ({
    ...previous,
    [section]: { ...previous[section], ...value },
  }));

  const persistDraft = async () => {
    const draftCheck = evaluateDraftSave(config);
    if (!draftCheck.ok) throw new Error(draftCheck.reason);
    const payload = normalizeStudioConfig(config);
    setConfig(payload);
    const targetAgentId = agentId ?? savedAgentId;
    if (!targetAgentId) {
      const created = await agentPlatformService.createAgent({
        name: payload.objective.name,
        type: 'custom_looper',
        description: payload.objective.problem,
        config: payload,
        version_note: payload.release.change_summary,
      });
      setSavedAgentId(created.id);
      setSavedVersionId(created.latest_version.id);
      navigate(`/agent-platform/agents/${created.id}/studio`, { replace: true });
      onVersionSaved?.(created.id, created.latest_version.id);
      return {
        agentId: created.id,
        versionId: created.latest_version.id,
        versionNumber: created.latest_version.version_number,
      };
    }
    const version = await agentPlatformService.createAgentVersion(targetAgentId, {
      config: payload,
      note: payload.release.change_summary,
    });
    setSavedVersionId(version.id);
    onVersionSaved?.(targetAgentId, version.id);
    return {
      agentId: targetAgentId,
      versionId: version.id,
      versionNumber: version.version_number,
    };
  };

  const save = async () => {
    setSaving(true);
    try {
      const result = await persistDraft();
      message.success(`草稿 v${result.versionNumber} 已保存`);
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '保存草稿失败');
    } finally {
      setSaving(false);
    }
  };

  const publish = async () => {
    setPublishing(true);
    try {
      const result = await persistDraft();
      await agentPlatformService.publishAgentVersion(result.agentId, result.versionId);
      setIsPublished(true);
      setPublishedVersion(result.versionNumber);
      message.success(`Agent 已发布 v${result.versionNumber}，可在对话工作台使用`);
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '发布失败');
    } finally {
      setPublishing(false);
    }
  };

  const content = (() => {
    switch (current) {
      case 0:
        return (
          <Form layout="vertical">
            <Alert
              type="info"
              showIcon
              message="保存草稿只需填写名称与问题；模型、Loop、护栏、Eval、Hook 等会使用默认配置，可在专家模式中调整。"
              style={{ marginBottom: 16 }}
            />
            <Form.Item label="Agent 名称" required>
              <Input value={config.objective.name} onChange={(event) => patch('objective', { name: event.target.value })} />
            </Form.Item>
            <Form.Item label="要解决的问题" required>
              <Input.TextArea rows={3} value={config.objective.problem} onChange={(event) => patch('objective', { problem: event.target.value })} />
            </Form.Item>
            <Form.Item label="成功标准（每行一条，可选）">
              <Input.TextArea rows={4} value={config.objective.success_criteria.join('\n')} onChange={(event) => patch('objective', { success_criteria: lines(event.target.value) })} />
            </Form.Item>
            <Form.Item label="明确不做（每行一条）">
              <Input.TextArea rows={3} value={config.objective.exclusions.join('\n')} onChange={(event) => patch('objective', { exclusions: lines(event.target.value) })} />
            </Form.Item>
          </Form>
        );
      case 1:
        return (
          <Form layout="vertical">
            <Form.Item label="系统指令">
              <Input.TextArea rows={10} value={config.role.system_prompt} onChange={(event) => patch('role', { system_prompt: event.target.value })} placeholder="定义职责、决策边界、证据要求与沟通方式" />
            </Form.Item>
            <Form.Item label="输出格式">
              <Input.TextArea rows={4} value={config.role.output_format} onChange={(event) => patch('role', { output_format: event.target.value })} />
            </Form.Item>
          </Form>
        );
      case 2:
        return (
          <Form layout="vertical">
            <Form.Item label="模型 ID">
              <Input value={config.model.model_id} onChange={(event) => patch('model', { model_id: event.target.value })} placeholder="选择或输入平台可用模型" />
            </Form.Item>
            <Form.Item label={`Temperature · ${config.model.temperature}`}>
              <Slider min={0} max={2} step={0.1} value={config.model.temperature} onChange={(value) => patch('model', { temperature: value })} />
            </Form.Item>
            <Form.Item label="上下文策略">
              <Select value={config.model.context_policy} onChange={(value) => patch('model', { context_policy: value })} options={[
                { value: 'turn', label: '仅当前轮' },
                { value: 'session', label: '会话上下文' },
                { value: 'retrieval', label: '会话 + 检索' },
              ]} />
            </Form.Item>
          </Form>
        );
      case 3:
        return (
          <Form layout="vertical">
            <Alert
              type="info"
              showIcon
              message="先选择 Agent 运行在哪台计算节点、哪个 OpenCode 容器上，再绑定 Skill / MCP。"
              style={{ marginBottom: 16 }}
            />
            <Form.Item label="运行节点">
              <Select
                placeholder="选择计算节点"
                value={config.runtime.node_id ?? undefined}
                options={nodes.map((node) => ({
                  value: node.id,
                  label: `${node.name} (${node.connection.connector_type})`,
                }))}
                onChange={(nodeId) => patch('runtime', {
                  node_id: nodeId,
                  container_id: null,
                  managed_root: null,
                  config_path: null,
                })}
              />
            </Form.Item>
            {runtimeInventory?.containers[0] ? (
              <Card size="small" title="OpenCode 容器" style={{ marginBottom: 16 }}>
                <Descriptions size="small" column={1} items={[
                  { key: 'status', label: '状态', children: runtimeInventory.containers[0].status },
                  { key: 'cli', label: 'CLI', children: runtimeInventory.containers[0].cli_path || '未检测到' },
                  { key: 'config', label: '配置文件', children: runtimeInventory.containers[0].config_path || '-' },
                  { key: 'root', label: '受管目录', children: runtimeInventory.containers[0].managed_roots.join(', ') },
                ]} />
                {config.runtime.container_id === runtimeInventory.containers[0].id ? (
                  <Alert type="success" showIcon message="已绑定此 OpenCode 实例" style={{ marginTop: 8 }} />
                ) : (
                  <Button
                    type="primary"
                    style={{ marginTop: 8 }}
                    onClick={() => patch('runtime', {
                      container_id: runtimeInventory.containers[0].id,
                      managed_root: runtimeInventory.containers[0].managed_roots[0] ?? null,
                      config_path: runtimeInventory.containers[0].config_path,
                    })}
                  >
                    绑定此 OpenCode 实例
                  </Button>
                )}
                {runtimeInventory.containers[0].config_preview ? (
                  <Collapse
                    ghost
                    style={{ marginTop: 8 }}
                    items={[{
                      key: 'config',
                      label: '查看 opencode.json 预览',
                      children: (
                        <pre style={{ margin: 0, maxHeight: 160, overflow: 'auto', fontSize: 12 }}>
                          {JSON.stringify(runtimeInventory.containers[0].config_preview, null, 2)}
                        </pre>
                      ),
                    }]}
                  />
                ) : null}
              </Card>
            ) : config.runtime.node_id ? (
              <Alert type="warning" showIcon message="该节点尚未发现 OpenCode 运行时" style={{ marginBottom: 16 }} />
            ) : null}
            <Form.Item label="Skill（从 OpenCode 发现结果选择）">
              <Select
                mode="multiple"
                placeholder="选择 Skill"
                value={config.capabilities.skill_ids}
                options={(runtimeInventory?.resources.skills ?? []).map((item) => ({
                  value: item.external_key,
                  label: `${item.external_key} · ${item.location}`,
                }))}
                onChange={(value) => patch('capabilities', { skill_ids: value })}
              />
            </Form.Item>
            <Form.Item label="MCP（从 OpenCode 发现结果选择）">
              <Select
                mode="multiple"
                placeholder="选择 MCP"
                value={config.capabilities.mcp_ids}
                options={(runtimeInventory?.resources.mcps ?? []).map((item) => ({
                  value: item.external_key,
                  label: `${item.external_key} · ${item.location}`,
                }))}
                onChange={(value) => patch('capabilities', { mcp_ids: value })}
              />
            </Form.Item>
            <Form.Item label="Skill IDs（手动补充，每行一个）">
              <Input.TextArea rows={4} value={config.capabilities.skill_ids.join('\n')} onChange={(event) => patch('capabilities', { skill_ids: lines(event.target.value) })} />
            </Form.Item>
            <Form.Item label="MCP IDs（手动补充，每行一个）">
              <Input.TextArea rows={4} value={config.capabilities.mcp_ids.join('\n')} onChange={(event) => patch('capabilities', { mcp_ids: lines(event.target.value) })} />
            </Form.Item>
          </Form>
        );
      case 4:
        return (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert type="info" showIcon message="先选择协作模式，再声明参与者与角色。" />
            <Radio.Group value={config.collaboration.mode} onChange={(event) => patch('collaboration', { mode: event.target.value })}>
              <Space direction="vertical">
                {[
                  ['single', 'Single', '单 Agent 独立完成'],
                  ['sequential', 'Sequential', '按顺序传递结果'],
                  ['router', 'Router', '主 Agent 按任务选择专家'],
                  ['parallel', 'Parallel', '并行分析后合并'],
                  ['evaluator_optimizer', 'Evaluator-Optimizer', '评估反馈驱动修订'],
                ].map(([value, title, description]) => <Radio key={value} value={value}><Text strong>{title}</Text><Text type="secondary"> · {description}</Text></Radio>)}
              </Space>
            </Radio.Group>
            <Form layout="vertical">
              <Form.Item label="参与者（每行 agent_id:role）" required={config.collaboration.mode !== 'single'}>
                <Input.TextArea
                  rows={6}
                  disabled={config.collaboration.mode === 'single'}
                  value={config.collaboration.participants.map((item) => `${item.agent_id}:${item.role}`).join('\n')}
                  onChange={(event) => patch('collaboration', {
                    participants: lines(event.target.value).map((item) => {
                      const [agent_id, ...role] = item.split(':');
                      return { agent_id, role: role.join(':') || 'worker' };
                    }),
                  })}
                />
              </Form.Item>
            </Form>
            {config.collaboration.mode !== 'single' ? (
              <Flex gap={8} align="center" wrap>
                <Tag color="blue">主 Agent</Tag>
                {config.collaboration.participants.map((item, index) => (
                  <Space key={`${item.agent_id}-${index}`}><Text>→</Text><Card size="small"><Tag>{item.role}</Tag>{item.agent_id}</Card></Space>
                ))}
              </Flex>
            ) : null}
          </Space>
        );
      case 5:
        return (
          <Form layout="vertical">
            <Form.Item label="Loop 策略">
              <Select value={config.loop.strategy} onChange={(value) => patch('loop', { strategy: value })} options={['react', 'plan_execute', 'evaluator_optimizer', 'sop'].map((value) => ({ value, label: value }))} />
            </Form.Item>
            <Flex gap={12}>
              <Form.Item label="最大迭代" style={{ flex: 1 }}>
                <InputNumber min={1} max={100} value={config.loop.max_iterations} onChange={(value) => patch('loop', { max_iterations: value ?? 1 })} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="超时（秒）" style={{ flex: 1 }}>
                <InputNumber min={5} max={3600} value={config.loop.timeout_seconds} onChange={(value) => patch('loop', { timeout_seconds: value ?? 90 })} style={{ width: '100%' }} />
              </Form.Item>
            </Flex>
            <Form.Item label="SOP（每行 key:instruction，可选）">
              <Input.TextArea
                rows={10}
                value={config.loop.sop.map((item) => `${item.key}:${item.instruction}`).join('\n')}
                onChange={(event) => patch('loop', {
                  sop: lines(event.target.value).map((item, index) => {
                    const [key, ...instruction] = item.split(':');
                    return { key: key || `step-${index + 1}`, instruction: instruction.join(':') };
                  }),
                })}
              />
            </Form.Item>
          </Form>
        );
      case 6:
        return (
          <Form layout="vertical">
            <Alert type="warning" showIcon message="Hook 只允许平台注册的受信 Action，不接受脚本。" style={{ marginBottom: 16 }} />
            <Form.Item label="Hooks（每行 event:action_id:failure_policy）">
              <Input.TextArea
                rows={12}
                value={config.hooks.map((item) => `${item.event}:${item.action_id}:${item.failure_policy}`).join('\n')}
                onChange={(event) => setConfig((previous) => ({
                  ...previous,
                  hooks: lines(event.target.value).map((item) => {
                    const [hookEvent, action_id, policy] = item.split(':');
                    return { event: hookEvent, action_id, failure_policy: policy === 'continue' ? 'continue' : 'block' };
                  }),
                }))}
                placeholder="tool.before:sql-readonly-guard:block"
              />
            </Form.Item>
          </Form>
        );
      case 7:
        return (
          <Form layout="vertical">
            <Alert type="info" showIcon message="至少一个 Eval 必须作为发布门禁。" style={{ marginBottom: 16 }} />
            <Form.Item label="Eval（每行 suite_id:threshold:required，可选）">
              <Input.TextArea
                rows={12}
                value={config.eval_bindings.map((item) => `${item.suite_id}:${item.threshold}:${item.required}`).join('\n')}
                onChange={(event) => setConfig((previous) => ({
                  ...previous,
                  eval_bindings: lines(event.target.value).map((item) => {
                    const [suite_id, threshold, required] = item.split(':');
                    return { suite_id, threshold: Number(threshold) || 0, required: required === 'true' };
                  }),
                }))}
                placeholder="business-consistency:0.9:true"
              />
            </Form.Item>
          </Form>
        );
      case 8:
        return (
          <Form layout="vertical">
            <Form.Item label="工具审批策略">
              <Select value={config.guardrails.tool_approval} onChange={(value) => patch('guardrails', { tool_approval: value })} options={[
                { value: 'always', label: '全部审批' },
                { value: 'risk_based', label: '按风险审批' },
                { value: 'never', label: '不审批（仅低风险场景）' },
              ]} />
            </Form.Item>
            <Form.Item label="单次 Run 最大工具调用">
              <InputNumber min={1} max={1000} value={config.guardrails.max_tool_calls} onChange={(value) => patch('guardrails', { max_tool_calls: value ?? 1 })} />
            </Form.Item>
            <Form.Item label="禁止动作（每行一条，可选）">
              <Input.TextArea rows={6} value={config.guardrails.forbidden_actions.join('\n')} onChange={(event) => patch('guardrails', { forbidden_actions: lines(event.target.value) })} />
            </Form.Item>
            <Form.Item label="PII 脱敏">
              <Switch checked={config.guardrails.pii_redaction} onChange={(value) => patch('guardrails', { pii_redaction: value })} />
            </Form.Item>
          </Form>
        );
      case 9:
        return (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              type="info"
              showIcon
              icon={<RocketOutlined />}
              message="发布到对话工作台"
              description="保存草稿仅写入版本快照；点击「发布上线」后，Agent 会出现在「对话工作台」供团队使用。"
            />
            {isPublished ? (
              <Alert
                type="success"
                showIcon
                message={`当前已发布 v${publishedVersion ?? '-'}`}
                description="修改配置后需再次发布，才会更新对话工作台中的 Agent。"
              />
            ) : (
              <Alert type="warning" showIcon message="尚未发布" description="完成配置后点击「发布上线」。" />
            )}
            <Descriptions
              bordered
              size="small"
              column={1}
              items={[
                { key: 'name', label: 'Agent', children: config.objective.name || '-' },
                { key: 'model', label: '模型', children: config.model.model_id || '默认模型' },
                {
                  key: 'node',
                  label: '运行节点',
                  children: nodes.find((node) => node.id === config.runtime.node_id)?.name ?? '本机（自动）',
                },
                {
                  key: 'skills',
                  label: 'Skill',
                  children: config.capabilities.skill_ids.length
                    ? config.capabilities.skill_ids.join(', ')
                    : '无（可选）',
                },
                {
                  key: 'mcps',
                  label: 'MCP',
                  children: config.capabilities.mcp_ids.length
                    ? config.capabilities.mcp_ids.join(', ')
                    : '无（可选）',
                },
              ]}
            />
            <Form layout="vertical">
              <Form.Item label="版本变更摘要">
                <Input.TextArea
                  maxLength={256}
                  rows={4}
                  value={config.release.change_summary}
                  onChange={(event) => patch('release', { change_summary: event.target.value })}
                />
              </Form.Item>
            </Form>
            <Space wrap>
              <Button loading={saving} onClick={() => void save()}>保存草稿</Button>
              <Button type="primary" icon={<RocketOutlined />} loading={publishing} onClick={() => void publish()}>
                发布上线
              </Button>
              {isPublished ? (
                <Button onClick={() => navigate('/workspace')}>前往对话工作台</Button>
              ) : null}
            </Space>
          </Space>
        );
      default:
        return null;
    }
  })();

  return (
    <div style={{ minWidth: 1040 }}>
      <PlatformPageHeader
        title="Agent Studio"
        subtitle={agentId ? `编辑 Agent ${agentId}` : '创建新的 Agent 与不可变版本'}
        extra={
          <Space wrap>
            <Segmented value={mode} onChange={(value) => setMode(value as 'quick' | 'expert')} options={[{ value: 'quick', label: '快速模式' }, { value: 'expert', label: '专家模式' }]} />
            {isPublished ? (
              <Tag color="success">已发布 v{publishedVersion ?? '-'}</Tag>
            ) : (
              <Tag>未发布</Tag>
            )}
            {!isLastStep && current !== 9 ? (
              <Button onClick={goToPublishStep}>前往发布</Button>
            ) : null}
            <Button loading={saving} onClick={() => void save()}>保存草稿</Button>
            <Button type="primary" icon={<RocketOutlined />} loading={publishing} onClick={() => void publish()}>
              发布上线
            </Button>
          </Space>
        }
      />
      <div style={{ display: 'grid', gridTemplateColumns: '270px minmax(500px, 1fr) 280px', gap: 16, alignItems: 'start' }}>
        <Card title={mode === 'quick' ? '快速配置（5 步）' : '十步设计方法'}>
          <Steps
            direction="vertical"
            current={flowIndex}
            onChange={(index) => setCurrent(stepFlow[index] ?? 0)}
            items={stepFlow.map((stepIndex) => ({
              ...studioSteps[stepIndex],
              status: completeness.sections[stepIndex]?.complete ? 'finish' : undefined,
            }))}
          />
          {mode === 'quick' ? (
            <Alert
              type="info"
              showIcon
              style={{ marginTop: 16 }}
              message="快速模式"
              description="Loop / Hook / Eval / 护栏等使用默认配置；第 5 步「发布」可保存并上线到对话工作台。"
            />
          ) : null}
        </Card>
        <Card
          title={`第 ${flowIndex + 1} 步 · ${studioSteps[current].title}`}
          extra={<Tag color="blue">{mode === 'quick' ? '快速模式' : '专家模式'}</Tag>}
          styles={{
            body: {
              display: 'flex',
              flexDirection: 'column',
              padding: 0,
              maxHeight: 'calc(100vh - 180px)',
            },
          }}
        >
          <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px' }}>
            {content}
            {mode === 'expert' ? (
              <>
                <Divider />
                <Alert type="info" message="专家模式" description="当前配置会完整写入 config_snapshot；Provider 扩展字段由后端 schema 校验。" />
              </>
            ) : null}
          </div>
          <div
            style={{
              position: 'sticky',
              bottom: 0,
              zIndex: 2,
              borderTop: '1px solid rgba(148, 163, 184, 0.18)',
              background: 'var(--ant-color-bg-container, #0f172a)',
              padding: '12px 24px',
            }}
          >
            <Flex justify="space-between" style={{ width: '100%' }}>
              <Button disabled={flowIndex === 0} onClick={goPrev}>上一步</Button>
              {isLastStep ? (
                <Space>
                  <Button loading={saving} onClick={() => void save()}>保存草稿</Button>
                  <Button type="primary" icon={<RocketOutlined />} loading={publishing} onClick={() => void publish()}>
                    发布上线
                  </Button>
                </Space>
              ) : (
                <Button type="primary" onClick={goNext}>下一步</Button>
              )}
            </Flex>
          </div>
        </Card>
        <Card title="配置完整度">
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Progress type="circle" percent={completeness.percent} />
            <Title level={5} style={{ margin: 0 }}>{studioSteps[current].title}</Title>
            <Paragraph type="secondary">{studioSteps[current].description}。快速模式聚焦必要配置，专家模式用于精确调参和 Provider 扩展。</Paragraph>
            <Divider style={{ margin: 0 }} />
            {completeness.sections.map((section) => (
              <Flex key={section.key} justify="space-between">
                <Text>{section.label}</Text>
                <Checkbox checked={section.complete} />
              </Flex>
            ))}
          </Space>
        </Card>
      </div>
    </div>
  );
}
