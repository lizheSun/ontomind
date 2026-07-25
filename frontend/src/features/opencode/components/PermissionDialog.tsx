/**
 * 全局权限审批弹窗.
 * 监听 opencodeStore.pendingPermissions，任意时刻只显示队首 permission.
 */
import { Alert, Button, Modal, Space, Tag, Typography } from 'antd';
import { CheckOutlined, CloseOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { usePermissions } from '../hooks/usePermissions';

const { Text } = Typography;

export default function PermissionDialog() {
  const { pending, respond } = usePermissions();
  const perm = pending[0]; // 队首
  const open = !!perm;

  const decide = async (response: 'once' | 'always' | 'reject') => {
    if (!perm) return;
    await respond(perm.id, response);
  };

  return (
    <Modal
      open={open}
      title={
        <Space>
          <ThunderboltOutlined style={{ color: '#faad14' }} />
          <span>工具调用需要审批</span>
          {perm?.type && <Tag color="orange">{perm.type}</Tag>}
        </Space>
      }
      onCancel={() => void decide('reject')}
      footer={null}
      mask={{ closable: false }}
      closable={false}
      width={520}
    >
      {perm && (
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <Alert
            type="warning"
            showIcon={false}
            message={<Text strong>{perm.title || '未提供描述'}</Text>}
          />
          {perm.metadata && (
            <pre
              style={{
                background: 'rgba(0,0,0,0.04)',
                padding: 8,
                borderRadius: 6,
                fontSize: 11,
                maxHeight: 220,
                overflow: 'auto',
                margin: 0,
              }}
            >
              {JSON.stringify(perm.metadata, null, 2)}
            </pre>
          )}
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button danger icon={<CloseOutlined />} onClick={() => void decide('reject')}>
              拒绝
            </Button>
            <Button icon={<CheckOutlined />} onClick={() => void decide('once')}>
              允许一次
            </Button>
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={() => void decide('always')}
            >
              始终允许
            </Button>
          </Space>
        </Space>
      )}
    </Modal>
  );
}
