/**
 * 容器配置编辑器 — 端口 / 环境变量 / 卷挂载 的结构化行编辑。
 *
 * 设计目标（替代原来「一个 Input 里用逗号拼字符串」的写法）：
 * - 每个字段拆成独立输入框，方向语义写在标签上，不用猜 8080:80 谁是谁
 * - 每行都有 placeholder 示例，且区块顶部给出「一键填入示例」
 * - 即时校验：端口范围、容器路径必须绝对、环境变量名合法
 */
import { Button, Input, InputNumber, Segmented, Select, Tooltip, Typography } from 'antd';
import {
  CloseOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { EnvVar, PortMapping, VolumeMapping } from '../../types/compute';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// 校验
// ---------------------------------------------------------------------------

export function isValidPort(v: unknown): boolean {
  const n = Number(v);
  return Number.isInteger(n) && n >= 1 && n <= 65535;
}

export function isAbsPath(v: string): boolean {
  return v.startsWith('/') && v.length > 1;
}

export function isValidHostPath(v: string): boolean {
  // 绝对路径 或 命名卷（字母数字开头）
  return v.startsWith('/') || /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(v);
}

export function isValidEnvKey(v: string): boolean {
  return /^[A-Za-z_][A-Za-z0-9_]*$/.test(v);
}

/** 提交前统一校验，返回错误文案数组（空数组 = 通过） */
export function validateContainerConfig(cfg: {
  ports: PortMapping[];
  envs: EnvVar[];
  volumes: VolumeMapping[];
  network?: string;
}): string[] {
  const errs: string[] = [];

  const seenHost = new Set<string>();
  cfg.ports.forEach((p, i) => {
    if (!isValidPort(p.host_port)) errs.push(`端口第 ${i + 1} 行：宿主端口需为 1-65535`);
    if (!isValidPort(p.container_port)) errs.push(`端口第 ${i + 1} 行：容器端口需为 1-65535`);
    const key = `${p.host_port}/${p.protocol}`;
    if (seenHost.has(key)) errs.push(`宿主端口 ${key} 重复映射`);
    seenHost.add(key);
  });

  cfg.envs.forEach((e, i) => {
    if (!e.key.trim()) errs.push(`环境变量第 ${i + 1} 行：变量名不能为空`);
    else if (!isValidEnvKey(e.key)) {
      errs.push(`环境变量第 ${i + 1} 行：'${e.key}' 非法（只能字母/数字/下划线，且不能数字开头）`);
    }
  });

  cfg.volumes.forEach((v, i) => {
    if (!v.host_path.trim()) errs.push(`挂载第 ${i + 1} 行：宿主路径不能为空`);
    else if (!isValidHostPath(v.host_path)) {
      errs.push(`挂载第 ${i + 1} 行：宿主路径需为绝对路径（/data/app）或命名卷（appdata）`);
    }
    if (!v.container_path.trim()) errs.push(`挂载第 ${i + 1} 行：容器路径不能为空`);
    else if (!isAbsPath(v.container_path)) {
      errs.push(`挂载第 ${i + 1} 行：容器路径必须是绝对路径，如 /app`);
    }
  });

  if (cfg.network === 'host' && cfg.ports.length > 0) {
    errs.push('network=host 时不能配置端口映射（容器直接用宿主网络），请删除端口或改回 bridge');
  }

  return errs;
}

// ---------------------------------------------------------------------------
// 区块头（标题 + 说明 + 填示例）
// ---------------------------------------------------------------------------

function BlockHead({
  title,
  hint,
  example,
  onFillExample,
}: {
  title: string;
  hint: string;
  example?: string;
  onFillExample?: () => void;
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 6,
      }}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Text strong style={{ fontSize: 13 }}>
          {title}
        </Text>
        <Tooltip title={hint}>
          <QuestionCircleOutlined style={{ color: '#999', fontSize: 12 }} />
        </Tooltip>
        {example && (
          <Text type="secondary" style={{ fontSize: 11.5, fontFamily: 'monospace' }}>
            例：{example}
          </Text>
        )}
      </span>
      {onFillExample && (
        <Button
          type="link"
          size="small"
          icon={<ThunderboltOutlined />}
          onClick={onFillExample}
          style={{ fontSize: 12, padding: 0, height: 'auto' }}
        >
          填入示例
        </Button>
      )}
    </div>
  );
}

const ROW: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  marginBottom: 6,
};

const SEP: React.CSSProperties = {
  color: '#bbb',
  fontFamily: 'monospace',
  flexShrink: 0,
};

// ---------------------------------------------------------------------------
// 端口映射
// ---------------------------------------------------------------------------

export function PortsEditor({
  value,
  onChange,
  disabled,
  disabledHint,
}: {
  value: PortMapping[];
  onChange: (v: PortMapping[]) => void;
  disabled?: boolean;
  disabledHint?: string;
}) {
  const add = () =>
    onChange([...value, { host_port: 8080, container_port: 80, protocol: 'tcp' }]);
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const patch = (i: number, p: Partial<PortMapping>) =>
    onChange(value.map((x, idx) => (idx === i ? { ...x, ...p } : x)));

  return (
    <div style={{ marginBottom: 18 }}>
      <BlockHead
        title="端口映射"
        hint="把宿主机的端口转发到容器内部端口。访问 localhost:宿主端口 就会打到容器里的容器端口。"
        example="宿主 8080 → 容器 80"
        onFillExample={
          disabled ? undefined : () => onChange([{ host_port: 8080, container_port: 80, protocol: 'tcp' }])
        }
      />
      {disabled ? (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {disabledHint || '当前网络模式下不需要端口映射'}
        </Text>
      ) : (
        <>
          {value.length === 0 && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              暂无端口映射（容器服务将无法从宿主访问）
            </Text>
          )}
          {value.map((p, i) => (
            <div key={i} style={ROW}>
              <Text style={{ fontSize: 11.5, color: '#888', width: 30, flexShrink: 0 }}>宿主</Text>
              <InputNumber
                size="small"
                min={1}
                max={65535}
                value={p.host_port}
                placeholder="8080"
                onChange={(v) => patch(i, { host_port: Number(v) || 0 })}
                status={isValidPort(p.host_port) ? undefined : 'error'}
                style={{ width: 92 }}
              />
              <span style={SEP}>→</span>
              <Text style={{ fontSize: 11.5, color: '#888', width: 30, flexShrink: 0 }}>容器</Text>
              <InputNumber
                size="small"
                min={1}
                max={65535}
                value={p.container_port}
                placeholder="80"
                onChange={(v) => patch(i, { container_port: Number(v) || 0 })}
                status={isValidPort(p.container_port) ? undefined : 'error'}
                style={{ width: 92 }}
              />
              <Select
                size="small"
                value={p.protocol}
                onChange={(v) => patch(i, { protocol: v })}
                options={[
                  { value: 'tcp', label: 'TCP' },
                  { value: 'udp', label: 'UDP' },
                ]}
                style={{ width: 76 }}
              />
              <Button size="small" type="text" danger icon={<CloseOutlined />} onClick={() => remove(i)} />
            </div>
          ))}
          <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={add}>
            添加端口
          </Button>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 环境变量
// ---------------------------------------------------------------------------

export function EnvsEditor({
  value,
  onChange,
}: {
  value: EnvVar[];
  onChange: (v: EnvVar[]) => void;
}) {
  const add = () => onChange([...value, { key: '', value: '' }]);
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const patch = (i: number, p: Partial<EnvVar>) =>
    onChange(value.map((x, idx) => (idx === i ? { ...x, ...p } : x)));

  return (
    <div style={{ marginBottom: 18 }}>
      <BlockHead
        title="环境变量"
        hint="传给容器内进程的环境变量。变量名只能包含字母、数字、下划线，且不能以数字开头。"
        example="TZ = Asia/Shanghai"
        onFillExample={() => onChange([{ key: 'TZ', value: 'Asia/Shanghai' }])}
      />
      {value.length === 0 && (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
          暂无环境变量
        </Text>
      )}
      {value.map((e, i) => (
        <div key={i} style={ROW}>
          <Input
            size="small"
            value={e.key}
            placeholder="TZ"
            onChange={(ev) => patch(i, { key: ev.target.value })}
            status={!e.key || isValidEnvKey(e.key) ? undefined : 'error'}
            style={{ width: 180, fontFamily: 'monospace' }}
          />
          <span style={SEP}>=</span>
          <Input
            size="small"
            value={e.value}
            placeholder="Asia/Shanghai"
            onChange={(ev) => patch(i, { value: ev.target.value })}
            style={{ flex: 1, fontFamily: 'monospace' }}
          />
          <Button size="small" type="text" danger icon={<CloseOutlined />} onClick={() => remove(i)} />
        </div>
      ))}
      <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={add}>
        添加变量
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 卷挂载
// ---------------------------------------------------------------------------

export function VolumesEditor({
  value,
  onChange,
}: {
  value: VolumeMapping[];
  onChange: (v: VolumeMapping[]) => void;
}) {
  const add = () =>
    onChange([...value, { host_path: '', container_path: '', read_only: false }]);
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const patch = (i: number, p: Partial<VolumeMapping>) =>
    onChange(value.map((x, idx) => (idx === i ? { ...x, ...p } : x)));

  return (
    <div style={{ marginBottom: 18 }}>
      <BlockHead
        title="目录挂载"
        hint="把宿主机目录（或 Docker 命名卷）挂到容器里。宿主侧可填绝对路径 /data/app，也可填命名卷 appdata（由 Docker 托管）。容器侧必须是绝对路径。"
        example="/tmp/site → /usr/share/nginx/html"
        onFillExample={() =>
          onChange([{ host_path: '/tmp/site', container_path: '/usr/share/nginx/html', read_only: true }])
        }
      />
      {value.length === 0 && (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
          暂无挂载（容器内数据在删除后会丢失）
        </Text>
      )}
      {value.map((v, i) => (
        <div key={i} style={ROW}>
          <Input
            size="small"
            value={v.host_path}
            placeholder="/data/app 或 appdata"
            onChange={(e) => patch(i, { host_path: e.target.value })}
            status={!v.host_path || isValidHostPath(v.host_path) ? undefined : 'error'}
            style={{ flex: 1, fontFamily: 'monospace' }}
          />
          <span style={SEP}>→</span>
          <Input
            size="small"
            value={v.container_path}
            placeholder="/app"
            onChange={(e) => patch(i, { container_path: e.target.value })}
            status={!v.container_path || isAbsPath(v.container_path) ? undefined : 'error'}
            style={{ flex: 1, fontFamily: 'monospace' }}
          />
          <Segmented
            size="small"
            value={v.read_only ? 'ro' : 'rw'}
            onChange={(val) => patch(i, { read_only: val === 'ro' })}
            options={[
              { label: '读写', value: 'rw' },
              { label: '只读', value: 'ro' },
            ]}
          />
          <Button size="small" type="text" danger icon={<CloseOutlined />} onClick={() => remove(i)} />
        </div>
      ))}
      <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={add}>
        添加挂载
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 网络模式
// ---------------------------------------------------------------------------

export const NETWORK_OPTIONS = [
  { value: 'bridge', label: 'bridge — 默认，通过端口映射访问' },
  { value: 'host', label: 'host — 共享宿主网络，无需映射端口' },
  { value: 'none', label: 'none — 完全无网络' },
];

export function NetworkSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div style={{ marginBottom: 18 }}>
      <BlockHead
        title="网络模式"
        hint="bridge 是默认模式，容器有独立网络栈，需要端口映射才能从宿主访问。host 让容器直接共享宿主网络（端口映射失效）。none 断网。"
        example="bridge"
      />
      <Select
        size="small"
        value={value}
        onChange={onChange}
        options={NETWORK_OPTIONS}
        style={{ width: '100%', maxWidth: 380 }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// 重启策略
// ---------------------------------------------------------------------------

export const RESTART_OPTIONS = [
  { value: 'no', label: '不重启' },
  { value: 'always', label: '总是重启' },
  { value: 'on-failure', label: '失败时重启' },
  { value: 'unless-stopped', label: '除手动停止外' },
];

export function RestartSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <BlockHead
        title="重启策略"
        hint="容器退出后 Docker 是否自动拉起。长期服务建议 unless-stopped；一次性任务用「不重启」。"
        example="unless-stopped"
      />
      <Select
        size="small"
        value={value}
        onChange={onChange}
        options={RESTART_OPTIONS}
        style={{ width: '100%', maxWidth: 380 }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// docker run 命令预览
// ---------------------------------------------------------------------------

export function CommandPreview({
  image,
  name,
  command,
  ports,
  envs,
  volumes,
  restart,
  network,
}: {
  image: string;
  name?: string;
  command?: string;
  ports: PortMapping[];
  envs: EnvVar[];
  volumes: VolumeMapping[];
  restart: string;
  network?: string;
}) {
  const parts = ['docker run -d'];
  if (name) parts.push(`--name ${name}`);
  if (network && network !== 'bridge') parts.push(`--network ${network}`);
  if (network !== 'host') {
    ports.forEach((p) =>
      parts.push(`-p ${p.host_port}:${p.container_port}${p.protocol === 'udp' ? '/udp' : ''}`),
    );
  }
  envs.filter((e) => e.key).forEach((e) => parts.push(`-e ${e.key}=${e.value}`));
  volumes
    .filter((v) => v.host_path && v.container_path)
    .forEach((v) =>
      parts.push(`-v ${v.host_path}:${v.container_path}${v.read_only ? ':ro' : ''}`),
    );
  if (restart && restart !== 'no') parts.push(`--restart ${restart}`);
  parts.push(image || '<镜像>');
  if (command) parts.push(command);

  return (
    <div
      style={{
        background: '#1a1918',
        color: '#a6e3a1',
        padding: '10px 12px',
        borderRadius: 8,
        fontSize: 11.5,
        fontFamily: "'JetBrains Mono', monospace",
        wordBreak: 'break-all',
        lineHeight: 1.6,
      }}
    >
      <Text style={{ color: '#666', fontSize: 11, display: 'block', marginBottom: 4 }}>
        等价命令预览
      </Text>
      {parts.join(' ')}
    </div>
  );
}
