/**
 * Loop 拓扑图 — 纯 SVG，零新依赖.
 *
 * 表达 Agent Loop 的三件事：
 * 1. 谁是对话入口（primary），谁是被调的 subagent
 *    —— 方案没有自定义 primary 时，入口是 OpenCode **内置**的 build/plan，
 *      这种情况必须把内置节点画出来，否则图上会出现「一堆 subagent 但没人调它们」
 * 2. 调用关系：由入口的 permission.task 决定
 *    实线 = allow（自动委派）／虚线 = ask（需确认）／灰虚线 = deny（模型看不到）
 * 3. skill 作为可加载资源列在图例区
 *
 * 布局按 pattern 切换：linear（流水线/双阶段）/ star（编排者居中，其余同心分布）
 */
import { useMemo } from 'react';
import { Empty, Space, Tag, Typography } from 'antd';
import type {
  BundleMember,
  BundlePattern,
  PermissionAction,
  PermissionConfig,
} from '../../types/agentFactory';

const { Text } = Typography;

interface AgentNode {
  name: string;
  role: 'primary' | 'subagent';
  /** 后端算好的最终委派动作（与「委派授权」矩阵同源） */
  effective?: PermissionAction;
  /** 内置 primary（build/plan）—— 不是本方案定义的，用虚边框区分 */
  builtin?: boolean;
  permission?: PermissionConfig | null;
  x: number;
  y: number;
}

interface Props {
  members: BundleMember[];
  pattern: BundlePattern;
  /** name → permission_json，用于解析 task 调用关系 */
  permissionByName: Record<string, PermissionConfig | null | undefined>;
  subagentDepth?: number | null;
  defaultAgent?: string | null;
  width?: number;
  height?: number;
}

const BUILTIN_PRIMARY = ['build', 'plan'];

/** OpenCode 的 task 规则：glob 匹配，最后匹配胜出 */
function resolveTaskAction(
  perm: PermissionConfig | null | undefined,
  target: string,
): PermissionAction {
  const rule = perm?.task;
  if (rule === undefined) return 'allow'; // 未配置 = 默认允许
  if (typeof rule === 'string') return rule;
  let action: PermissionAction = 'allow';
  for (const [pat, act] of Object.entries(rule)) {
    const re = new RegExp(
      '^' + pat.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$',
    );
    if (re.test(target)) action = act;
  }
  return action;
}

const NODE_W = 104;
const NODE_H = 32;
const PAD = 14;

export default function LoopTopology({
  members,
  pattern,
  permissionByName,
  subagentDepth,
  defaultAgent,
  width = 560,
  height,
}: Props) {
  const { agentMembers, skillMembers } = useMemo(() => {
    const a = members.filter((m) => m.member_type === 'agent' && m.member_name);
    const s = members.filter((m) => m.member_type === 'skill' && m.member_name);
    return { agentMembers: a, skillMembers: s };
  }, [members]);

  /** 入口节点：自定义 primary，没有则用内置 build/plan 兜底 */
  const entries = useMemo(() => {
    const custom = agentMembers
      .filter((m) => m.role === 'primary')
      .map((m) => ({
        name: m.member_name!,
        builtin: false,
        permission: permissionByName[m.member_name!],
      }));
    if (custom.length > 0) return custom;

    // 方案没自定义 primary → 主对话来自 OpenCode 内置
    const fallback =
      defaultAgent && BUILTIN_PRIMARY.includes(defaultAgent) ? defaultAgent : 'build';
    return [{ name: fallback, builtin: true, permission: undefined }];
  }, [agentMembers, permissionByName, defaultAgent]);

  const subs = useMemo(
    () =>
      agentMembers
        .filter((m) => m.role !== 'primary')
        .map((m) => ({
          name: m.member_name!,
          builtin: false,
          permission: permissionByName[m.member_name!],
          // 后端已按「方案覆盖 > 模板 > 默认」算好最终动作，
          // 优先用它，保证图与「委派授权」矩阵完全一致
          effective: (m.task_permission ??
            m.effective_task ??
            undefined) as PermissionAction | undefined,
        })),
    [agentMembers, permissionByName],
  );

  const isLinear = pattern === 'pipeline' || pattern === 'plan-build';

  /** 布局：linear 单行等距；star 入口在上、subagent 在下分行铺开 */
  const { nodes, canvasW, canvasH } = useMemo(() => {
    const out: AgentNode[] = [];

    if (isLinear) {
      const chain = [...entries, ...subs];
      const gap = 34;
      const needW = chain.length * NODE_W + (chain.length - 1) * gap + PAD * 2;
      const w = Math.max(width, needW);
      const y = 60;
      chain.forEach((n, i) => {
        out.push({
          ...n,
          role: i === 0 ? 'primary' : 'subagent',
          x: PAD + i * (NODE_W + gap),
          y,
        });
      });
      return { nodes: out, canvasW: w, canvasH: 150 };
    }

    // star：subagent 每行最多 4 个，避免溢出与重叠
    const perRow = Math.min(4, Math.max(1, subs.length));
    const rows = Math.ceil(subs.length / perRow) || 1;
    const gapX = 22;
    const rowGapY = 74;
    const rowW = perRow * NODE_W + (perRow - 1) * gapX;
    const w = Math.max(width, rowW + PAD * 2);
    const cx = w / 2;
    const topY = 34;

    entries.forEach((n, i) => {
      const total = entries.length;
      const spanW = total * NODE_W + (total - 1) * gapX;
      out.push({
        ...n,
        role: 'primary',
        x: cx - spanW / 2 + i * (NODE_W + gapX),
        y: topY,
      });
    });

    subs.forEach((n, i) => {
      const row = Math.floor(i / perRow);
      const idxInRow = i % perRow;
      const countInRow = Math.min(perRow, subs.length - row * perRow);
      const thisRowW = countInRow * NODE_W + (countInRow - 1) * gapX;
      out.push({
        ...n,
        role: 'subagent',
        x: cx - thisRowW / 2 + idxInRow * (NODE_W + gapX),
        y: topY + 96 + row * rowGapY,
      });
    });

    const h = topY + 96 + Math.max(0, rows - 1) * rowGapY + NODE_H + 20;
    return { nodes: out, canvasW: w, canvasH: Math.max(height ?? 0, h) };
  }, [entries, subs, isLinear, width, height]);

  const edges = useMemo(() => {
    const out: Array<{ from: AgentNode; to: AgentNode; action: PermissionAction }> = [];
    if (isLinear) {
      for (let i = 0; i < nodes.length - 1; i++) {
        out.push({
          from: nodes[i],
          to: nodes[i + 1],
          action:
            nodes[i + 1].effective ??
            resolveTaskAction(nodes[i].permission, nodes[i + 1].name),
        });
      }
      return out;
    }
    const primaryNodes = nodes.filter((n) => n.role === 'primary');
    const subNodes = nodes.filter((n) => n.role === 'subagent');
    primaryNodes.forEach((p) => {
      subNodes.forEach((s) => {
        out.push({
          from: p,
          to: s,
          action: s.effective ?? resolveTaskAction(p.permission, s.name),
        });
      });
    });
    return out;
  }, [nodes, isLinear]);

  if (agentMembers.length === 0 && skillMembers.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Text type="secondary" style={{ fontSize: 12 }}>
            添加成员后显示 Loop 拓扑
          </Text>
        }
      />
    );
  }

  const EDGE_STYLE: Record<
    PermissionAction,
    { stroke: string; dash?: string; opacity: number }
  > = {
    allow: { stroke: '#0071e3', opacity: 0.9 }, /* 【UI 重构】Apple Blue */
    ask: { stroke: '#faad14', dash: '5 3', opacity: 0.9 },
    deny: { stroke: '#bfbcb5', dash: '2 4', opacity: 0.55 },
  };

  const depthBlocked = subagentDepth === 0 && subs.length > 0;
  const usingBuiltin = entries.some((e) => e.builtin);
  /** 被 deny 的目标 —— 图上是灰虚线，用户最容易困惑的就是这个，要明确点出来 */
  const deniedTargets = Array.from(
    new Set(edges.filter((e) => e.action === 'deny').map((e) => e.to.name)),
  );

  return (
    <div>
      <svg width={canvasW} height={canvasH} style={{ display: 'block' }}>
        <defs>
          {(['allow', 'ask', 'deny'] as PermissionAction[]).map((a) => (
            <marker
              key={a}
              id={`arrow-${a}`}
              viewBox="0 0 8 8"
              refX="7"
              refY="4"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path
                d="M 0 1 L 7 4 L 0 7 z"
                fill={EDGE_STYLE[a].stroke}
                opacity={EDGE_STYLE[a].opacity}
              />
            </marker>
          ))}
        </defs>

        {/* 边（先画，压在节点下面） */}
        {edges.map((e, i) => {
          const st = EDGE_STYLE[e.action];
          let d: string;
          if (isLinear) {
            d = `M ${e.from.x + NODE_W} ${e.from.y + NODE_H / 2} L ${e.to.x} ${
              e.to.y + NODE_H / 2
            }`;
          } else {
            const x1 = e.from.x + NODE_W / 2;
            const y1 = e.from.y + NODE_H;
            const x2 = e.to.x + NODE_W / 2;
            const y2 = e.to.y;
            const my = y1 + (y2 - y1) * 0.55;
            d = `M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`;
          }
          return (
            <path
              key={`${e.from.name}-${e.to.name}-${i}`}
              d={d}
              fill="none"
              stroke={st.stroke}
              strokeWidth={e.action === 'deny' ? 1 : 1.6}
              strokeDasharray={st.dash}
              opacity={depthBlocked ? 0.22 : st.opacity}
              markerEnd={`url(#arrow-${e.action})`}
            />
          );
        })}

        {/* 节点 */}
        {nodes.map((n) => {
          const isPrimary = n.role === 'primary';
          const isDefault = defaultAgent === n.name;
          const label = n.name.length > 13 ? `${n.name.slice(0, 12)}…` : n.name;
          return (
            <g key={`${n.role}-${n.name}`}>
              <rect
                x={n.x}
                y={n.y}
                width={NODE_W}
                height={NODE_H}
                rx={8}
                fill={isPrimary ? (n.builtin ? '#69b4ff' : '#0071e3') : '#fff'}
                stroke={isPrimary ? '#0071e3' : 'rgba(26,25,24,0.20)'}
                strokeWidth={isDefault ? 2.5 : 1}
                strokeDasharray={n.builtin ? '4 3' : undefined}
              />
              <text
                x={n.x + NODE_W / 2}
                y={n.y + NODE_H / 2 + 4}
                textAnchor="middle"
                fontSize="11.5"
                fontFamily="'JetBrains Mono', monospace"
                fill={isPrimary ? '#fff' : '#1a1918'}
              >
                {label}
              </text>
              {(isDefault || n.builtin) && (
                <text
                  x={n.x + NODE_W / 2}
                  y={n.y - 6}
                  textAnchor="middle"
                  fontSize="9.5"
                  fill={n.builtin ? '#8f8b84' : '#0071e3'}
                >
                  {n.builtin ? 'OpenCode 内置入口' : '默认入口'}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* 图例 */}
      <Space size={12} wrap style={{ marginTop: 8 }}>
        <Space size={4}>
          <svg width="26" height="8">
            <line x1="0" y1="4" x2="26" y2="4" stroke="#0071e3" strokeWidth="1.6" />{/* 【UI 重构】Apple Blue */}
          </svg>
          <Text type="secondary" style={{ fontSize: 11 }}>
            允许委派
          </Text>
        </Space>
        <Space size={4}>
          <svg width="26" height="8">
            <line
              x1="0"
              y1="4"
              x2="26"
              y2="4"
              stroke="#faad14"
              strokeWidth="1.6"
              strokeDasharray="5 3"
            />
          </svg>
          <Text type="secondary" style={{ fontSize: 11 }}>
            需确认
          </Text>
        </Space>
        <Space size={4}>
          <svg width="26" height="8">
            <line
              x1="0"
              y1="4"
              x2="26"
              y2="4"
              stroke="#bfbcb5"
              strokeWidth="1"
              strokeDasharray="2 4"
            />
          </svg>
          <Text type="secondary" style={{ fontSize: 11 }}>
            禁止（模型看不到，不会指派）
          </Text>
        </Space>
        {usingBuiltin && (
          <Space size={4}>
            <svg width="16" height="12">
              <rect
                x="0.5"
                y="1"
                width="15"
                height="10"
                rx="3"
                fill="#69b4ff"
                stroke="#0071e3"
                strokeDasharray="3 2"
              />
            </svg>
            <Text type="secondary" style={{ fontSize: 11 }}>
              OpenCode 内置
            </Text>
          </Space>
        )}
        {skillMembers.length > 0 && (
          <Space size={4}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              Skill：
            </Text>
            {skillMembers.map((s) => (
              <Tag
                key={s.id}
                color={s.skill_permission === 'deny' ? 'default' : 'blue'}
                style={{ fontSize: 10, margin: 0 }}
              >
                {s.member_name}
                {s.skill_permission && s.skill_permission !== 'allow'
                  ? `(${s.skill_permission})`
                  : ''}
              </Tag>
            ))}
          </Space>
        )}
      </Space>

      {usingBuiltin && (
        <Text type="secondary" style={{ fontSize: 11.5, display: 'block', marginTop: 6 }}>
          本方案未自定义 primary，主对话使用 OpenCode 内置的{' '}
          <Text code style={{ fontSize: 11 }}>
            {entries[0].name}
          </Text>
          （虚线框），它会按各 subagent 的 description 自动委派。
        </Text>
      )}
      {deniedTargets.length > 0 && (
        <Text type="warning" style={{ fontSize: 11.5, display: 'block', marginTop: 6 }}>
          ⚠ <Text code style={{ fontSize: 11 }}>{deniedTargets.join('、')}</Text>{' '}
          当前是禁止状态（灰虚线）—— OpenCode 会把它从 Task 工具描述里整条移除，
          模型看不到、永远不会指派。到上方「<b>委派授权</b>」把它切成「允许」即可。
        </Text>
      )}
      {depthBlocked && (
        <Text type="warning" style={{ fontSize: 11.5, display: 'block', marginTop: 4 }}>
          ⚠ subagent_depth = 0 → 禁止派生任何 subagent，图中委派关系都不会生效
        </Text>
      )}
    </div>
  );
}
