import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Divider,
  Empty,
  Flex,
  List,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import AgentChatPanel from '../../components/common/AgentChatPanel';
import { agentPlatformService } from '../../services/agentPlatform.service';
import { useAgentStream } from '../../hooks/useAgentStream';
import { useAgentPlatformStore } from '../../stores/agentPlatformStore';
import { PlatformPageHeader, RunTimelinePanel } from './components';

const { Text } = Typography;

export default function ChatWorkspacePage() {
  const navigate = useNavigate();
  const store = useAgentPlatformStore();
  const stream = useAgentStream(store.activeRunId, store.ingestEvent);
  const selectedAgent = store.agents.find((agent) => agent.id === store.selectedAgentId);

  useEffect(() => {
    void (async () => {
      await useAgentPlatformStore.getState().loadAgents();
      const agentId = useAgentPlatformStore.getState().selectedAgentId;
      if (agentId != null) {
        await useAgentPlatformStore.getState().loadSessions(agentId);
      }
    })();
  }, []);

  const newSession = async () => {
    if (!store.selectedAgentId) return;
    try {
      await store.createSession(store.selectedAgentId, '新会话');
      message.success('已创建会话');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '创建会话失败');
    }
  };

  const decideTool = async (partId: string, decision: 'approve' | 'reject') => {
    try {
      const approvalId = Number(partId);
      if (!Number.isInteger(approvalId)) throw new Error('审批事件缺少有效 approval_id');
      const approval = await agentPlatformService.getApproval(approvalId);
      await agentPlatformService.decideApproval(
        approvalId,
        decision,
        approval.lock_version,
      );
      message.success(decision === 'approve' ? '已批准工具调用' : '已拒绝工具调用');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '工具审批失败');
    }
  };

  return (
    <div style={{ minWidth: 1040 }}>
      <PlatformPageHeader
        title="对话工作台"
        subtitle="与已发布 Agent 对话；真实调用本机 OpenCode。编辑 / 发布请去资源管理。"
        extra={
          <Space>
            <Button icon={<SettingOutlined />} onClick={() => navigate('/agent-platform/resources')}>
              资源管理
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => void store.loadAgents()}>
              刷新
            </Button>
          </Space>
        }
      />
      {store.error ? <Alert type="error" showIcon message={store.error} style={{ marginBottom: 12 }} /> : null}
      <div style={{ display: 'grid', gridTemplateColumns: '260px minmax(460px, 1fr) 340px', gap: 14 }}>
        <Card title="Agent 与会话" styles={{ body: { padding: 12 } }}>
          <Button
            type="primary"
            block
            icon={<PlusOutlined />}
            disabled={!store.selectedAgentId}
            onClick={() => void newSession()}
          >
            新建会话
          </Button>
          <Divider style={{ margin: '12px 0' }} />
          {store.loading && store.agents.length === 0 ? (
            <Flex justify="center"><Spin /></Flex>
          ) : (
            <List
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无 Agent，请先到资源管理发布" /> }}
              dataSource={store.agents}
              renderItem={(agent) => (
                <List.Item
                  onClick={() => store.selectAgent(agent.id)}
                  style={{
                    cursor: 'pointer',
                    padding: 8,
                    borderBlockEnd: 0,
                    borderRadius: 8,
                    background: agent.id === store.selectedAgentId ? 'rgba(59,130,246,.14)' : undefined,
                  }}
                >
                  <List.Item.Meta
                    avatar={(
                      <Badge status={agent.is_published ? 'success' : 'default'} dot>
                        <Avatar icon={<RobotOutlined />} />
                      </Badge>
                    )}
                    title={<Text ellipsis style={{ maxWidth: 160 }}>{agent.name}</Text>}
                    description={(
                      <Tag bordered={false} color={agent.is_published ? 'success' : 'default'}>
                        {agent.is_published ? `已发布 v${agent.version}` : '未发布'}
                      </Tag>
                    )}
                  />
                </List.Item>
              )}
            />
          )}
          <Divider style={{ margin: '12px 0' }} />
          <Text type="secondary" style={{ fontSize: 12 }}>最近会话</Text>
          <List
            size="small"
            dataSource={store.sessions}
            locale={{ emptyText: '暂无会话' }}
            renderItem={(session) => (
              <List.Item
                onClick={() => void store.selectSession(session.id)}
                style={{
                  cursor: 'pointer',
                  paddingInline: 6,
                  borderRadius: 6,
                  background: session.id === store.selectedSessionId ? 'rgba(96,165,250,.1)' : undefined,
                }}
              >
                <Text ellipsis>{session.title || `会话 #${session.id}`}</Text>
              </List.Item>
            )}
          />
        </Card>

        <AgentChatPanel
          title={selectedAgent?.name ?? 'Agent 会话'}
          statusText={
            selectedAgent
              ? selectedAgent.is_published
                ? `已发布 v${selectedAgent.version} · OpenCode`
                : '未发布 · 可对话，建议先在资源管理发布'
              : '请选择 Agent'
          }
          height={590}
          messages={store.timeline.messages}
          streaming={stream.state === 'open' && store.timeline.status === 'running'}
          disabled={!selectedAgent}
          onSend={async (content) => { await store.sendMessage(content); }}
          onApproveTool={(_, partId) => decideTool(partId, 'approve')}
          onRejectTool={(_, partId) => decideTool(partId, 'reject')}
          onClear={store.clearTimeline}
          emptyText="选择 Agent 后发送消息；后端将调用本机 opencode run"
          extra={
            store.activeRunId ? (
              <Space>
                <Tag color="blue">Run {store.activeRunId}</Tag>
                <Button size="small" danger onClick={() => void agentPlatformService.controlRun(store.activeRunId!, 'cancel')}>
                  取消
                </Button>
              </Space>
            ) : null
          }
        />

        <RunTimelinePanel
          entries={store.timeline.entries}
          connectionState={stream.state}
          error={stream.error}
        />
      </div>
    </div>
  );
}
