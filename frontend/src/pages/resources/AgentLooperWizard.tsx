import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Steps, Form, Input, Select, InputNumber, Switch, Button, Space, Typography,
  Card, Row, Col, Divider, Tooltip, App as AntApp,
} from 'antd';
import {
  ArrowLeftOutlined, ArrowRightOutlined, CheckCircleOutlined,
  PlusOutlined, DeleteOutlined, PlayCircleOutlined,
} from '@ant-design/icons';
import { PageHeader, GlassPanel } from '../../components/common';
import { agentLooperService } from '../../services/agentLooper.service';
import {
  EMPTY_CONFIG, PRESETS, findPreset,
} from '../../presets/agentLoopers';
import type {
  AgentLooperConfig, AgentLooperType, LoopStrategy, CustomTool,
} from '../../presets/agentLoopers';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const LOOP_STRATEGY_OPTIONS: { value: LoopStrategy; label: string; hint: string }[] = [
  { value: 'single_shot',  label: 'single_shot — 单次响应',      hint: '一次调用即返回，适合直接问答/单步生成。' },
  { value: 'react',        label: 'react — 思考→工具→观察循环', hint: 'ReAct 范式，每轮先思考、再选工具、再观察结果。' },
  { value: 'plan_execute', label: 'plan_execute — 先规划再执行', hint: '先生成计划，再顺序执行子步骤。' },
  { value: 'reflect',      label: 'reflect — 自我反思修正',       hint: '产出后自评并修正，适合审核/质检类任务。' },
];

interface Step1Values {
  name: string;
  description?: string;
  type: AgentLooperType;
  presetKey?: string;
}

interface AgentLooperWizardProps {
  /** Test hook: skip navigate side-effect. */
  onCreated?: (id: number) => void;
}

export default function AgentLooperWizard({ onCreated }: AgentLooperWizardProps = {}) {
  const navigate = useNavigate();
  const { message } = AntApp.useApp();

  const [current, setCurrent] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  // Step 1 meta
  const [meta, setMeta] = useState<Step1Values>({
    name: '',
    description: '',
    type: 'custom_looper',
    presetKey: undefined,
  });

  // Steps 2-3 config
  const [config, setConfig] = useState<AgentLooperConfig>({ ...EMPTY_CONFIG });

  // Step 4
  const [testPrompt, setTestPrompt] = useState('你好，请介绍一下你自己');

  const updateConfig = <K extends keyof AgentLooperConfig>(k: K, v: AgentLooperConfig[K]) => {
    setConfig((prev) => ({ ...prev, [k]: v }));
  };

  const pickPreset = (key: string) => {
    const preset = findPreset(key);
    if (!preset) return;
    setMeta((prev) => ({ ...prev, presetKey: key }));
    // Deep clone so subsequent edits don't mutate the preset constant.
    setConfig({
      ...preset.config,
      tool_permissions: { ...preset.config.tool_permissions },
      custom_tools: preset.config.custom_tools.map((t) => ({ ...t })),
      guardrails: { ...preset.config.guardrails },
      resource_bindings: preset.config.resource_bindings ? { ...preset.config.resource_bindings } : null,
    });
    message.success(`已应用模板：${preset.name}`);
  };

  const canGoNext = useMemo(() => {
    if (current === 0) return meta.name.trim().length > 0;
    return true;
  }, [current, meta.name]);

  const onNext = () => setCurrent((c) => Math.min(c + 1, 3));
  const onBack = () => setCurrent((c) => Math.max(c - 1, 0));

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Preview test skipped for now (backend endpoint not available)
      setTestResult('暂不可用：后端 preview-test 接口尚未部署，可先完成注册后到详情页测试。');
    } finally {
      setTesting(false);
    }
  };

  const onFinish = async () => {
    if (!meta.name.trim()) {
      message.error('请填写 Agent 名称');
      setCurrent(0);
      return;
    }
    setSubmitting(true);
    try {
      const created = await agentLooperService.create({
        name: meta.name.trim() || '未命名 Agent',
        type: meta.type,
        description: meta.description || null,
        config_json: config,
      });
      message.success('Agent Looper 注册成功');
      if (onCreated) {
        onCreated(created.id);
      } else if (created?.id) {
        navigate(`/resources/agent-looper/${created.id}`);
      }
    } catch (err) {
      message.error(`注册失败：${(err as Error).message ?? '未知错误'}`);
    } finally {
      setSubmitting(false);
    }
  };

  // ---- Step contents

  const step1 = (
    <GlassPanel style={{ padding: 24 }}>
      <Form layout="vertical">
        <Form.Item label="名称" required>
          <Input
            data-testid="wizard-name"
            placeholder="例如：数据分析师-北美线"
            value={meta.name}
            onChange={(e) => setMeta({ ...meta, name: e.target.value })}
            maxLength={128}
          />
        </Form.Item>
        <Form.Item label="描述">
          <TextArea
            data-testid="wizard-description"
            rows={3}
            placeholder="用途、面向的资源范围、启用场景"
            value={meta.description}
            onChange={(e) => setMeta({ ...meta, description: e.target.value })}
          />
        </Form.Item>
        <Form.Item label="类型">
          <Select
            value={meta.type}
            onChange={(v) => setMeta({ ...meta, type: v as AgentLooperType })}
            options={[
              { value: 'custom_looper',   label: 'custom_looper — 自定义循环（推荐）' },
              { value: 'opencode_native', label: 'opencode_native — OpenCode 原生' },
              { value: 'mcp_agent',       label: 'mcp_agent — MCP 智能体' },
              { value: 'imported',        label: 'imported — 外部导入' },
            ]}
          />
        </Form.Item>
      </Form>

      <Divider style={{ margin: '20px 0 16px' }} />
      <Text strong style={{ fontSize: 14 }}>选择模板（可选）</Text>
      <Paragraph type="secondary" style={{ marginTop: 4, marginBottom: 12 }}>
        选择一个预设模板会填充能力/提示词/护栏；后续步骤仍可修改。
      </Paragraph>
      <Row gutter={[12, 12]}>
        {PRESETS.map((p) => {
          const selected = meta.presetKey === p.key;
          return (
            <Col xs={24} sm={12} md={12} lg={6} key={p.key}>
              <Card
                hoverable
                data-testid={`preset-card-${p.key}`}
                onClick={() => pickPreset(p.key)}
                style={{
                  borderRadius: 12,
                  border: selected
                    ? '1px solid rgba(59,130,246,0.55)'
                    : '1px solid rgba(255,255,255,0.06)',
                  background: selected
                    ? 'rgba(59,130,246,0.08)'
                    : 'rgba(255,255,255,0.015)',
                  transition: 'all .2s',
                }}
                styles={{ body: { padding: 14 } }}
              >
                <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                  <Text strong>{p.name}</Text>
                  <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.5 }}>
                    {p.description}
                  </Text>
                  <Space size={8} style={{ marginTop: 6 }}>
                    <Text style={{ fontSize: 11, color: '#60a5fa' }}>
                      {p.config.loop_strategy}
                    </Text>
                    <Text style={{ fontSize: 11, color: '#8895b4' }}>
                      T={p.config.temperature}
                    </Text>
                  </Space>
                </Space>
              </Card>
            </Col>
          );
        })}
      </Row>
    </GlassPanel>
  );

  const toolPerms = config.tool_permissions;
  const step2 = (
    <GlassPanel style={{ padding: 24 }}>
      <Form layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="模型 (model)">
              <Select
                data-testid="wizard-model"
                placeholder="agent-plan/ark-code-latest"
                value={config.model || undefined}
                onChange={(v) => updateConfig('model', v)}
                showSearch
                allowClear
                style={{ width: '100%' }}
              >
                <Select.Option value="agent-plan/ark-code-latest">agent-plan/ark-code-latest</Select.Option>
                <Select.Option value="doubao-seed-2-0-pro-260215">doubao-seed-2-0-pro-260215</Select.Option>
                <Select.Option value="doubao-seed-2-0-code-preview-260215">doubao-seed-2-0-code-preview-260215</Select.Option>
                <Select.Option value="gpt-4o">gpt-4o</Select.Option>
                <Select.Option value="claude-sonnet-4-20250514">claude-sonnet-4-20250514</Select.Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="温度 (temperature)">
              <InputNumber
                aria-label="temperature"
                data-testid="wizard-temperature"
                min={0}
                max={2}
                step={0.1}
                value={config.temperature}
                onChange={(v) => updateConfig('temperature', (v ?? 0.7) as number)}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item label="循环策略 (loop_strategy)">
          <Select
            value={config.loop_strategy}
            onChange={(v) => updateConfig('loop_strategy', v)}
            optionRender={(opt) => {
              const meta_ = LOOP_STRATEGY_OPTIONS.find((o) => o.value === opt.value);
              return (
                <Tooltip title={meta_?.hint} placement="right">
                  <span>{opt.label}</span>
                </Tooltip>
              );
            }}
            options={LOOP_STRATEGY_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
          />
        </Form.Item>

        <Divider style={{ margin: '8px 0 12px' }}>工具权限</Divider>
        <Row gutter={16}>
          {(['edit', 'webfetch', 'bash', 'websearch'] as const).map((k) => (
            <Col span={6} key={k}>
              <Space>
                <Switch
                  data-testid={`toolperm-${k}`}
                  checked={Boolean(toolPerms[k])}
                  onChange={(v) => updateConfig('tool_permissions', { ...toolPerms, [k]: v })}
                />
                <Text>{k}</Text>
              </Space>
            </Col>
          ))}
        </Row>

        <Divider style={{ margin: '20px 0 12px' }}>自定义工具</Divider>
        {config.custom_tools.map((t, idx) => (
          <Card
            key={idx}
            size="small"
            style={{ marginBottom: 10, background: 'rgba(255,255,255,0.02)' }}
            title={`工具 ${idx + 1}`}
            extra={
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => {
                  const next = config.custom_tools.slice();
                  next.splice(idx, 1);
                  updateConfig('custom_tools', next);
                }}
              />
            }
          >
            <Form.Item label="name" style={{ marginBottom: 8 }}>
              <Input
                value={t.name}
                onChange={(e) => {
                  const next = config.custom_tools.slice();
                  next[idx] = { ...t, name: e.target.value };
                  updateConfig('custom_tools', next);
                }}
              />
            </Form.Item>
            <Form.Item label="description" style={{ marginBottom: 8 }}>
              <Input
                value={t.description}
                onChange={(e) => {
                  const next = config.custom_tools.slice();
                  next[idx] = { ...t, description: e.target.value };
                  updateConfig('custom_tools', next);
                }}
              />
            </Form.Item>
            <Form.Item label="params_schema (JSON)" style={{ marginBottom: 0 }}>
              <TextArea
                rows={3}
                value={JSON.stringify(t.params_schema, null, 2)}
                onChange={(e) => {
                  try {
                    const parsed = JSON.parse(e.target.value) as Record<string, unknown>;
                    const next = config.custom_tools.slice();
                    next[idx] = { ...t, params_schema: parsed };
                    updateConfig('custom_tools', next);
                  } catch {
                    // Ignore parse errors while user is typing.
                  }
                }}
              />
            </Form.Item>
          </Card>
        ))}
        <Button
          type="dashed"
          block
          icon={<PlusOutlined />}
          onClick={() => {
            const next: CustomTool = { name: '', description: '', params_schema: {} };
            updateConfig('custom_tools', [...config.custom_tools, next]);
          }}
        >
          添加自定义工具
        </Button>

        <Divider style={{ margin: '20px 0 12px' }} />
        <Form.Item label="记忆窗口 (memory_window)" tooltip="0 表示不启用记忆">
          <InputNumber
            min={0}
            max={100}
            value={config.memory_window}
            onChange={(v) => updateConfig('memory_window', (v ?? 0) as number)}
            style={{ width: 200 }}
          />
        </Form.Item>
      </Form>
    </GlassPanel>
  );

  const yamlPreview = useMemo(() => {
    const perms = Object.entries(config.tool_permissions)
      .filter(([, v]) => v)
      .map(([k]) => `  - ${k}`)
      .join('\n');
    return [
      '---',
      `mode: ${config.mode}`,
      `model: ${config.model || '<待填>'}`,
      `temperature: ${config.temperature}`,
      `loop_strategy: ${config.loop_strategy}`,
      `memory_window: ${config.memory_window}`,
      'tools:',
      perms || '  <none>',
      `max_tokens: ${config.guardrails.max_tokens}`,
      `max_iterations: ${config.guardrails.max_iterations}`,
      `timeout_ms: ${config.guardrails.timeout_ms}`,
      '---',
      config.system_prompt || '# system prompt 尚未填写',
    ].join('\n');
  }, [config]);

  const [showPreview, setShowPreview] = useState(false);

  const step3 = (
    <GlassPanel style={{ padding: 24 }}>
      <Form layout="vertical">
        <Form.Item label="系统提示词 (system_prompt)">
          <TextArea
            data-testid="wizard-system-prompt"
            rows={15}
            value={config.system_prompt}
            onChange={(e) => updateConfig('system_prompt', e.target.value)}
            style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 13 }}
            placeholder="定义 Agent 的身份、职责、行为约束、输出规范…"
          />
        </Form.Item>

        <Divider style={{ margin: '8px 0 12px' }}>护栏 (guardrails)</Divider>
        <Row gutter={16}>
          <Col span={8}>
            <Form.Item label="max_tokens">
              <InputNumber
                min={128}
                max={131072}
                value={config.guardrails.max_tokens}
                onChange={(v) =>
                  updateConfig('guardrails', { ...config.guardrails, max_tokens: (v ?? 4096) as number })
                }
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="max_iterations">
              <InputNumber
                min={1}
                max={100}
                value={config.guardrails.max_iterations}
                onChange={(v) =>
                  updateConfig('guardrails', { ...config.guardrails, max_iterations: (v ?? 5) as number })
                }
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label="timeout_ms">
              <InputNumber
                min={1000}
                max={600000}
                step={1000}
                value={config.guardrails.timeout_ms}
                onChange={(v) =>
                  updateConfig('guardrails', { ...config.guardrails, timeout_ms: (v ?? 30000) as number })
                }
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
        </Row>

        <Button onClick={() => setShowPreview((s) => !s)}>
          {showPreview ? '隐藏预览' : '预览 YAML frontmatter'}
        </Button>
        {showPreview && (
          <pre
            data-testid="wizard-yaml-preview"
            style={{
              marginTop: 12,
              padding: 12,
              background: 'rgba(0,0,0,0.35)',
              borderRadius: 8,
              fontSize: 12,
              lineHeight: 1.55,
              color: '#cbd5e1',
              maxHeight: 320,
              overflow: 'auto',
            }}
          >
            {yamlPreview}
          </pre>
        )}
      </Form>
    </GlassPanel>
  );

  const step4 = (
    <GlassPanel style={{ padding: 24 }}>
      <Form layout="vertical">
        <Form.Item label="测试提示词">
          <TextArea
            data-testid="wizard-test-prompt"
            rows={4}
            value={testPrompt}
            onChange={(e) => setTestPrompt(e.target.value)}
          />
        </Form.Item>
        <Space>
          <Button
            icon={<PlayCircleOutlined />}
            onClick={runTest}
            loading={testing}
            data-testid="wizard-run-test"
          >
            运行测试
          </Button>
          <Text type="secondary" style={{ fontSize: 12 }}>
            后端 preview-test 未部署时会显示“暂不可用”，不影响完成注册。
          </Text>
        </Space>
        {testResult && (
          <pre
            data-testid="wizard-test-result"
            style={{
              marginTop: 12,
              padding: 12,
              background: 'rgba(0,0,0,0.35)',
              borderRadius: 8,
              fontSize: 12,
              lineHeight: 1.6,
              color: '#cbd5e1',
              maxHeight: 240,
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {testResult}
          </pre>
        )}
      </Form>
    </GlassPanel>
  );

  const stepBody = [step1, step2, step3, step4][current];

  return (
    <div style={{ padding: '0 4px 40px', maxWidth: 1080, margin: '0 auto' }}>
      <PageHeader
        title="注册 Agent Looper"
        subtitle="4 步向导：定位 → 能力 → 系统提示词 → 联通测试"
      />

      <GlassPanel style={{ padding: '20px 24px', marginBottom: 16 }}>
        <Steps
          current={current}
          items={[
            { title: '定位' },
            { title: '能力' },
            { title: '系统提示词' },
            { title: '联通测试' },
          ]}
        />
      </GlassPanel>

      <div data-testid="wizard-step-body">{stepBody}</div>

      <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Button
          icon={<ArrowLeftOutlined />}
          disabled={current === 0}
          onClick={onBack}
          data-testid="wizard-back"
        >
          上一步
        </Button>
        {current < 3 ? (
          <Button
            type="primary"
            icon={<ArrowRightOutlined />}
            disabled={!canGoNext}
            onClick={onNext}
            data-testid="wizard-next"
          >
            下一步
          </Button>
        ) : (
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            loading={submitting}
            onClick={onFinish}
            data-testid="wizard-finish"
          >
            完成注册
          </Button>
        )}
      </div>
    </div>
  );
}
