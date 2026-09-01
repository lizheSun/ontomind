import type { PluginId } from '../../types/harness';

export const AGENT_META: Record<
  PluginId,
  { name: string; blurb: string; placeholder: string; hints: string[] }
> = {
  opencode: {
    name: 'OpenCode',
    blurb: '本地编码助手。在选定工作区里读改代码、排查问题。',
    placeholder: '描述要改的代码或排查的问题… Shift+Enter 换行',
    hints: ['先看仓库结构，再指出最可能的问题', '帮我把这个函数改得更清晰并补测试', '排查这个问题并给出修复步骤'],
  },
  dsh: {
    name: 'DeepSeek Harness',
    blurb: '通用助手。调研、写稿、分析数据、把任务跑完。',
    placeholder: '问任何事，或描述要完成的任务… Shift+Enter 换行',
    hints: ['把这件事拆成可执行步骤并标出风险', '根据这些材料写一份简报', '帮我设计验证方案，怎么算做完'],
  },
};

export function agentName(id: PluginId): string {
  return AGENT_META[id]?.name ?? id;
}
