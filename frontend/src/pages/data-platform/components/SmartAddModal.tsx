import { useState } from 'react';
import { Modal, Input, Alert, Space, Typography, Spin, message } from 'antd';
import { ThunderboltOutlined, WarningOutlined } from '@ant-design/icons';
import type { AxiosError } from 'axios';
import {
  dataPlatformService,
  type ParseConfigResult,
} from '../../../services/dataPlatform.service';

const { Text } = Typography;
const { TextArea } = Input;

const PLACEHOLDER_EXAMPLES = `示例 1 (环境变量):
MYSQL_HOST=10.1.1.1
MYSQL_PORT=3306
MYSQL_USER=readonly
MYSQL_DB=orders

示例 2 (连接串):
postgresql://analyst@pg.internal:5432/analytics

示例 3 (自然语言):
生产库主库 MySQL，地址 10.1.1.1:3306，库名 core，用户 readonly，只读

粘贴任意格式，AI 会解析出字段（密码不会被提取，需你手动填写）`;

export interface SmartAddModalProps {
  open: boolean;
  onCancel: () => void;
  onParsed: (result: ParseConfigResult) => void;
}

export default function SmartAddModal({
  open,
  onCancel,
  onParsed,
}: SmartAddModalProps) {
  const [rawText, setRawText] = useState('');
  const [loading, setLoading] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);

  const handleParse = async () => {
    const trimmed = rawText.trim();
    if (!trimmed) {
      message.warning('请粘贴配置文本或输入自然语言描述');
      return;
    }
    setLoading(true);
    setWarnings([]);
    try {
      const result = await dataPlatformService.parseConfig(trimmed);
      setWarnings(result.warnings);
      message.success(`解析成功（${result.model_used}）`);
      onParsed(result);
      setRawText('');
    } catch (err: unknown) {
      const axErr = err as AxiosError<{ message?: string; detail?: string }>;
      const msg =
        axErr.response?.data?.message ??
        axErr.response?.data?.detail ??
        (err instanceof Error ? err.message : '解析失败');
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (loading) return;
    setRawText('');
    setWarnings([]);
    onCancel();
  };

  return (
    <Modal
      title={
        <Space>
          <ThunderboltOutlined style={{ color: 'var(--accent, #3b82f6)' }} />
          <span>智能添加数据源</span>
        </Space>
      }
      open={open}
      onOk={handleParse}
      onCancel={handleCancel}
      okText={loading ? '解析中...' : '解析'}
      okButtonProps={{ loading, disabled: !rawText.trim() }}
      cancelText="取消"
      width={640}
      destroyOnHidden
      maskClosable={!loading}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Alert
          message="密码字段将自动留空，需在下一步的表单中手动输入"
          description="出于安全考虑，AI 不会从粘贴的文本中提取密码，即使文本包含 MYSQL_PASSWORD/PWD 等字段也不会。"
          type="warning"
          icon={<WarningOutlined />}
          showIcon
        />
        <TextArea
          rows={10}
          placeholder={PLACEHOLDER_EXAMPLES}
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          disabled={loading}
          data-testid="smart-add-textarea"
        />
        {loading && (
          <div style={{ textAlign: 'center', padding: 12 }}>
            <Spin tip="正在调用 LLM 解析..." />
          </div>
        )}
        {warnings.length > 0 && (
          <Alert
            type="info"
            message="解析警告"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            }
            showIcon
          />
        )}
        <Text style={{ fontSize: 12, color: 'var(--text-tertiary, #506080)' }}>
          点击"解析"后，AI 生成的字段将自动填入下一步的新建数据源表单，你可以在提交前修改任何字段。
        </Text>
      </Space>
    </Modal>
  );
}
