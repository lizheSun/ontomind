import { useEffect, useRef, useState } from 'react';
import { Button, Dropdown, Input, Space, Typography, message } from 'antd';
import {
  CopyOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  SendOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { GlassPanel } from '../../../components/common';
import type { DpChatMessage, DpChatSession, DpExecuteResponse } from '../../../types/dataPlatform';
import { dataPlatformService } from '../../../services/dataPlatform.service';

const { Text } = Typography;

interface Props {
  sourceId: number;
  onApplyToEditor: (sql: string) => void;
}

export default function ChatTab({ sourceId, onApplyToEditor }: Props) {
  const [sessions, setSessions] = useState<DpChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<DpChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [applyResult, setApplyResult] = useState<DpExecuteResponse | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const list = await dataPlatformService.listSessions();
        const forSource = list.filter((s) => s.sourceId === sourceId);
        setSessions(forSource);
        if (forSource.length > 0) {
          setCurrentSessionId(forSource[0].id);
        }
      } catch (err: unknown) {
        const anyErr = err as { message?: string };
        message.error(anyErr.message ?? '加载会话失败');
      }
    })();
  }, [sourceId]);

  useEffect(() => {
    if (currentSessionId === null) {
      setMessages([]);
      return;
    }
    void (async () => {
      try {
        const list = await dataPlatformService.listMessages(currentSessionId);
        setMessages(list);
      } catch {
        setMessages([]);
      }
    })();
  }, [currentSessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length]);

  const ensureSession = async (): Promise<number> => {
    if (currentSessionId !== null) return currentSessionId;
    const s = await dataPlatformService.createSession({
      name: '未命名会话',
      sourceId,
      modelConfigId: null,
    });
    setSessions((prev) => [s, ...prev]);
    setCurrentSessionId(s.id);
    return s.id;
  };

  const handleSend = async (): Promise<void> => {
    const content = input.trim();
    if (!content || sending) return;
    setSending(true);
    try {
      const sid = await ensureSession();
      // Optimistic user echo
      const userMsg: DpChatMessage = {
        id: -Date.now(),
        sessionId: sid,
        role: 'user',
        content,
        generatedSql: null,
        executed: false,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      const reply = await dataPlatformService.sendMessage(sid, content);
      setMessages((prev) => [...prev, reply]);
    } catch (err: unknown) {
      const anyErr = err as { response?: { data?: { message?: string } }; message?: string };
      message.error(anyErr.response?.data?.message ?? anyErr.message ?? '发送失败');
    } finally {
      setSending(false);
    }
  };

  const handleCreateNewSession = async (): Promise<void> => {
    try {
      const s = await dataPlatformService.createSession({
        name: '未命名会话',
        sourceId,
        modelConfigId: null,
      });
      setSessions((prev) => [s, ...prev]);
      setCurrentSessionId(s.id);
      setMessages([]);
    } catch (err: unknown) {
      const anyErr = err as { message?: string };
      message.error(anyErr.message ?? '创建会话失败');
    }
  };

  const handleCopySql = async (sql: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(sql);
      message.success('已复制');
    } catch {
      message.error('复制失败');
    }
  };

  const handleApplyToEditor = (sql: string): void => {
    onApplyToEditor(sql);
    message.success('已应用到编辑器');
  };

  const handleRun = async (msg: DpChatMessage): Promise<void> => {
    if (currentSessionId === null || !msg.generatedSql) return;
    try {
      const res = await dataPlatformService.applyMessage(currentSessionId, msg.id);
      setApplyResult(res);
      message.success(`执行成功 · ${res.rowCount} 行`);
    } catch (err: unknown) {
      const anyErr = err as { response?: { data?: { message?: string } }; message?: string };
      message.error(anyErr.response?.data?.message ?? anyErr.message ?? '执行失败');
    }
  };

  const sessionMenu = {
    items: [
      ...sessions.map((s) => ({
        key: String(s.id),
        label: s.name || `会话 #${s.id}`,
        icon: <EditOutlined />,
      })),
      { type: 'divider' as const },
      { key: 'new', label: '新建会话', icon: <PlusOutlined /> },
    ],
    onClick: ({ key }: { key: string }) => {
      if (key === 'new') {
        void handleCreateNewSession();
      } else {
        setCurrentSessionId(Number(key));
      }
    },
  };

  const currentSessionLabel =
    sessions.find((s) => s.id === currentSessionId)?.name ??
    (currentSessionId === null ? '未开始' : `会话 #${currentSessionId}`);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: 'var(--text-secondary, #8895b4)', fontSize: 13 }}>
          与 AI 对话生成 SQL
        </Text>
        <Dropdown menu={sessionMenu} trigger={['click']}>
          <Button size="small" icon={<DownOutlined />} iconPosition="end">
            {currentSessionLabel}
          </Button>
        </Dropdown>
      </div>

      <GlassPanel padded={false} style={{ overflow: 'hidden' }}>
        <div
          ref={scrollRef}
          style={{
            padding: 16,
            height: 420,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                margin: 'auto',
                color: 'var(--text-tertiary, #506080)',
                fontSize: 13,
              }}
            >
              发送第一条消息开始对话
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                {m.role === 'user' ? (
                  <div
                    style={{
                      maxWidth: '70%',
                      padding: '8px 14px',
                      borderRadius: 16,
                      background: 'rgba(59,130,246,0.14)',
                      color: 'var(--text-primary, #e8eef5)',
                      fontSize: 13.5,
                      lineHeight: 1.6,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {m.content}
                  </div>
                ) : (
                  <div style={{ maxWidth: '85%', display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div
                      style={{
                        padding: '10px 14px',
                        borderRadius: 12,
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid var(--dp-panel-border, rgba(59,130,246,0.14))',
                        color: 'var(--text-primary, #e8eef5)',
                        fontSize: 13.5,
                        lineHeight: 1.6,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {m.content}
                    </div>
                    {m.generatedSql && (
                      <GlassPanel padded={false} style={{ overflow: 'hidden' }}>
                        <pre
                          style={{
                            margin: 0,
                            padding: 12,
                            fontFamily: 'var(--font-mono, ui-monospace, monospace)',
                            fontSize: 12.5,
                            color: 'var(--text-primary, #e8eef5)',
                            background: 'var(--code-bg, #0a0f1f)',
                            overflow: 'auto',
                            whiteSpace: 'pre-wrap',
                          }}
                        >
                          {m.generatedSql}
                        </pre>
                        <div
                          style={{
                            padding: '8px 12px',
                            borderTop: '1px solid var(--dp-panel-border, rgba(59,130,246,0.14))',
                          }}
                        >
                          <Space size={8}>
                            <Button
                              size="small"
                              icon={<CopyOutlined />}
                              onClick={() => void handleCopySql(m.generatedSql!)}
                            >
                              复制
                            </Button>
                            <Button
                              size="small"
                              icon={<EditOutlined />}
                              onClick={() => handleApplyToEditor(m.generatedSql!)}
                            >
                              应用到编辑器
                            </Button>
                            <Button
                              size="small"
                              type="primary"
                              icon={<PlayCircleOutlined />}
                              onClick={() => void handleRun(m)}
                            >
                              直接运行
                            </Button>
                          </Space>
                        </div>
                      </GlassPanel>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </GlassPanel>

      {applyResult && (
        <Text style={{ fontSize: 12, color: 'var(--text-secondary, #8895b4)' }}>
          最近运行结果：{applyResult.rowCount} 行 · {applyResult.elapsedMs} ms
        </Text>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="用自然语言描述你的需求，例如：查询销售额前 10 的商品"
          autoSize={{ minRows: 2, maxRows: 5 }}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={() => void handleSend()}
          loading={sending}
          style={{ height: 'auto' }}
        >
          发送
        </Button>
      </div>
    </div>
  );
}
