/** Agent 工厂共用小组件：校验结果、产物预览、目录树 */
import { Alert, Empty, Space, Tag, Tooltip, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type {
  RenderedArtifact,
  ValidationResult,
} from '../../types/agentFactory';

const { Text } = Typography;

/** 校验结果展示 —— error 阻断保存，warning 仅提示 */
export function ValidationPanel({
  result,
  compact,
}: {
  result?: ValidationResult | null;
  compact?: boolean;
}) {
  if (!result) return null;
  const errors = result.issues.filter((i) => i.level === 'error');
  const warns = result.issues.filter((i) => i.level === 'warning');
  // info = 配置合法，只是把「会发生什么」讲清楚（如「主对话用内置 build」）
  const infos = result.issues.filter((i) => i.level === 'info');

  if (errors.length === 0 && warns.length === 0 && infos.length === 0) {
    return (
      <Space size={6}>
        <CheckCircleOutlined style={{ color: '#52c41a' }} />
        <Text type="success" style={{ fontSize: 12 }}>
          校验通过
        </Text>
      </Space>
    );
  }

  return (
    <div>
      {errors.length > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: warns.length ? 8 : 0 }}
          title={`${errors.length} 处错误必须修正`}
          description={
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {errors.slice(0, compact ? 3 : 20).map((i, idx) => (
                <li key={idx} style={{ fontSize: 12 }}>
                  <Text code style={{ fontSize: 11 }}>
                    {i.field}
                  </Text>{' '}
                  {i.message}
                </li>
              ))}
            </ul>
          }
        />
      )}
      {warns.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: infos.length ? 8 : 0 }}
          title={`${warns.length} 处提示`}
          description={
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {warns.slice(0, compact ? 3 : 20).map((i, idx) => (
                <li key={idx} style={{ fontSize: 12 }}>
                  <Text code style={{ fontSize: 11 }}>
                    {i.field}
                  </Text>{' '}
                  {i.message}
                </li>
              ))}
            </ul>
          }
        />
      )}
      {infos.length > 0 && (
        <Alert
          type="info"
          showIcon
          title={
            errors.length === 0 && warns.length === 0 ? '校验通过' : '补充说明'
          }
          description={
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {infos.map((i, idx) => (
                <li key={idx} style={{ fontSize: 12 }}>
                  {i.message}
                </li>
              ))}
            </ul>
          }
        />
      )}
    </div>
  );
}

/** 状态点（拓扑图与列表共用） */
export function StatusDot({ ok, size = 6 }: { ok: boolean; size?: number }) {
  return (
    <span
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: ok ? '#22c55e' : '#faad14',
        display: 'inline-block',
        flexShrink: 0,
      }}
    />
  );
}

/** 产物内容预览（等宽 + 深色，模拟文件视图） */
export function ArtifactPreview({
  artifact,
  maxHeight = 420,
}: {
  artifact?: RenderedArtifact | null;
  maxHeight?: number;
}) {
  if (!artifact) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Text type="secondary" style={{ fontSize: 12 }}>
            左侧选择一个产物查看内容
          </Text>
        }
      />
    );
  }
  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 6,
        }}
      >
        <Text code style={{ fontSize: 11.5 }}>
          {artifact.path}
        </Text>
        <Space size={6}>
          <Text type="secondary" style={{ fontSize: 10.5 }}>
            {artifact.bytes} B
          </Text>
          <Tooltip title={`sha256: ${artifact.sha256}`}>
            <Text type="secondary" style={{ fontSize: 10.5, fontFamily: 'monospace' }}>
              {artifact.sha256.slice(0, 8)}
            </Text>
          </Tooltip>
          {artifact.is_executable && (
            <Tag style={{ fontSize: 10, margin: 0 }}>可执行</Tag>
          )}
        </Space>
      </div>
      <pre
        style={{
          background: '#1a1918',
          color: '#e0e0e0',
          padding: 12,
          borderRadius: 8,
          maxHeight,
          overflow: 'auto',
          fontSize: 11.5,
          fontFamily: "'JetBrains Mono', monospace",
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          margin: 0,
        }}
      >
        {artifact.content}
      </pre>
    </div>
  );
}

/** 产物目录树（可点击切换） */
export function ArtifactTree({
  artifacts,
  selected,
  onSelect,
  diffMap,
}: {
  artifacts: RenderedArtifact[];
  selected?: string;
  onSelect: (path: string) => void;
  /** path → 'new' | 'changed' | 'same'，发布中心用来标 diff */
  diffMap?: Record<string, 'new' | 'changed' | 'same'>;
}) {
  const DIFF_TAG: Record<string, { label: string; color: string }> = {
    new: { label: '新增', color: 'green' },
    changed: { label: '修改', color: 'orange' },
    same: { label: '未变', color: 'default' },
  };

  return (
    <div style={{ maxHeight: 420, overflow: 'auto' }}>
      {artifacts.map((a) => {
        const d = diffMap?.[a.path];
        const isSel = selected === a.path;
        return (
          <div
            key={a.path}
            onClick={() => onSelect(a.path)}
            style={{
              padding: '5px 8px',
              cursor: 'pointer',
              borderRadius: 6,
              background: isSel ? 'rgba(0,113,227,0.08)' : 'transparent', /* 【UI 重构】Apple Blue 替代原品牌色 */
              borderLeft: isSel ? '2px solid #0071e3' : '2px solid transparent',
              marginBottom: 2,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Text
                style={{
                  fontSize: 11.5,
                  fontFamily: 'monospace',
                  flex: 1,
                  wordBreak: 'break-all',
                }}
              >
                {a.path}
              </Text>
              {d && d !== 'same' && (
                <Tag color={DIFF_TAG[d].color} style={{ fontSize: 10, margin: 0 }}>
                  {DIFF_TAG[d].label}
                </Tag>
              )}
              <Text type="secondary" style={{ fontSize: 10 }}>
                {a.bytes}B
              </Text>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** 回读校验项（发布中心用） */
export function VerifyIcon({ match }: { match: boolean }) {
  return match ? (
    <CheckCircleOutlined style={{ color: '#52c41a' }} />
  ) : (
    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
  );
}

export function WarnIcon() {
  return <WarningOutlined style={{ color: '#faad14' }} />;
}
