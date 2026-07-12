import type { ReactNode } from 'react';
import { Alert, Card, Flex, Space, Tag, Timeline, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  RobotOutlined,
  SyncOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import type { TimelineEntry } from './types';

const { Title, Text, Paragraph } = Typography;

export function PlatformPageHeader({
  title,
  subtitle,
  extra,
}: {
  title: string;
  subtitle: string;
  extra?: ReactNode;
}) {
  return (
    <Flex justify="space-between" align="flex-start" gap={16} wrap style={{ marginBottom: 16 }}>
      <div>
        <Title level={3} style={{ margin: 0 }}>{title}</Title>
        <Text type="secondary">{subtitle}</Text>
      </div>
      {extra}
    </Flex>
  );
}

const statusColor: Record<TimelineEntry['status'], string> = {
  pending: 'gray',
  running: 'blue',
  success: 'green',
  error: 'red',
  warning: 'orange',
};

const categoryIcon: Record<TimelineEntry['category'], ReactNode> = {
  thinking: <SyncOutlined />,
  step: <NodeIndexOutlined />,
  tool: <ToolOutlined />,
  subagent: <RobotOutlined />,
  eval: <ExperimentOutlined />,
  run: <CheckCircleOutlined />,
};

export function RunTimelinePanel({
  entries,
  connectionState,
  error,
}: {
  entries: TimelineEntry[];
  connectionState?: string;
  error?: string | null;
}) {
  return (
    <Card
      title="执行轨迹"
      extra={connectionState ? <Tag color={connectionState === 'open' ? 'green' : 'blue'}>{connectionState}</Tag> : null}
      styles={{ body: { paddingBottom: 4 } }}
    >
      <Alert
        type="info"
        showIcon
        message="仅展示结构化思考摘要，不展示模型私有思维链"
        style={{ marginBottom: 16 }}
      />
      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} /> : null}
      {entries.length === 0 ? (
        <Text type="secondary">Run 事件将在这里实时出现</Text>
      ) : (
        <Timeline
          items={entries.map((entry) => ({
            color: statusColor[entry.status],
            dot: entry.status === 'error' ? <CloseCircleOutlined /> : categoryIcon[entry.category],
            children: (
              <div data-testid={`timeline-${entry.category}`}>
                <Space size={6}>
                  <Text strong>{entry.title}</Text>
                  <Tag bordered={false}>{entry.eventType}</Tag>
                </Space>
                {entry.summary ? (
                  <Paragraph type="secondary" style={{ margin: '4px 0 0', whiteSpace: 'pre-wrap' }}>
                    {entry.summary}
                  </Paragraph>
                ) : null}
              </div>
            ),
          }))}
        />
      )}
    </Card>
  );
}
