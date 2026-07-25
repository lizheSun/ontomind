/**
 * SettingsDialog — opencode 风格的偏好面板 (Editorial Light theme).
 *
 * 5 项设置严格照 opencode web:
 *  1. Shell (auto/bash/zsh/fish/sh/pwsh) — 通过 PATCH /config 写到 opencode server
 *  2. Show reasoning summaries — 前端偏好
 *  3. Expand shell tool parts — 前端偏好
 *  4. Expand edit/write/patch tool parts — 前端偏好
 *  5. New layout designs — 保留字段，本项目 default true
 */
import { Modal, Switch, Typography } from 'antd';
import { useOcSettings, type OcSettings, type ShellOption } from '../hooks/useOcSettings';

const { Text } = Typography;

interface Props {
  open: boolean;
  onClose: () => void;
}

const SHELL_OPTIONS: { value: ShellOption; label: string; hint?: string }[] = [
  { value: 'auto', label: '自动', hint: '默认' },
  { value: 'bash', label: 'bash' },
  { value: 'zsh', label: 'zsh' },
  { value: 'fish', label: 'fish' },
  { value: 'sh', label: 'sh' },
  { value: 'pwsh', label: 'pwsh', hint: 'PowerShell' },
];

interface RowProps {
  title: string;
  description: string;
  control: React.ReactNode;
}

function Row({ title, description, control }: RowProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 24,
        padding: '18px 0',
        borderBottom: '1px solid var(--border-hairline)',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 15,
            fontWeight: 500,
            color: 'var(--ink-100)',
            letterSpacing: '-0.01em',
            marginBottom: 4,
          }}
        >
          {title}
        </div>
        <Text style={{ color: 'var(--ink-60)', fontSize: 12.5, lineHeight: 1.6 }}>
          {description}
        </Text>
      </div>
      <div style={{ flexShrink: 0, paddingTop: 2 }}>{control}</div>
    </div>
  );
}

function ShellPicker({
  value,
  onChange,
}: {
  value: ShellOption;
  onChange: (v: ShellOption) => void;
}) {
  return (
    <div
      style={{
        display: 'inline-flex',
        gap: 4,
        padding: 3,
        borderRadius: 10,
        background: 'var(--paper-02)',
        border: '1px solid var(--border-hairline)',
      }}
    >
      {SHELL_OPTIONS.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            style={{
              height: 26,
              padding: '0 10px',
              borderRadius: 7,
              border: 'none',
              background: active ? 'var(--paper-00)' : 'transparent',
              boxShadow: active ? '0 1px 2px rgba(26,25,24,0.04)' : 'none',
              color: active ? 'var(--ink-100)' : 'var(--ink-60)',
              fontSize: 12,
              fontFamily: active ? 'var(--font-mono)' : 'var(--font-sans)',
              fontWeight: active ? 500 : 400,
              cursor: 'pointer',
              transition: 'all 140ms',
            }}
            title={opt.hint}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export default function SettingsDialog({ open, onClose }: Props) {
  const { settings, set, updateShell } = useOcSettings();

  const bind = <K extends keyof OcSettings>(key: K) => ({
    checked: settings[key] as boolean,
    onChange: (v: boolean) => set(key, v as OcSettings[K]),
  });

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
      centered
      styles={{
        body: { padding: 0 },
      }}
      closable={false}
    >
      <div
        style={{
          padding: '24px 32px 8px',
          borderBottom: '1px solid var(--border-hairline)',
        }}
      >
        <div
          style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 24,
            fontWeight: 500,
            color: 'var(--ink-100)',
            letterSpacing: '-0.02em',
            fontStyle: 'italic',
            marginBottom: 4,
          }}
        >
          Settings
        </div>
        <Text style={{ color: 'var(--ink-60)', fontSize: 12.5 }}>
          偏好项在本机保留；Shell 会同步给 opencode server。
        </Text>
      </div>

      <div style={{ padding: '4px 32px 24px' }}>
        <Row
          title="终端 Shell"
          description="选择终端使用的 shell。兼容的 shell 也会用于智能体工具调用。"
          control={
            <ShellPicker
              value={settings.shell}
              onChange={(v) => void updateShell(v)}
            />
          }
        />
        <Row
          title="显示推理摘要"
          description="在时间线中显示模型推理摘要。"
          control={<Switch {...bind('showReasoningSummaries')} />}
        />
        <Row
          title="展开 shell 工具部分"
          description="默认在时间线中展开 shell 工具部分。"
          control={<Switch {...bind('expandShellTool')} />}
        />
        <Row
          title="展开编辑工具部分"
          description="默认在时间线中展开 edit、write 和 patch 工具部分。"
          control={<Switch {...bind('expandEditTool')} />}
        />
        <Row
          title="新版布局和设计"
          description="启用重新设计的布局、主页、输入框和会话界面。"
          control={<Switch {...bind('newLayoutDesigns')} />}
        />
      </div>

      <div
        style={{
          padding: '14px 32px',
          borderTop: '1px solid var(--border-hairline)',
          background: 'var(--paper-02)',
          borderBottomLeftRadius: 14,
          borderBottomRightRadius: 14,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 8,
        }}
      >
        <button
          type="button"
          onClick={onClose}
          style={{
            height: 32,
            padding: '0 16px',
            borderRadius: 8,
            border: 'none',
            background: 'var(--ink-100)',
            color: 'var(--paper-00)',
            fontSize: 13,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          完成
        </button>
      </div>
    </Modal>
  );
}
