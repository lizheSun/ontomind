/**
 * 权限矩阵编辑器 — OpenCode 的 15 个权限键 × {allow/ask/deny} + glob 细粒度规则.
 *
 * 为什么要做成矩阵而不是 JSON 编辑框：
 * OpenCode 对**未知权限键静默忽略** —— 写 `write: deny`（应为 `edit`）不会报错，
 * 只是不生效，用户以为限制住了实际没有。矩阵从 UI 层面就杜绝了写错键的可能。
 *
 * 两个必须让用户看见的规则：
 * 1. 只有 10 个键支持 glob，其余 5 个只能给简写动作（这里直接禁用按钮）
 * 2. 规则**最后匹配胜出**，所以 `*` 必须在最前（提供一键置顶）
 */
import { useMemo } from 'react';
import {
  Alert,
  Button,
  Input,
  Segmented,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ArrowUpOutlined,
  CloseOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type {
  PermissionAction,
  PermissionConfig,
  PermissionKeyMeta,
} from '../../types/agentFactory';

const { Text } = Typography;

const ACTIONS: PermissionAction[] = ['allow', 'ask', 'deny'];
const ACTION_LABEL: Record<PermissionAction, string> = {
  allow: '允许',
  ask: '询问',
  deny: '禁止',
};
const ACTION_COLOR: Record<PermissionAction, string> = {
  allow: '#52c41a',
  ask: '#faad14',
  deny: '#ff4d4f',
};

/** 常见 glob 示例，按权限键给不同建议 —— 让用户不用猜怎么写 */
const GLOB_EXAMPLES: Record<string, string> = {
  bash: 'git diff',
  read: 'src/**',
  edit: 'src/**',
  task: 'code-reviewer',
  skill: 'git-*',
  external_directory: '/tmp/**',
  glob: '**/*.ts',
  grep: 'src/**',
  list: 'src/**',
  lsp: '*',
};

interface Props {
  value: PermissionConfig;
  onChange: (next: PermissionConfig) => void;
  meta: PermissionKeyMeta[];
  /** 只显示这些键（如 Task 权限矩阵只关心 task） */
  onlyKeys?: string[];
}

export default function PermissionMatrix({ value, onChange, meta, onlyKeys }: Props) {
  const keys = useMemo(
    () => (onlyKeys ? meta.filter((m) => onlyKeys.includes(m.key)) : meta),
    [meta, onlyKeys],
  );

  const setKey = (key: string, rule: PermissionConfig[string] | undefined) => {
    const next = { ...value };
    if (rule === undefined) delete next[key];
    else next[key] = rule;
    onChange(next);
  };

  /** 当前该键的模式：未配置 / 简写动作 / glob 规则 */
  const modeOf = (key: string): 'unset' | 'simple' | 'glob' => {
    const v = value[key];
    if (v === undefined) return 'unset';
    return typeof v === 'string' ? 'simple' : 'glob';
  };

  const toSimple = (key: string, act: PermissionAction) => setKey(key, act);

  const toGlob = (key: string) => {
    const cur = value[key];
    const base: Record<string, PermissionAction> =
      typeof cur === 'string'
        ? { '*': cur }
        : { '*': 'ask', [GLOB_EXAMPLES[key] ?? 'example']: 'allow' };
    setKey(key, base);
  };

  const patchGlob = (
    key: string,
    updater: (cur: Record<string, PermissionAction>) => Record<string, PermissionAction>,
  ) => {
    const cur = value[key];
    if (typeof cur !== 'object' || !cur) return;
    setKey(key, updater(cur));
  };

  return (
    <div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        title="OpenCode 只认这 15 个权限键"
        description={
          <span style={{ fontSize: 12 }}>
            写错的键（如 <Text code>write</Text>）会被 <b>静默忽略</b>
            ：不报错、也不生效。规则<b>最后匹配胜出</b>，所以{' '}
            <Text code>*</Text> 必须放第一条。
          </span>
        }
      />

      {keys.map((m) => {
        const mode = modeOf(m.key);
        const rule = value[m.key];
        const globRule = typeof rule === 'object' && rule ? rule : null;
        const patterns = globRule ? Object.keys(globRule) : [];
        const starMisplaced = patterns.includes('*') && patterns.indexOf('*') !== 0;

        return (
          <div
            key={m.key}
            style={{
              padding: '8px 10px',
              marginBottom: 6,
              border: '1px solid var(--border-hairline, rgba(26,25,24,0.08))',
              borderRadius: 8,
              background: mode === 'unset' ? 'transparent' : 'var(--paper-01, #fafaf7)',
            }}
          >
            {/* 键名 + 动作选择 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <Space size={5} style={{ width: 210, flexShrink: 0 }}>
                <Text code style={{ fontSize: 12 }}>
                  {m.key}
                </Text>
                <Tooltip title={`管控：${m.gates}`}>
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: 11 }} />
                </Tooltip>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {m.label}
                </Text>
              </Space>

              <Segmented
                size="small"
                value={mode === 'unset' ? 'unset' : mode === 'simple' ? (rule as string) : 'glob'}
                onChange={(v) => {
                  const s = v as string;
                  if (s === 'unset') setKey(m.key, undefined);
                  else if (s === 'glob') toGlob(m.key);
                  else toSimple(m.key, s as PermissionAction);
                }}
                options={[
                  { label: '默认', value: 'unset' },
                  ...ACTIONS.map((a) => ({ label: ACTION_LABEL[a], value: a })),
                  ...(m.glob ? [{ label: '按模式', value: 'glob' }] : []),
                ]}
              />

              {!m.glob && (
                <Tooltip title="OpenCode 不支持对该键做 glob 细粒度配置">
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    仅简写
                  </Text>
                </Tooltip>
              )}
              {mode === 'unset' && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  未配置 → 用 OpenCode 默认行为
                </Text>
              )}
            </div>

            {/* glob 规则行编辑 */}
            {globRule && (
              <div style={{ marginTop: 8, paddingLeft: 8 }}>
                {starMisplaced && (
                  <Text type="warning" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
                    ⚠ 最后匹配胜出，<Text code>*</Text> 放在中间会覆盖它后面的规则
                  </Text>
                )}
                {patterns.map((pat, idx) => (
                  <div
                    key={`${pat}-${idx}`}
                    style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}
                  >
                    <Input
                      size="small"
                      value={pat}
                      placeholder={GLOB_EXAMPLES[m.key] ?? '*'}
                      onChange={(e) => {
                        const nk = e.target.value;
                        patchGlob(m.key, (cur) => {
                          // 保持顺序：重建对象
                          const out: Record<string, PermissionAction> = {};
                          Object.entries(cur).forEach(([k, v], i) => {
                            out[i === idx ? nk : k] = v;
                          });
                          return out;
                        });
                      }}
                      style={{ width: 210, fontFamily: 'monospace', fontSize: 12 }}
                      status={pat === '*' && idx !== 0 ? 'warning' : undefined}
                    />
                    <Segmented
                      size="small"
                      value={globRule[pat]}
                      onChange={(v) =>
                        patchGlob(m.key, (cur) => ({
                          ...cur,
                          [pat]: v as PermissionAction,
                        }))
                      }
                      options={ACTIONS.map((a) => ({ label: ACTION_LABEL[a], value: a }))}
                    />
                    {pat === '*' && idx !== 0 && (
                      <Tooltip title="把 * 移到第一条">
                        <Button
                          size="small"
                          type="text"
                          icon={<ArrowUpOutlined />}
                          onClick={() =>
                            patchGlob(m.key, (cur) => {
                              const star = cur['*'];
                              const rest = Object.fromEntries(
                                Object.entries(cur).filter(([k]) => k !== '*'),
                              );
                              return { '*': star, ...rest } as Record<string, PermissionAction>;
                            })
                          }
                        />
                      </Tooltip>
                    )}
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<CloseOutlined />}
                      onClick={() =>
                        patchGlob(m.key, (cur) =>
                          Object.fromEntries(
                            Object.entries(cur).filter(([k]) => k !== pat),
                          ) as Record<string, PermissionAction>,
                        )
                      }
                    />
                  </div>
                ))}
                <Button
                  size="small"
                  type="dashed"
                  icon={<PlusOutlined />}
                  onClick={() =>
                    patchGlob(m.key, (cur) => ({
                      ...cur,
                      [GLOB_EXAMPLES[m.key] ?? `pattern-${Object.keys(cur).length}`]: 'allow',
                    }))
                  }
                >
                  添加模式
                </Button>
              </div>
            )}
          </div>
        );
      })}

      {/* 摘要：让用户一眼看到最终会写进文件的内容 */}
      {Object.keys(value).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Space size={4} wrap>
            <Text type="secondary" style={{ fontSize: 11 }}>
              已配置：
            </Text>
            {Object.entries(value).map(([k, v]) => (
              <Tag
                key={k}
                style={{
                  fontSize: 10.5,
                  margin: 0,
                  color: typeof v === 'string' ? ACTION_COLOR[v] : undefined,
                }}
              >
                {k}
                {typeof v === 'string' ? `=${v}` : `(${Object.keys(v).length} 条)`}
              </Tag>
            ))}
          </Space>
        </div>
      )}
    </div>
  );
}
