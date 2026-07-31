/**
 * 容器配置字段 — 端口 / 环境变量 / 目录映射 / 网络 / 重启策略.
 *
 * 采用行式结构化编辑（Form.List 风格），对外仍以后端所需的 string[] 形式序列化。
 * 提供 parse* / serialize* 工具函数，供创建 Modal 与模板回填互转。
 */
import { useMemo } from 'react';
import { Button, Input, Radio, Select, Tooltip, Typography } from 'antd';
import { CloseOutlined, PlusOutlined } from '@ant-design/icons';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// 结构化类型
// ---------------------------------------------------------------------------

export interface PortMapping {
  hostPort: string;
  containerPort: string;
  protocol: 'tcp' | 'udp';
}

export interface EnvVar {
  key: string;
  value: string;
}

export interface VolumeMapping {
  hostPath: string;
  containerPath: string;
  mode: 'rw' | 'ro';
}

export interface ContainerConfig {
  ports: PortMapping[];
  envs: EnvVar[];
  volumes: VolumeMapping[];
  network: string;
  restartPolicy: string;
}

export function emptyConfig(): ContainerConfig {
  return {
    ports: [],
    envs: [],
    volumes: [],
    network: 'bridge',
    restartPolicy: 'no',
  };
}

// ---------------------------------------------------------------------------
// 序列化 / 反序列化（后端 string[] ↔ 前端结构化）
// ---------------------------------------------------------------------------

const RE_PORT = /^(\d+):(\d+)(?:\/(tcp|udp))?$/i;
const RE_VOLUME = /^([^:]+):([^:]+)(?::(ro|rw))?$/i;

export function parsePorts(raw: string[] | undefined): PortMapping[] {
  if (!raw) return [];
  return raw
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const m = s.match(RE_PORT);
      if (m) {
        return {
          hostPort: m[1],
          containerPort: m[2],
          protocol: ((m[3] || 'tcp').toLowerCase() as 'tcp' | 'udp'),
        };
      }
      // fallback：整段塞到 hostPort，让用户看到并修
      return { hostPort: s, containerPort: '', protocol: 'tcp' as const };
    });
}

/** 解析 `docker ps` 端口字符串，如 "0.0.0.0:4096->4096/tcp, :::4096->4096/tcp"。 */
export function parsePortsFromContainer(raw: string | undefined): PortMapping[] {
  if (!raw) return [];
  const seen = new Set<string>();
  const items: PortMapping[] = [];
  const re = /(?:[\d.:]+:)?(\d+)->(\d+)\/(tcp|udp)/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(raw))) {
    const key = `${m[1]}:${m[2]}/${m[3]}`;
    if (seen.has(key)) continue;
    seen.add(key);
    items.push({
      hostPort: m[1],
      containerPort: m[2],
      protocol: m[3].toLowerCase() as 'tcp' | 'udp',
    });
  }
  return items;
}

export function serializePorts(items: PortMapping[]): string[] {
  return items
    .filter((p) => p.hostPort && p.containerPort)
    .map((p) => {
      const base = `${p.hostPort.trim()}:${p.containerPort.trim()}`;
      return p.protocol === 'udp' ? `${base}/udp` : base;
    });
}

export function parseEnvs(raw: string[] | undefined): EnvVar[] {
  if (!raw) return [];
  return raw
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const idx = s.indexOf('=');
      if (idx < 0) return { key: s, value: '' };
      return { key: s.slice(0, idx), value: s.slice(idx + 1) };
    });
}

export function serializeEnvs(items: EnvVar[]): string[] {
  return items
    .filter((e) => e.key.trim())
    .map((e) => `${e.key.trim()}=${e.value}`);
}

export function parseVolumes(raw: string[] | undefined): VolumeMapping[] {
  if (!raw) return [];
  return raw
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const m = s.match(RE_VOLUME);
      if (m) {
        return {
          hostPath: m[1],
          containerPath: m[2],
          mode: ((m[3] || 'rw').toLowerCase() as 'rw' | 'ro'),
        };
      }
      return { hostPath: s, containerPath: '', mode: 'rw' as const };
    });
}

/** 解析后端返回的容器 volumes 字符串，形如 "/data:/app:rw, vol→/x(ro)"。 */
export function parseVolumesFromContainer(raw: string | undefined): VolumeMapping[] {
  if (!raw) return [];
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      // 命名卷格式 "vol→/dst" 或 "vol→/dst(mode)"
      const arrow = s.match(/^([^→]+)→([^(]+)(?:\(([^)]+)\))?$/);
      if (arrow) {
        const mode = (arrow[3] || '').toLowerCase();
        return {
          hostPath: arrow[1].trim(),
          containerPath: arrow[2].trim(),
          mode: mode === 'ro' ? 'ro' : 'rw',
        };
      }
      const m = s.match(RE_VOLUME);
      if (m) {
        return {
          hostPath: m[1],
          containerPath: m[2],
          mode: ((m[3] || 'rw').toLowerCase() as 'rw' | 'ro'),
        };
      }
      return { hostPath: s, containerPath: '', mode: 'rw' as const };
    });
}

export function serializeVolumes(items: VolumeMapping[]): string[] {
  return items
    .filter((v) => v.hostPath && v.containerPath)
    .map((v) => {
      const base = `${v.hostPath.trim()}:${v.containerPath.trim()}`;
      return v.mode === 'ro' ? `${base}:ro` : base;
    });
}

// ---------------------------------------------------------------------------
// 校验规则
// ---------------------------------------------------------------------------

const RE_ENV_KEY = /^[A-Za-z_][A-Za-z0-9_]*$/;

function isPortNumber(v: string): boolean {
  if (!/^\d+$/.test(v)) return false;
  const n = Number(v);
  return n >= 1 && n <= 65535;
}

function isValidContainerPath(v: string): boolean {
  return v.startsWith('/') && v.length > 1;
}

function isValidHostPath(v: string): boolean {
  // 绝对路径 或 命名卷（首字符字母数字）
  return v.startsWith('/') || /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(v);
}

// ---------------------------------------------------------------------------
// UI 组件
// ---------------------------------------------------------------------------

const NETWORK_OPTIONS = [
  { value: 'bridge', label: 'bridge · 默认，NAT 到宿主' },
  { value: 'host', label: 'host · 共享宿主网络栈' },
  { value: 'none', label: 'none · 无网络' },
];

interface Props {
  value: ContainerConfig;
  onChange: (next: ContainerConfig) => void;
}

export default function ContainerConfigFields({ value, onChange }: Props) {
  const isHost = value.network === 'host';

  const set = (patch: Partial<ContainerConfig>) => onChange({ ...value, ...patch });

  // 端口
  const addPort = () =>
    set({ ports: [...value.ports, { hostPort: '', containerPort: '', protocol: 'tcp' }] });
  const removePort = (i: number) => set({ ports: value.ports.filter((_, idx) => idx !== i) });
  const updatePort = (i: number, patch: Partial<PortMapping>) =>
    set({ ports: value.ports.map((p, idx) => (idx === i ? { ...p, ...patch } : p)) });

  // 环境变量
  const addEnv = () => set({ envs: [...value.envs, { key: '', value: '' }] });
  const removeEnv = (i: number) => set({ envs: value.envs.filter((_, idx) => idx !== i) });
  const updateEnv = (i: number, patch: Partial<EnvVar>) =>
    set({ envs: value.envs.map((e, idx) => (idx === i ? { ...e, ...patch } : e)) });

  // 挂载
  const addVolume = () =>
    set({ volumes: [...value.volumes, { hostPath: '', containerPath: '', mode: 'rw' }] });
  const removeVolume = (i: number) =>
    set({ volumes: value.volumes.filter((_, idx) => idx !== i) });
  const updateVolume = (i: number, patch: Partial<VolumeMapping>) =>
    set({ volumes: value.volumes.map((v, idx) => (idx === i ? { ...v, ...patch } : v)) });

  const portErrors = useMemo(() => value.ports.map((p) => {
    const hErr = !p.hostPort ? '' : (isPortNumber(p.hostPort) ? '' : '1-65535');
    const cErr = !p.containerPort ? '' : (isPortNumber(p.containerPort) ? '' : '1-65535');
    return { hostPort: hErr, containerPort: cErr };
  }), [value.ports]);

  const envErrors = useMemo(() => value.envs.map((e) => ({
    key: e.key && !RE_ENV_KEY.test(e.key) ? '仅字母/数字/下划线，且不能数字开头' : '',
  })), [value.envs]);

  const volumeErrors = useMemo(() => value.volumes.map((v) => ({
    hostPath: v.hostPath && !isValidHostPath(v.hostPath) ? '需绝对路径或命名卷' : '',
    containerPath: v.containerPath && !isValidContainerPath(v.containerPath) ? '需绝对路径 /...' : '',
  })), [value.volumes]);

  return (
    <div className="cfg-fields">
      {/* 端口映射 */}
      <div className="cfg-block">
        <div className="cfg-block-head">
          <span className="cfg-block-title">端口映射</span>
          {isHost && (
            <Text style={{ fontSize: 11, color: 'var(--ink-40)' }}>
              host 模式下容器直接使用宿主网络，端口无需映射
            </Text>
          )}
        </div>
        <div className={isHost ? 'cfg-block-body cfg-block-body--disabled' : 'cfg-block-body'}>
          {value.ports.length === 0 && !isHost && (
            <Text style={{ fontSize: 12, color: 'var(--ink-30)' }}>暂无端口映射</Text>
          )}
          {value.ports.map((p, i) => (
            <div key={i} className="cfg-row cfg-row--port">
              <Input
                size="small"
                placeholder="宿主端口"
                value={p.hostPort}
                disabled={isHost}
                status={portErrors[i]?.hostPort ? 'error' : undefined}
                onChange={(e) => updatePort(i, { hostPort: e.target.value })}
                style={{ width: 110, fontFamily: 'var(--font-mono)' }}
              />
              <span className="cfg-sep">:</span>
              <Input
                size="small"
                placeholder="容器端口"
                value={p.containerPort}
                disabled={isHost}
                status={portErrors[i]?.containerPort ? 'error' : undefined}
                onChange={(e) => updatePort(i, { containerPort: e.target.value })}
                style={{ width: 110, fontFamily: 'var(--font-mono)' }}
              />
              <Select
                size="small"
                value={p.protocol}
                disabled={isHost}
                onChange={(v) => updatePort(i, { protocol: v })}
                options={[{ value: 'tcp', label: 'TCP' }, { value: 'udp', label: 'UDP' }]}
                style={{ width: 74 }}
              />
              <Button
                size="small" type="text" danger
                icon={<CloseOutlined />}
                disabled={isHost}
                onClick={() => removePort(i)}
              />
            </div>
          ))}
          <Button
            size="small" type="dashed"
            icon={<PlusOutlined />}
            onClick={addPort}
            disabled={isHost}
            style={{ marginTop: 4 }}
          >
            添加端口
          </Button>
        </div>
      </div>

      {/* 环境变量 */}
      <div className="cfg-block">
        <div className="cfg-block-head">
          <span className="cfg-block-title">环境变量</span>
        </div>
        <div className="cfg-block-body">
          {value.envs.length === 0 && (
            <Text style={{ fontSize: 12, color: 'var(--ink-30)' }}>暂无环境变量</Text>
          )}
          {value.envs.map((e, i) => (
            <div key={i} className="cfg-row cfg-row--env">
              <Input
                size="small"
                placeholder="KEY"
                value={e.key}
                status={envErrors[i]?.key ? 'error' : undefined}
                onChange={(ev) => updateEnv(i, { key: ev.target.value })}
                style={{ width: 180, fontFamily: 'var(--font-mono)' }}
              />
              <span className="cfg-sep">=</span>
              <Input
                size="small"
                placeholder="VALUE"
                value={e.value}
                onChange={(ev) => updateEnv(i, { value: ev.target.value })}
                style={{ flex: 1, fontFamily: 'var(--font-mono)' }}
              />
              <Button
                size="small" type="text" danger
                icon={<CloseOutlined />}
                onClick={() => removeEnv(i)}
              />
            </div>
          ))}
          <Button
            size="small" type="dashed"
            icon={<PlusOutlined />}
            onClick={addEnv}
            style={{ marginTop: 4 }}
          >
            添加环境变量
          </Button>
        </div>
      </div>

      {/* 目录映射 */}
      <div className="cfg-block">
        <div className="cfg-block-head">
          <span className="cfg-block-title">目录映射</span>
          <Text style={{ fontSize: 11, color: 'var(--ink-40)' }}>
            支持绝对路径（如 /data/app）或命名卷（如 pgdata）
          </Text>
        </div>
        <div className="cfg-block-body">
          {value.volumes.length === 0 && (
            <Text style={{ fontSize: 12, color: 'var(--ink-30)' }}>暂无挂载</Text>
          )}
          {value.volumes.map((v, i) => (
            <div key={i} className="cfg-row cfg-row--volume">
              <Input
                size="small"
                placeholder="宿主路径 / 命名卷"
                value={v.hostPath}
                status={volumeErrors[i]?.hostPath ? 'error' : undefined}
                onChange={(e) => updateVolume(i, { hostPath: e.target.value })}
                style={{ flex: 1, fontFamily: 'var(--font-mono)' }}
              />
              <span className="cfg-sep">:</span>
              <Input
                size="small"
                placeholder="容器路径 /..."
                value={v.containerPath}
                status={volumeErrors[i]?.containerPath ? 'error' : undefined}
                onChange={(e) => updateVolume(i, { containerPath: e.target.value })}
                style={{ flex: 1, fontFamily: 'var(--font-mono)' }}
              />
              <Radio.Group
                size="small"
                value={v.mode}
                onChange={(e) => updateVolume(i, { mode: e.target.value })}
              >
                <Radio.Button value="rw">rw</Radio.Button>
                <Radio.Button value="ro">ro</Radio.Button>
              </Radio.Group>
              <Button
                size="small" type="text" danger
                icon={<CloseOutlined />}
                onClick={() => removeVolume(i)}
              />
            </div>
          ))}
          <Button
            size="small" type="dashed"
            icon={<PlusOutlined />}
            onClick={addVolume}
            style={{ marginTop: 4 }}
          >
            添加挂载
          </Button>
        </div>
      </div>

      {/* 网络模式 */}
      <div className="cfg-block cfg-block--inline">
        <span className="cfg-block-title">网络模式</span>
        <Tooltip title="选到 host 后容器直接使用宿主网络栈，端口映射不再生效">
          <Select
            size="small"
            value={value.network}
            onChange={(v) => set({ network: v })}
            options={NETWORK_OPTIONS}
            style={{ width: 260 }}
          />
        </Tooltip>
      </div>

      {/* 重启策略 */}
      <div className="cfg-block cfg-block--inline">
        <span className="cfg-block-title">重启策略</span>
        <Radio.Group
          value={value.restartPolicy}
          onChange={(e) => set({ restartPolicy: e.target.value })}
        >
          <Radio.Button value="no">不重启</Radio.Button>
          <Radio.Button value="always">始终</Radio.Button>
          <Radio.Button value="on-failure">失败时</Radio.Button>
          <Radio.Button value="unless-stopped">除非手动停止</Radio.Button>
        </Radio.Group>
      </div>
    </div>
  );
}
