/**
 * 容器表单弹窗 — 新建 / 修改配置共用。
 *
 * 交互设计要点：
 * - 新建时先选「预设」，一键把镜像/端口/挂载/环境变量全套填好，避免从零手写
 * - 修改时用后端返回的结构化配置回填（不再解析 inspect 的驼峰/下划线，那是原来回填空白的根因）
 * - 每个输入都有 placeholder + 示例 + 一键填示例
 * - 底部实时显示等价 docker run 命令，所见即所得
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  App,
  Divider,
  Input,
  Modal,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';
import { AppstoreOutlined } from '@ant-design/icons';
import useComputeStore, { extractErrMsg } from '../../stores/computeStore';
import type {
  ContainerInfo,
  ContainerPreset,
  EnvVar,
  PortMapping,
  RestartPolicy,
  VolumeMapping,
} from '../../types/compute';
import {
  CommandPreview,
  EnvsEditor,
  NetworkSelect,
  PortsEditor,
  RestartSelect,
  VolumesEditor,
  validateContainerConfig,
} from './ContainerConfigEditor';

const { Text } = Typography;

interface FormState {
  image: string;
  name: string;
  command: string;
  ports: PortMapping[];
  envs: EnvVar[];
  volumes: VolumeMapping[];
  restart: RestartPolicy;
  network: string;
}

const EMPTY: FormState = {
  image: '',
  name: '',
  command: '',
  ports: [],
  envs: [],
  volumes: [],
  restart: 'no',
  network: 'bridge',
};

function fromContainer(c: ContainerInfo): FormState {
  return {
    image: c.image.split(',')[0].trim(),
    name: c.name,
    command: c.command || '',
    ports: c.port_mappings ?? [],
    envs: c.env_vars ?? [],
    volumes: c.volume_mappings ?? [],
    restart: c.restart || 'no',
    network: c.network || 'bridge',
  };
}

function fromPreset(p: ContainerPreset): FormState {
  return {
    image: p.image,
    name: p.id === 'blank' ? '' : p.id,
    command: p.command || '',
    ports: p.ports ?? [],
    envs: p.envs ?? [],
    volumes: p.volumes ?? [],
    restart: p.restart || 'no',
    network: p.network || 'bridge',
  };
}

interface Props {
  open: boolean;
  /** 传入则为「修改配置」模式 */
  editing: ContainerInfo | null;
  /** 新建模式下预填的镜像（从镜像列表点「用它建容器」时传入） */
  prefillImage?: string;
  onClose: () => void;
}

export default function ContainerFormModal({ open, editing, prefillImage, onClose }: Props) {
  const { notification } = App.useApp();
  const {
    presets,
    fetchPresets,
    images,
    createContainer,
    updateContainer,
  } = useComputeStore();

  const [form, setForm] = useState<FormState>(EMPTY);
  const [presetId, setPresetId] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);

  const isEdit = !!editing;

  useEffect(() => {
    if (!open) return;
    void fetchPresets();
    if (editing) {
      setForm(fromContainer(editing));
      setPresetId(undefined);
    } else {
      // 从镜像列表进来时预填镜像，并按镜像名猜一个容器名
      setForm(
        prefillImage
          ? {
              ...EMPTY,
              image: prefillImage,
              name: prefillImage
                .split('/')
                .pop()!
                .replace(/[:.]/g, '-')
                .toLowerCase(),
            }
          : EMPTY,
      );
      setPresetId(undefined);
    }
  }, [open, editing, prefillImage, fetchPresets]);

  const patch = (p: Partial<FormState>) => setForm((s) => ({ ...s, ...p }));

  const applyPreset = (id: string) => {
    setPresetId(id);
    const p = presets.find((x) => x.id === id);
    if (p) setForm(fromPreset(p));
  };

  const errors = useMemo(() => validateContainerConfig(form), [form]);

  // 本地已有镜像，做成下拉可选（避免手打错 tag）
  const imageOptions = useMemo(
    () =>
      images
        .flatMap((i) => i.tags)
        .filter((t) => t && !t.startsWith('<none>'))
        .map((t) => ({ value: t, label: t })),
    [images],
  );

  const submit = async () => {
    if (!form.image.trim()) {
      notification.warning({ title: '请填写镜像', description: '例如 nginx:1.27-alpine' });
      return;
    }
    if (errors.length > 0) {
      notification.warning({ title: '配置有误', description: errors[0] });
      return;
    }
    setSubmitting(true);
    try {
      const isHost = form.network === 'host';
      const payload = {
        image: form.image.trim(),
        name: form.name.trim() || undefined,
        command: form.command.trim() || undefined,
        ports: isHost ? [] : form.ports,
        envs: form.envs.filter((e) => e.key.trim()),
        volumes: form.volumes.filter((v) => v.host_path && v.container_path),
        restart: form.restart,
        network: form.network,
      };

      if (isEdit && editing) {
        await updateContainer(editing.id, payload);
        notification.success({
          title: '容器已按新配置重建',
          description: `${form.name}：端口/挂载/环境变量已生效`,
        });
      } else {
        const created = await createContainer({ ...payload, auto_pull: true, start: true });
        notification.success({
          title: '容器已创建并启动',
          description: `${created.name} · ${created.ports || '无端口映射'}`,
        });
      }
      onClose();
    } catch (err) {
      notification.error({
        title: isEdit ? '重建失败' : '创建失败',
        description: extractErrMsg(err),
        duration: 8,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={isEdit ? `修改容器配置 · ${editing?.name}` : '新建容器'}
      open={open}
      onOk={submit}
      onCancel={onClose}
      confirmLoading={submitting}
      okText={isEdit ? '停止并重建' : '创建并启动'}
      width={680}
      destroyOnHidden
      styles={{ body: { maxHeight: '68vh', overflowY: 'auto', paddingRight: 8 } }}
    >
      {isEdit && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="Docker 不支持热改端口 / 挂载 / 网络"
          description="保存后会「停止 → 删除 → 按新配置重建」。挂载卷里的数据不受影响，容器内其他文件会丢失。原来在运行的容器会自动重新启动。"
        />
      )}

      {!isEdit && (
        <>
          <div style={{ marginBottom: 6 }}>
            <Space size={6}>
              <AppstoreOutlined style={{ color: '#0071e3' }} />{/* 【UI 重构】Apple Blue */}
              <Text strong style={{ fontSize: 13 }}>
                从预设开始（推荐）
              </Text>
              <Text type="secondary" style={{ fontSize: 11.5 }}>
                选一个就自动填好镜像、端口、挂载、环境变量
              </Text>
            </Space>
          </div>
          <Select
            style={{ width: '100%', marginBottom: 8 }}
            placeholder="选择一个预设，或直接跳过手动配置"
            value={presetId}
            onChange={applyPreset}
            optionLabelProp="label"
            options={presets.map((p) => ({
              value: p.id,
              label: p.name,
              title: p.description,
            }))}
          />
          {presetId && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              {presets.find((p) => p.id === presetId)?.description}
            </Text>
          )}
          <Divider style={{ margin: '12px 0' }} />
        </>
      )}

      {/* 镜像 */}
      <div style={{ marginBottom: 14 }}>
        <Text strong style={{ fontSize: 13 }}>
          镜像 <Text type="danger">*</Text>
        </Text>
        <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
          例：nginx:1.27-alpine
        </Text>
        <Select
          showSearch
          allowClear
          mode="tags"
          maxCount={1}
          size="small"
          style={{ width: '100%', marginTop: 4 }}
          placeholder="从本地镜像选择，或直接输入镜像名"
          value={form.image ? [form.image] : []}
          onChange={(v) => patch({ image: (v as string[])[0] ?? '' })}
          options={imageOptions}
        />
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 3 }}>
          本地不存在时会自动拉取（无外网会在 15 分钟后超时并提示）
        </Text>
      </div>

      {/* 容器名 */}
      <div style={{ marginBottom: 14 }}>
        <Text strong style={{ fontSize: 13 }}>
          容器名称
        </Text>
        <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
          例：my-nginx
        </Text>
        <Input
          size="small"
          style={{ marginTop: 4, fontFamily: 'monospace' }}
          placeholder="留空则由 Docker 随机生成"
          value={form.name}
          onChange={(e) => patch({ name: e.target.value })}
        />
      </div>

      {/* 启动命令 */}
      <div style={{ marginBottom: 18 }}>
        <Text strong style={{ fontSize: 13 }}>
          启动命令
        </Text>
        <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
          例：redis-server --appendonly yes
        </Text>
        <Input
          size="small"
          style={{ marginTop: 4, fontFamily: 'monospace' }}
          placeholder="留空则用镜像默认 CMD"
          value={form.command}
          onChange={(e) => patch({ command: e.target.value })}
        />
      </div>

      <PortsEditor
        value={form.ports}
        onChange={(ports) => patch({ ports })}
        disabled={form.network === 'host'}
        disabledHint="host 网络下容器直接使用宿主端口，无需也不能配置映射"
      />
      <EnvsEditor value={form.envs} onChange={(envs) => patch({ envs })} />
      <VolumesEditor value={form.volumes} onChange={(volumes) => patch({ volumes })} />
      <NetworkSelect value={form.network} onChange={(network) => patch({ network })} />
      <RestartSelect
        value={form.restart}
        onChange={(restart) => patch({ restart: restart as RestartPolicy })}
      />

      {errors.length > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 12 }}
          title="请先修正以下问题"
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {errors.slice(0, 5).map((e) => (
                <li key={e} style={{ fontSize: 12 }}>
                  {e}
                </li>
              ))}
            </ul>
          }
        />
      )}

      <CommandPreview
        image={form.image}
        name={form.name}
        command={form.command}
        ports={form.ports}
        envs={form.envs}
        volumes={form.volumes}
        restart={form.restart}
        network={form.network}
      />

      {isEdit && editing && (
        <div style={{ marginTop: 10 }}>
          <Space size={6} wrap>
            <Tag>当前状态：{editing.status}</Tag>
            {editing.exit_code != null && editing.status !== 'running' && (
              <Tag color={editing.exit_code === 0 ? 'default' : 'error'}>
                上次退出码 {editing.exit_code}
              </Tag>
            )}
          </Space>
        </div>
      )}
    </Modal>
  );
}
