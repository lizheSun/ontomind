import { useMemo, useState } from 'react';
import { Card, Input, Space, Tag, Button, message } from 'antd';
import { SendOutlined, BarChartOutlined } from '@ant-design/icons';
import { PageHeader, AgentEmbedRunner } from '../../components/common';

/**
 * AIBI page (agent-embedded).
 *
 * Embeds an agent runner into the AIBI application surface. Uses the
 * postMessage protocol via <AgentEmbedRunner /> to feed prompts as context,
 * receive analysis results, and surface errors.
 */
export default function AIBIPage() {
  const [msgApi, contextHolder] = message.useMessage();
  const [prompt, setPrompt] = useState('');
  const [submittedPrompt, setSubmittedPrompt] = useState('');
  const [dataset, setDataset] = useState<string>('kb.default');
  const [result, setResult] = useState<unknown>(null);
  const [ready, setReady] = useState(false);

  const context = useMemo(
    () => ({
      surface: 'aibi',
      prompt: submittedPrompt,
      dataset,
      locale: 'zh-CN',
    }),
    [submittedPrompt, dataset],
  );

  const handleSubmit = () => {
    const trimmed = prompt.trim();
    if (!trimmed) {
      msgApi.warning('请输入分析需求');
      return;
    }
    setSubmittedPrompt(trimmed);
  };

  return (
    <div>
      {contextHolder}
      <PageHeader
        title="AIbi 智能分析"
        subtitle="Agent 驱动 · 自然语言查询与可视化"
      />

      <Card
        style={{
          borderRadius: 14,
          border: '1px solid rgba(255,255,255,0.06)',
          marginBottom: 16,
          background:
            'linear-gradient(135deg, rgba(59,130,246,0.05), rgba(139,92,246,0.02))',
        }}
        styles={{ body: { padding: 16 } }}
      >
        <Space.Compact style={{ width: '100%' }}>
          <Input
            size="large"
            placeholder="例如: 分析最近 30 天风控拒绝率趋势"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onPressEnter={handleSubmit}
            prefix={<BarChartOutlined style={{ color: '#60a5fa' }} />}
          />
          <Button
            size="large"
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSubmit}
          >
            分析
          </Button>
        </Space.Compact>

        <Space size={8} style={{ marginTop: 12 }}>
          <span style={{ color: '#7a8ba5', fontSize: 12 }}>数据集:</span>
          {['kb.default', 'kb.risk', 'kb.marketing'].map((ds) => (
            <Tag.CheckableTag
              key={ds}
              checked={dataset === ds}
              onChange={() => setDataset(ds)}
            >
              {ds}
            </Tag.CheckableTag>
          ))}
          <Tag bordered={false} color={ready ? 'green' : 'default'}>
            Agent {ready ? '就绪' : '连接中'}
          </Tag>
        </Space>
      </Card>

      <AgentEmbedRunner
        agentId="aibi"
        title="AIbi Agent"
        height={520}
        context={context}
        onReady={() => setReady(true)}
        onResult={(data) => setResult(data)}
        onError={(err) => msgApi.error(err)}
      />

      <Card
        title={<span style={{ fontWeight: 600 }}>最近分析结果</span>}
        style={{
          borderRadius: 14,
          border: '1px solid rgba(255,255,255,0.06)',
          marginTop: 16,
        }}
        styles={{ body: { padding: 16 } }}
      >
        {result ? (
          <pre
            style={{
              margin: 0,
              padding: 12,
              fontSize: 12,
              color: '#c7d2df',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: 10,
              maxHeight: 240,
              overflow: 'auto',
            }}
            data-testid="aibi-result"
          >
            {JSON.stringify(result, null, 2)}
          </pre>
        ) : (
          <span style={{ color: '#506380', fontSize: 13 }}>
            结果将在 Agent 返回后展示
          </span>
        )}
      </Card>
    </div>
  );
}
