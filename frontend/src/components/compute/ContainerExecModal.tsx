/**
 * 快速命令弹窗 — 在容器内执行命令。
 *
 * 相比原实现的改进：
 * - 支持「立即执行」(sync) 与「后台执行」(async) 两种模式，模板自带推荐模式
 * - 模板参数渲染成独立输入框（带默认值/示例），不用手改命令串里的 {port}
 * - async 模式自动轮询日志直到结束，并正确展示退出码
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  App,
  Button,
  Divider,
  Input,
  InputNumber,
  Modal,
  Segmented,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import useComputeStore, { extractErrMsg } from '../../stores/computeStore';
import type { ContainerInfo } from '../../types/compute';

const { Text } = Typography;

const LOG_BOX: React.CSSProperties = {
  background: '#1a1918',
  color: '#e0e0e0',
  padding: 12,
  borderRadius: 8,
  minHeight: 160,
  maxHeight: 320,
  overflow: 'auto',
  fontSize: 12,
  fontFamily: "'JetBrains Mono', monospace",
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
  margin: 0,
};

interface Props {
  open: boolean;
  container: ContainerInfo | null;
  onClose: () => void;
}

export default function ContainerExecModal({ open, container, onClose }: Props) {
  const { notification } = App.useApp();
  const { templates, fetchTemplates, execCommand, getCommandLogs } = useComputeStore();

  const [templateId, setTemplateId] = useState<string | undefined>();
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [command, setCommand] = useState('');
  const [mode, setMode] = useState<'sync' | 'async'>('sync');
  const [workdir, setWorkdir] = useState('');
  const [running, setRunning] = useState(false);

  const [logs, setLogs] = useState('');
  const [execId, setExecId] = useState('');
  const [isLive, setIsLive] = useState(false);
  const [exitCode, setExitCode] = useState<number | null>(null);
  const pollRef = useRef<number | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (open) {
      void fetchTemplates();
      setTemplateId(undefined);
      setParams({});
      setCommand('');
      setMode('sync');
      setWorkdir('');
      setLogs('');
      setExecId('');
      setExitCode(null);
      setIsLive(false);
    } else {
      stopPoll();
    }
  }, [open, fetchTemplates, stopPoll]);

  useEffect(() => stopPoll, [stopPoll]);

  const tpl = templates.find((t) => t.id === templateId);

  const applyTemplate = (id: string) => {
    setTemplateId(id);
    const t = templates.find((x) => x.id === id);
    if (!t) return;
    setCommand(t.command);
    setMode((t.mode as 'sync' | 'async') || 'async');
    const defaults: Record<string, unknown> = {};
    Object.entries(t.params || {}).forEach(([k, spec]) => {
      defaults[k] = spec.default;
    });
    setParams(defaults);
  };

  const poll = useCallback(
    async (eid: string) => {
      if (!container) return;
      try {
        const d = await getCommandLogs(container.id, eid);
        setLogs(d.logs);
        setIsLive(d.running);
        setExitCode(d.exit_code);
        if (!d.running) stopPoll();
      } catch (err) {
        setLogs((p) => `${p}\n[获取日志失败] ${extractErrMsg(err)}`);
        stopPoll();
        setIsLive(false);
      }
    },
    [container, getCommandLogs, stopPoll],
  );

  const submit = async () => {
    if (!container) return;
    if (!templateId && !command.trim()) {
      notification.warning({
        title: '请输入命令',
        description: '可以先在上方选一个命令模板，或直接输入如 ps aux',
      });
      return;
    }
    setRunning(true);
    setLogs('');
    setExitCode(null);
    stopPoll();
    try {
      const res = await execCommand(container.id, {
        command: templateId ? '' : command,
        template_id: templateId,
        params: Object.keys(params).length > 0 ? params : undefined,
        mode,
        workdir: workdir.trim() || undefined,
        timeout: 60,
      });
      setExecId(res.exec_id);

      if (res.mode === 'sync') {
        setLogs(res.logs || '(无输出)');
        setExitCode(res.exit_code);
        setIsLive(false);
      } else {
        setIsLive(true);
        setLogs('命令已在后台启动，正在获取输出…');
        // 立即拉一次，然后每 1.5s 轮询
        void poll(res.exec_id);
        pollRef.current = window.setInterval(() => void poll(res.exec_id), 1500);
      }
    } catch (err) {
      notification.error({
        title: '命令执行失败',
        description: extractErrMsg(err),
        duration: 8,
      });
    } finally {
      setRunning(false);
    }
  };

  const statusTag = () => {
    if (isLive) return <Tag color="processing">运行中</Tag>;
    if (exitCode === null) return null;
    return exitCode === 0 ? (
      <Tag color="success">成功 (exit 0)</Tag>
    ) : (
      <Tag color="error">失败 (exit {exitCode})</Tag>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <ThunderboltOutlined />
          在容器内执行命令
          {container && (
            <Text code style={{ fontSize: 12 }}>
              {container.name}
            </Text>
          )}
          {statusTag()}
        </Space>
      }
      open={open}
      onCancel={() => {
        stopPoll();
        onClose();
      }}
      width={720}
      destroyOnHidden
      footer={
        <Space>
          {logs && (
            <Button onClick={() => execId && void poll(execId)} disabled={!execId}>
              刷新日志
            </Button>
          )}
          <Button
            type="primary"
            loading={running}
            onClick={submit}
            icon={<ThunderboltOutlined />}
          >
            {mode === 'sync' ? '立即执行' : '后台执行'}
          </Button>
          <Button
            onClick={() => {
              stopPoll();
              onClose();
            }}
          >
            关闭
          </Button>
        </Space>
      }
    >
      {container && container.status !== 'running' && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          title="容器未运行"
          description="需要先启动容器才能在里面执行命令。"
        />
      )}

      {/* 模板选择 */}
      <div style={{ marginBottom: 10 }}>
        <Text strong style={{ fontSize: 13 }}>
          命令模板
        </Text>
        <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8 }}>
          选一个即可，参数会自动生成输入框
        </Text>
        <Select
          allowClear
          size="small"
          style={{ width: '100%', marginTop: 4 }}
          placeholder="例如「查看监听端口」「opencode serve」"
          value={templateId}
          onChange={(v) => {
            if (v) applyTemplate(v);
            else {
              setTemplateId(undefined);
              setParams({});
            }
          }}
          options={templates.map((t) => ({ value: t.id, label: t.name, title: t.description }))}
        />
        {tpl && (
          <Text type="secondary" style={{ fontSize: 11.5, display: 'block', marginTop: 4 }}>
            {tpl.description}
          </Text>
        )}
      </div>

      {/* 模板参数 */}
      {tpl && Object.keys(tpl.params || {}).length > 0 && (
        <>
          <Divider style={{ margin: '10px 0' }} />
          <Text strong style={{ fontSize: 13 }}>
            参数
          </Text>
          <div style={{ marginTop: 6 }}>
            {Object.entries(tpl.params).map(([key, spec]) => (
              <div
                key={key}
                style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}
              >
                <Text style={{ fontSize: 12, width: 110, flexShrink: 0 }}>{spec.label}</Text>
                {spec.type === 'number' ? (
                  <InputNumber
                    size="small"
                    value={params[key] as number}
                    placeholder={spec.example}
                    onChange={(v) => setParams((p) => ({ ...p, [key]: v }))}
                    style={{ width: 160 }}
                  />
                ) : (
                  <Input
                    size="small"
                    value={params[key] as string}
                    placeholder={spec.example}
                    onChange={(e) => setParams((p) => ({ ...p, [key]: e.target.value }))}
                    style={{ flex: 1, fontFamily: 'monospace' }}
                  />
                )}
                {spec.example && (
                  <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace' }}>
                    例：{spec.example}
                  </Text>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      <Divider style={{ margin: '10px 0' }} />

      {/* 命令 */}
      <div style={{ marginBottom: 10 }}>
        <Text strong style={{ fontSize: 13 }}>
          命令{!templateId && <Text type="danger"> *</Text>}
        </Text>
        <Text type="secondary" style={{ fontSize: 11.5, marginLeft: 8, fontFamily: 'monospace' }}>
          例：ps aux
        </Text>
        <Input.TextArea
          rows={3}
          style={{ marginTop: 4, fontFamily: 'monospace', fontSize: 12 }}
          placeholder="ps aux"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          disabled={!!templateId}
        />
        {templateId && (
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 3 }}>
            使用模板时命令由上方参数生成，如需自定义请清空模板
          </Text>
        )}
      </div>

      {/* 模式 + 工作目录 */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
            执行模式
          </Text>
          <Segmented
            size="small"
            value={mode}
            onChange={(v) => setMode(v as 'sync' | 'async')}
            options={[
              { label: '立即执行', value: 'sync' },
              { label: '后台执行', value: 'async' },
            ]}
          />
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 3 }}>
            {mode === 'sync'
              ? '等命令跑完直接返回结果（适合 ps / df / cat）'
              : '立即返回并轮询日志（适合 serve 等常驻进程）'}
          </Text>
        </div>
        <div style={{ flex: 1 }}>
          <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
            工作目录
          </Text>
          <Input
            size="small"
            placeholder="/workspace（留空用容器默认）"
            value={workdir}
            onChange={(e) => setWorkdir(e.target.value)}
            style={{ fontFamily: 'monospace' }}
          />
        </div>
      </div>

      {/* 输出 */}
      {(logs || isLive) && (
        <>
          <Text strong style={{ fontSize: 13 }}>
            输出
          </Text>
          <pre style={{ ...LOG_BOX, marginTop: 4 }}>{logs || '等待输出…'}</pre>
        </>
      )}
    </Modal>
  );
}
