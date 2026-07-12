import type {
  AgentStudioConfig,
  DiscoveryDecision,
  DiscoveryItem,
} from './types';
import { normalizeStudioConfig } from './types';

export interface StudioCompleteness {
  percent: number;
  complete: boolean;
  sections: Array<{ key: string; label: string; complete: boolean; reason?: string; optional?: boolean }>;
}

export function evaluateDraftSave(config: AgentStudioConfig): { ok: boolean; reason?: string } {
  const normalized = normalizeStudioConfig(config);
  if (!normalized.objective.name.trim()) {
    return { ok: false, reason: '请先填写 Agent 名称' };
  }
  if (!normalized.objective.problem.trim()) {
    return { ok: false, reason: '请先填写要解决的问题' };
  }
  return { ok: true };
}

export function evaluateStudioCompleteness(config: AgentStudioConfig): StudioCompleteness {
  const normalized = normalizeStudioConfig(config);
  const sections = [
    {
      key: 'objective',
      label: '目标',
      complete: Boolean(
        normalized.objective.name.trim() && normalized.objective.problem.trim(),
      ),
      reason: '需要名称和要解决的问题',
    },
    {
      key: 'role',
      label: '角色',
      complete: Boolean(normalized.role.system_prompt.trim()),
      reason: '需要系统指令（留空将使用默认模板）',
    },
    {
      key: 'model',
      label: '模型',
      complete: Boolean(normalized.model.model_id.trim()),
      reason: '需要选择模型（留空将使用默认模型）',
    },
    {
      key: 'capabilities',
      label: '能力',
      optional: true,
      complete: true,
      reason: 'Skill / MCP 可选；运行环境会在保存时尽量自动绑定',
    },
    {
      key: 'collaboration',
      label: '协作',
      optional: true,
      complete:
        normalized.collaboration.mode === 'single' ||
        normalized.collaboration.participants.length > 0,
      reason: '多 Agent 模式需要参与者',
    },
    {
      key: 'loop',
      label: 'Loop / SOP',
      optional: true,
      complete: normalized.loop.max_iterations > 0 && normalized.loop.timeout_seconds > 0,
      reason: '已提供默认 Loop 与 SOP，可按需调整',
    },
    {
      key: 'hooks',
      label: 'Hook',
      optional: true,
      complete: true,
      reason: 'Hook 可选，默认不启用',
    },
    {
      key: 'eval',
      label: 'Eval',
      optional: true,
      complete: true,
      reason: 'Eval 可选，发布前可再补充门禁',
    },
    {
      key: 'guardrails',
      label: '护栏',
      optional: true,
      complete: normalized.guardrails.max_tool_calls > 0,
      reason: '已提供默认护栏，可按需调整',
    },
    {
      key: 'release',
      label: '发布',
      optional: true,
      complete: Boolean(normalized.release.change_summary.trim()),
      reason: '留空将自动写入“初始草稿”',
    },
  ];
  const required = sections.filter((section) => !section.optional);
  const passed = required.filter((section) => section.complete).length;
  return {
    percent: Math.round((passed / required.length) * 100),
    complete: passed === required.length,
    sections,
  };
}

const decisionMatrix: Record<DiscoveryItem['status'], DiscoveryDecision[]> = {
  new: ['import', 'link', 'ignore', 'external'],
  matched: ['link', 'keep_platform', 'ignore', 'external'],
  changed: ['link', 'keep_platform', 'ignore', 'external'],
  missing: ['keep_platform', 'external', 'ignore'],
  unsupported: ['external', 'ignore'],
  error: ['pending', 'ignore'],
};

export function availableDiscoveryDecisions(item: DiscoveryItem): DiscoveryDecision[] {
  return decisionMatrix[item.status];
}

export function resolveDiscoveryDecision(
  item: DiscoveryItem,
  decision: DiscoveryDecision,
): DiscoveryItem {
  if (!availableDiscoveryDecisions(item).includes(decision)) {
    throw new Error(`状态 ${item.status} 不允许决策 ${decision}`);
  }
  return { ...item, decision };
}
