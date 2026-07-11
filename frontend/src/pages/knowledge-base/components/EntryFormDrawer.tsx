import { useEffect } from 'react';
import { Drawer, Form, Input, Select, Space, Button } from 'antd';

export type SchemaKey = 'dataAsset' | 'codeRepo' | 'experience';

export interface EntryField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'input.password' | 'tags';
  required?: boolean;
  placeholder?: string;
  rows?: number;
}

export const ENTRY_SCHEMAS: Record<SchemaKey, EntryField[]> = {
  dataAsset: [
    { name: 'titleZh', label: '中文名', type: 'text', required: true },
    { name: 'titleEn', label: '英文名', type: 'text' },
    { name: 'domain', label: '业务域', type: 'text' },
    { name: 'descriptionMd', label: '描述', type: 'textarea', rows: 6 },
    { name: 'tags', label: '标签', type: 'tags' },
  ],
  codeRepo: [
    { name: 'titleZh', label: '仓库名', type: 'text', required: true },
    { name: 'repoUrl', label: '仓库 URL', type: 'text', required: true },
    { name: 'branch', label: '分支', type: 'text', placeholder: 'main' },
    { name: 'language', label: '主语言', type: 'text' },
    { name: 'descriptionMd', label: '描述', type: 'textarea', rows: 4 },
    { name: 'tags', label: '标签', type: 'tags' },
  ],
  experience: [
    { name: 'titleZh', label: '标题', type: 'text', required: true },
    { name: 'scenario', label: '场景', type: 'text' },
    { name: 'contentMd', label: '正文', type: 'textarea', rows: 10, required: true },
    { name: 'outcome', label: '结果 / 指标', type: 'text' },
    { name: 'tags', label: '标签', type: 'tags' },
  ],
};

export type EntryFormValues = Record<string, string | string[] | undefined>;

interface EntryFormDrawerProps {
  open: boolean;
  schemaKey: SchemaKey;
  title: string;
  initialValues?: EntryFormValues;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: EntryFormValues) => void | Promise<void>;
}

export default function EntryFormDrawer({
  open,
  schemaKey,
  title,
  initialValues,
  submitting,
  onClose,
  onSubmit,
}: EntryFormDrawerProps) {
  const [form] = Form.useForm<EntryFormValues>();
  const fields = ENTRY_SCHEMAS[schemaKey];

  useEffect(() => {
    if (open) {
      form.resetFields();
      if (initialValues) form.setFieldsValue(initialValues);
    }
  }, [open, initialValues, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      await onSubmit(values);
    } catch (err) {
      // validation errors handled by Form
      if (err && typeof err === 'object' && 'errorFields' in err) return;
    }
  };

  return (
    <Drawer
      title={title}
      open={open}
      onClose={onClose}
      width={520}
      destroyOnHidden
      extra={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={submitting} onClick={handleOk}>
            保存
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical" autoComplete="off">
        {fields.map((f) => {
          const rules = f.required
            ? [{ required: true, message: `请填写${f.label}` }]
            : undefined;
          if (f.type === 'text') {
            return (
              <Form.Item key={f.name} name={f.name} label={f.label} rules={rules}>
                <Input placeholder={f.placeholder} />
              </Form.Item>
            );
          }
          if (f.type === 'input.password') {
            return (
              <Form.Item key={f.name} name={f.name} label={f.label} rules={rules}>
                <Input.Password placeholder={f.placeholder} />
              </Form.Item>
            );
          }
          if (f.type === 'textarea') {
            return (
              <Form.Item key={f.name} name={f.name} label={f.label} rules={rules}>
                <Input.TextArea rows={f.rows ?? 4} placeholder={f.placeholder} />
              </Form.Item>
            );
          }
          // tags
          return (
            <Form.Item key={f.name} name={f.name} label={f.label} rules={rules}>
              <Select
                mode="tags"
                tokenSeparators={[',', ' ']}
                placeholder="输入标签后回车"
                style={{ width: '100%' }}
              />
            </Form.Item>
          );
        })}
      </Form>
    </Drawer>
  );
}
