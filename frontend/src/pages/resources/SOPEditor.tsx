import { useMemo, useRef, useState } from 'react';
import type { CSSProperties, DragEvent } from 'react';
import {
  App,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Input,
  Row,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ApiOutlined,
  BranchesOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ExperimentOutlined,
  HolderOutlined,
  NotificationOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { GlassPanel, PageHeader } from '../../components/common';
import {
  SOP_TEMPLATES,
  compileSOPFromNaturalLanguage,
} from '../../presets/agentLoopers';
import type { SOPStep, SOPStepKind, SOPTemplate } from '../../presets/agentLoopers';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const KIND_META: Record<SOPStepKind, { label: string; color: string; icon: React.ReactNode }> = {
  agent: { label: 'Agent', color: 'geekblue', icon: <RobotOutlined /> },
  tool: { label: '工具调用', color: 'cyan', icon: <ApiOutlined /> },
  human: { label: '人工节点', color: 'gold', icon: <UserOutlined /> },
  condition: { label: '条件分支', color: 'purple', icon: <BranchesOutlined /> },
  notify: { label: '通知', color: 'magenta', icon: <NotificationOutlined /> },
};

const KIND_OPTIONS: { value: SOPStepKind; label: string }[] = (
  Object.keys(KIND_META) as SOPStepKind[]
).map((k) => ({ value: k, label: KIND_META[k].label }));

function makeStepId(existing: SOPStep[]): string {
  const used = new Set(existing.map((s) => s.id));
  let i = existing.length + 1;
  while (used.has(`s${i}`)) i += 1;
  return `s${i}`;
}

function renumberDeps(steps: SOPStep[]): SOPStep[] {
  const valid = new Set(steps.map((s) => s.id));
  return steps.map((s) => ({
    ...s,
    depends_on: s.depends_on.filter((d) => valid.has(d) && d !== s.id),
  }));
}

interface StepRowProps {
  step: SOPStep;
  index: number;
  total: number;
  onChange: (patch: Partial<SOPStep>) => void;
  onRemove: () => void;
  onDragStart: (e: DragEvent<HTMLDivElement>) => void;
  onDragOver: (e: DragEvent<HTMLDivElement>) => void;
  onDrop: (e: DragEvent<HTMLDivElement>) => void;
  dragging: boolean;
}

const rowBase: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 12,
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid rgba(148, 163, 184, 0.15)',
  background: 'rgba(30, 41, 59, 0.35)',
  marginBottom: 8,
  transition: 'background 0.15s',
};

function StepRow({
  step,
  index,
  total,
  onChange,
  onRemove,
  onDragStart,
  onDragOver,
  onDrop,
  dragging,
}: StepRowProps) {
  const meta = KIND_META[step.kind];
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      style={{
        ...rowBase,
        background: dragging ? 'rgba(96, 165, 250, 0.15)' : rowBase.background,
        cursor: 'grab',
      }}
      data-testid={`sop-step-${step.id}`}
    >
      <div style={{ color: '#8895b4', fontSize: 16, paddingTop: 4 }}>
        <HolderOutlined />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <Tag color={meta.color} icon={meta.icon}>
            {meta.label}
          </Tag>
          <Text style={{ color: '#8895b4', fontSize: 12 }}>
            #{index + 1} / {total} · id: {step.id}
          </Text>
        </div>
        <Row gutter={8}>
          <Col span={14}>
            <Input
              placeholder="步骤标题（例如：抽取元数据）"
              value={step.title}
              onChange={(e) => onChange({ title: e.target.value })}
            />
          </Col>
          <Col span={10}>
            <Select<SOPStepKind>
              value={step.kind}
              options={KIND_OPTIONS}
              onChange={(kind) => onChange({ kind })}
              style={{ width: '100%' }}
            />
          </Col>
        </Row>
        <TextArea
          placeholder="详细描述 / prompt（可选）"
          value={step.detail ?? ''}
          onChange={(e) => onChange({ detail: e.target.value || undefined })}
          autoSize={{ minRows: 1, maxRows: 4 }}
          style={{ marginTop: 6 }}
        />
      </div>
      <Tooltip title="删除该步骤">
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={onRemove}
          aria-label="delete-step"
        />
      </Tooltip>
    </div>
  );
}

interface DagPreviewProps {
  steps: SOPStep[];
}

function DagPreview({ steps }: DagPreviewProps) {
  if (steps.length === 0) {
    return <Empty description="暂无步骤" />;
  }
  const idToIndex = new Map(steps.map((s, i) => [s.id, i]));
  return (
    <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 12 }}>
      {steps.map((s, i) => {
        const deps = s.depends_on
          .map((d) => (idToIndex.has(d) ? `#${(idToIndex.get(d) ?? 0) + 1}` : d))
          .join(', ');
        return (
          <div key={s.id} style={{ color: '#cbd5e1', lineHeight: 1.9 }}>
            <span style={{ color: '#60a5fa' }}>#{i + 1}</span>{' '}
            <span style={{ color: '#94a3b8' }}>[{KIND_META[s.kind].label}]</span>{' '}
            <span>{s.title || <em style={{ color: '#64748b' }}>(未命名)</em>}</span>
            {deps && <span style={{ color: '#8895b4' }}> ← {deps}</span>}
          </div>
        );
      })}
    </div>
  );
}

export default function SOPEditor() {
  const { message } = App.useApp();
  const [nlInput, setNlInput] = useState('');
  const [steps, setSteps] = useState<SOPStep[]>([]);
  const [templateKey, setTemplateKey] = useState<string | undefined>(undefined);
  const dragFrom = useRef<number | null>(null);
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);

  const handleCompile = () => {
    const compiled = compileSOPFromNaturalLanguage(nlInput);
    if (compiled.length === 0) {
      message.warning('未识别到任何步骤，请输入至少一句话或按换行分隔');
      return;
    }
    setSteps(compiled);
    setTemplateKey(undefined);
    message.success(`已解析 ${compiled.length} 个步骤`);
  };

  const handleTemplateSelect = (key: string) => {
    const tpl: SOPTemplate | undefined = SOP_TEMPLATES.find((t) => t.key === key);
    if (!tpl) return;
    setSteps(tpl.steps.map((s) => ({ ...s, depends_on: [...s.depends_on] })));
    setTemplateKey(key);
    message.success(`已加载模板：${tpl.name}`);
  };

  const handleAddStep = () => {
    setSteps((prev) => {
      const id = makeStepId(prev);
      const last = prev[prev.length - 1];
      const next: SOPStep = {
        id,
        title: '',
        kind: 'agent',
        depends_on: last ? [last.id] : [],
      };
      return [...prev, next];
    });
  };

  const handleUpdate = (index: number, patch: Partial<SOPStep>) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const handleRemove = (index: number) => {
    setSteps((prev) => {
      const removedId = prev[index]?.id;
      const filtered = prev.filter((_, i) => i !== index);
      if (!removedId) return filtered;
      return renumberDeps(
        filtered.map((s) => ({
          ...s,
          depends_on: s.depends_on.filter((d) => d !== removedId),
        })),
      );
    });
  };

  const handleReset = () => {
    setSteps([]);
    setNlInput('');
    setTemplateKey(undefined);
  };

  const handleDragStart = (index: number) => (e: DragEvent<HTMLDivElement>) => {
    dragFrom.current = index;
    setDraggingIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (targetIndex: number) => (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const from = dragFrom.current;
    dragFrom.current = null;
    setDraggingIndex(null);
    if (from === null || from === targetIndex) return;
    setSteps((prev) => {
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      if (!moved) return prev;
      next.splice(targetIndex, 0, moved);
      return next;
    });
  };

  const dagJson = useMemo(
    () => JSON.stringify({ steps }, null, 2),
    [steps],
  );

  const handleExport = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(dagJson)
        .then(() => message.success('已复制到剪贴板'))
        .catch(() => message.error('复制失败，请手动选中'));
    } else {
      message.info('当前环境不支持剪贴板，请手动复制下方 JSON');
    }
  };

  return (
    <div style={{ maxWidth: 1400 }}>
      <PageHeader
        title="SOP 编辑器"
        subtitle="用自然语言描述流程 → 编译成 DAG 步骤 → 挑一个模板一键上手"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              清空
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              disabled={steps.length === 0}
              onClick={handleExport}
            >
              导出 DAG JSON
            </Button>
          </Space>
        }
      />

      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <GlassPanel padded style={{ marginBottom: 16 }}>
            <Space align="center" size={8} style={{ marginBottom: 12 }}>
              <ThunderboltOutlined style={{ color: '#a78bfa' }} />
              <Text strong style={{ color: '#e8eef5' }}>
                自然语言 → SOP
              </Text>
            </Space>
            <Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
              每行一步，或用「。/；」分隔多个动作。识别关键词自动分配节点类型
              （工具 / 人工 / 条件 / 通知 / Agent）。
            </Paragraph>
            <TextArea
              value={nlInput}
              onChange={(e) => setNlInput(e.target.value)}
              placeholder={
                '示例：\n1. 抽取数据源元数据\n2. 人工审核字段注释\n3. 若质量不达标则回退\n4. 通知负责人验收'
              }
              autoSize={{ minRows: 6, maxRows: 12 }}
            />
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              <Button
                type="primary"
                icon={<ExperimentOutlined />}
                onClick={handleCompile}
              >
                编译为 SOP
              </Button>
              <Button icon={<PlusOutlined />} onClick={handleAddStep}>
                手动追加步骤
              </Button>
            </div>
          </GlassPanel>

          <GlassPanel padded>
            <Text strong style={{ color: '#e8eef5' }}>
              模板库（5 个）
            </Text>
            <Divider style={{ margin: '10px 0' }} />
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              {SOP_TEMPLATES.map((tpl) => {
                const active = tpl.key === templateKey;
                return (
                  <Card
                    key={tpl.key}
                    size="small"
                    hoverable
                    onClick={() => handleTemplateSelect(tpl.key)}
                    style={{
                      background: active
                        ? 'rgba(96, 165, 250, 0.12)'
                        : 'rgba(30, 41, 59, 0.35)',
                      borderColor: active
                        ? 'rgba(96, 165, 250, 0.6)'
                        : 'rgba(148, 163, 184, 0.15)',
                      cursor: 'pointer',
                    }}
                    data-testid={`sop-template-${tpl.key}`}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div>
                        <Text strong style={{ color: '#e8eef5' }}>
                          {tpl.name}
                        </Text>
                        <div style={{ color: '#8895b4', fontSize: 12, marginTop: 2 }}>
                          {tpl.description}
                        </div>
                      </div>
                      <Tag color="blue">{tpl.steps.length} 步</Tag>
                    </div>
                  </Card>
                );
              })}
            </Space>
          </GlassPanel>
        </Col>

        <Col xs={24} lg={12}>
          <GlassPanel padded style={{ marginBottom: 16 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12,
              }}
            >
              <Text strong style={{ color: '#e8eef5' }}>
                步骤编辑器（拖拽调整顺序）
              </Text>
              <Text style={{ color: '#8895b4', fontSize: 12 }}>
                共 {steps.length} 步
              </Text>
            </div>
            {steps.length === 0 ? (
              <Empty description="用左侧自然语言或模板生成步骤" />
            ) : (
              steps.map((s, i) => (
                <StepRow
                  key={s.id}
                  step={s}
                  index={i}
                  total={steps.length}
                  dragging={draggingIndex === i}
                  onChange={(patch) => handleUpdate(i, patch)}
                  onRemove={() => handleRemove(i)}
                  onDragStart={handleDragStart(i)}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop(i)}
                />
              ))
            )}
          </GlassPanel>

          <GlassPanel padded>
            <Text strong style={{ color: '#e8eef5' }}>
              DAG 预览
            </Text>
            <Divider style={{ margin: '10px 0' }} />
            <DagPreview steps={steps} />
          </GlassPanel>
        </Col>
      </Row>
    </div>
  );
}
