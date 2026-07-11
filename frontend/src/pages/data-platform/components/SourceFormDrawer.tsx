import { useEffect, useMemo, useState } from 'react';
import {
  Drawer,
  Form,
  Input,
  InputNumber,
  Segmented,
  Switch,
  Space,
  Button,
  message,
} from 'antd';
import type { AxiosError } from 'axios';
import type {
  DpDataSource,
  DpDataSourceCreate,
  DpDataSourceUpdate,
  DpDialect,
} from '../../../types/dataPlatform';
import useDataPlatformStore from '../../../stores/dataPlatformStore';
import { dataPlatformService } from '../../../services/dataPlatform.service';

const { TextArea } = Input;

type Mode = 'create' | 'edit';

type SegmentedType = 'MySQL' | 'PostgreSQL' | 'SQLite';

interface DialectMeta {
  source_type: string;
  dialect: DpDialect;
  defaultPort: number | null;
  hidesHost: boolean;
  showsSchema: boolean;
}

const DIALECT_META: Record<SegmentedType, DialectMeta> = {
  MySQL: {
    source_type: 'mysql',
    dialect: 'mysql',
    defaultPort: 3306,
    hidesHost: false,
    showsSchema: false,
  },
  PostgreSQL: {
    source_type: 'postgresql',
    dialect: 'postgresql',
    defaultPort: 5432,
    hidesHost: false,
    showsSchema: true,
  },
  SQLite: {
    source_type: 'sqlite',
    dialect: 'sqlite',
    defaultPort: null,
    hidesHost: true,
    showsSchema: false,
  },
};

function dialectToSegmented(d: DpDialect | undefined): SegmentedType {
  if (d === 'postgresql') return 'PostgreSQL';
  if (d === 'sqlite') return 'SQLite';
  return 'MySQL';
}

interface FormValues {
  name: string;
  segmented_type: SegmentedType;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  database: string;
  default_schema?: string;
  charset?: string;
  description?: string;
  read_only_flag: boolean;
}

export interface SourceFormDrawerProps {
  open: boolean;
  mode: Mode;
  initial?: DpDataSource | null;
  onClose: () => void;
  onSaved?: (row?: DpDataSource) => void;
}

export default function SourceFormDrawer({
  open,
  mode,
  initial,
  onClose,
  onSaved,
}: SourceFormDrawerProps) {
  const [form] = Form.useForm<FormValues>();
  const [submitting, setSubmitting] = useState(false);
  const createSource = useDataPlatformStore((s) => s.createSource);
  const fetchSources = useDataPlatformStore((s) => s.fetchSources);

  const [segmentedType, setSegmentedType] = useState<SegmentedType>('MySQL');
  const meta = useMemo(() => DIALECT_META[segmentedType], [segmentedType]);

  // Reset form when drawer opens / initial changes.
  useEffect(() => {
    if (!open) return;
    if (mode === 'edit' && initial) {
      const seg = dialectToSegmented(initial.dialect);
      setSegmentedType(seg);
      form.setFieldsValue({
        name: initial.name,
        segmented_type: seg,
        host: initial.host ?? undefined,
        port: initial.port ?? undefined,
        username: initial.username ?? undefined,
        password: '',
        database: initial.database,
        default_schema: initial.defaultSchema ?? undefined,
        charset: initial.charset ?? 'utf8mb4',
        description: initial.description ?? undefined,
        read_only_flag: initial.readOnlyFlag,
      });
    } else {
      const seg: SegmentedType = 'MySQL';
      setSegmentedType(seg);
      form.resetFields();
      form.setFieldsValue({
        segmented_type: seg,
        port: DIALECT_META[seg].defaultPort ?? undefined,
        charset: 'utf8mb4',
        read_only_flag: true,
      });
    }
  }, [open, mode, initial, form]);

  const handleTypeChange = (val: SegmentedType) => {
    setSegmentedType(val);
    const nextMeta = DIALECT_META[val];
    // reset port to sensible default per dialect
    form.setFieldsValue({
      port: nextMeta.defaultPort ?? undefined,
      segmented_type: val,
    });
  };

  const handleClose = () => {
    form.resetFields();
    onClose();
  };

  const handleSubmit = async () => {
    let values: FormValues;
    try {
      values = await form.validateFields();
    } catch {
      // antd form validation error — no toast
      return;
    }
    setSubmitting(true);
    try {
      const nextMeta = DIALECT_META[values.segmented_type];
      const basePayload: DpDataSourceCreate = {
        name: values.name.trim(),
        source_type: nextMeta.source_type,
        dialect: nextMeta.dialect,
        database: values.database.trim(),
        charset: values.charset ?? 'utf8mb4',
        description: values.description ?? null,
        read_only_flag: values.read_only_flag,
      };
      if (!nextMeta.hidesHost) {
        basePayload.host = values.host ?? null;
        basePayload.port = values.port ?? null;
        basePayload.username = values.username ?? null;
      } else {
        basePayload.host = null;
        basePayload.port = null;
        basePayload.username = null;
      }
      if (nextMeta.showsSchema) {
        basePayload.default_schema = values.default_schema ?? null;
      }

      if (mode === 'create') {
        if (!values.password) {
          form.setFields([
            { name: 'password', errors: ['请输入密码'] },
          ]);
          setSubmitting(false);
          return;
        }
        basePayload.password = values.password;
        const row = await createSource(basePayload);
        message.success('数据源创建成功');
        onSaved?.(row);
        handleClose();
      } else if (mode === 'edit' && initial) {
        const patch: DpDataSourceUpdate = { ...basePayload };
        if (values.password) {
          patch.password = values.password;
        } else {
          delete patch.password;
        }
        const row = await dataPlatformService.updateSource(initial.id, patch);
        await fetchSources();
        message.success('数据源已更新');
        onSaved?.(row);
        handleClose();
      }
    } catch (err: unknown) {
      const axErr = err as AxiosError<{ message?: string; detail?: { message?: string } }>;
      const msg =
        axErr.response?.data?.message ??
        axErr.response?.data?.detail?.message ??
        (err instanceof Error ? err.message : '保存失败');
      message.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const title =
    mode === 'create'
      ? '新建数据源'
      : `编辑数据源: ${initial?.name ?? ''}`;

  return (
    <Drawer
      title={title}
      open={open}
      width={520}
      onClose={handleClose}
      destroyOnHidden
      maskClosable={!submitting}
      extra={
        <Space>
          <Button onClick={handleClose} disabled={submitting}>
            取消
          </Button>
          <Button type="primary" onClick={handleSubmit} loading={submitting}>
            {mode === 'create' ? '创建' : '保存'}
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        autoComplete="off"
        initialValues={{
          segmented_type: 'MySQL',
          charset: 'utf8mb4',
          read_only_flag: true,
          port: 3306,
        }}
      >
        <Form.Item
          name="name"
          label="名称"
          rules={[
            { required: true, message: '请输入名称' },
            { min: 1, max: 128, message: '名称长度需在 1-128 字符之间' },
          ]}
        >
          <Input placeholder="例如：生产环境 · 主库" maxLength={128} />
        </Form.Item>

        <Form.Item name="segmented_type" label="类型">
          <Segmented<SegmentedType>
            options={['MySQL', 'PostgreSQL', 'SQLite']}
            value={segmentedType}
            onChange={handleTypeChange}
            block
          />
        </Form.Item>

        {!meta.hidesHost && (
          <>
            <Form.Item
              name="host"
              label="主机地址"
              rules={[{ required: true, message: '请输入主机地址' }]}
            >
              <Input placeholder="例如：127.0.0.1 或 db.example.com" />
            </Form.Item>

            <Form.Item
              name="port"
              label="端口"
              rules={[{ required: true, message: '请输入端口' }]}
            >
              <InputNumber
                min={1}
                max={65535}
                style={{ width: '100%' }}
                placeholder="端口号"
              />
            </Form.Item>

            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input placeholder="连接账号" autoComplete="off" />
            </Form.Item>
          </>
        )}

        <Form.Item
          name="password"
          label="密码"
          rules={
            mode === 'create'
              ? [{ required: true, message: '请输入密码' }]
              : []
          }
        >
          <Input.Password
            placeholder={mode === 'edit' ? '留空保留原密码' : '连接密码'}
            autoComplete="new-password"
          />
        </Form.Item>

        <Form.Item
          name="database"
          label={meta.hidesHost ? '数据库文件路径' : '数据库'}
          rules={[{ required: true, message: '请输入数据库' }]}
        >
          <Input
            placeholder={
              meta.hidesHost
                ? '例如：/data/app.db'
                : '数据库名称，例如：ontomind'
            }
          />
        </Form.Item>

        {meta.showsSchema && (
          <Form.Item name="default_schema" label="默认 Schema">
            <Input placeholder="例如：public" />
          </Form.Item>
        )}

        <Form.Item name="charset" label="字符集">
          <Input placeholder="utf8mb4" />
        </Form.Item>

        <Form.Item name="description" label="描述">
          <TextArea rows={2} placeholder="可填写该数据源的业务说明" maxLength={500} />
        </Form.Item>

        <Form.Item
          name="read_only_flag"
          label="只读模式"
          valuePropName="checked"
          tooltip="开启后仅允许 SELECT / EXPLAIN 查询"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Drawer>
  );
}
