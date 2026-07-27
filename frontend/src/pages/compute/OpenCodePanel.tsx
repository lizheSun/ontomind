/**
 * OpenCode 本地服务面板 — Web 启停 / CLI 一次性执行 / 对话工作台选服务.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert, App, Button, Card, Descriptions, Input, Space, Spin, Tag, Typography,
} from 'antd';
import {
  ApiOutlined, PlayCircleOutlined, ReloadOutlined, RocketOutlined,
  SendOutlined, StopOutlined,
} from '@ant-design/icons';
import * as srv from '../../services/compute.service';
import type { OpenCodeStatus, OpenCodeWebInstance, OpenCodeCliRun } from './types';
import { fmtDateTime, fmtDuration } from './mock';

const { Text } = Typography;
const { TextArea } = Input;

/** 存到 localStorage，供 workspace 读取当前选中的 opencode URL */
const OPENCODE_URL_KEY = 'ontomind_opencode_url';

export default function OpenCodePanel() {
  const { message } = App.useApp();

  // ---- 状态 ----
  const [status, setStatus] = useState<OpenCodeStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [startingWeb, setStartingWeb] = useState(false);
  const [startPort, setStartPort] = useState(4096);
  const [startCors, setStartCors] = useState('http://localhost:5173');
  const [selectedUrl, setSelectedUrl] = useState<string>(() => localStorage.getItem(OPENCODE_URL_KEY) || '');

  // CLI
  const [cliPrompt, setCliPrompt] = useState('');
  const [cliRunning, setCliRunning] = useState(false);
  const [cliOutput, setCliOutput] = useState('');
  const [cliRuns, setCliRuns] = useState<OpenCodeCliRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  // 轮询 CLI 运行状态
  const runPollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  // ---- 加载 ----
  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const s = await srv.getOpenCodeStatus();
      setStatus(s);
      // 如果还没选 URL 但有一个实例在跑，自动选中
      if (!selectedUrl && s.running_instances.length > 0) {
        setSelectedUrl(s.running_instances[0].url);
        localStorage.setItem(OPENCODE_URL_KEY, s.running_instances[0].url);
      }
    } catch (e: any) {
      message.error('获取 OpenCode 状态失败');
    } finally {
      setLoading(false);
    }
  }, [selectedUrl, message]);

  const loadCliRuns = useCallback(async () => {
    try {
      const runs = await srv.getOpenCodeRuns(20);
      setCliRuns(runs);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadStatus();
    loadCliRuns();
  }, [loadStatus, loadCliRuns]);

  // 轮询正在运行的 CLI 任务
  useEffect(() => {
    if (runPollRef.current) { clearInterval(runPollRef.current); runPollRef.current = undefined; }
    const activeRun = cliRuns.find(r => r.status === 'running');
    if (!activeRun && selectedRunId === null) return;

    runPollRef.current = setInterval(async () => {
      try {
        if (selectedRunId) {
          const run = await srv.getOpenCodeRun(selectedRunId);
          const updated = cliRuns.map(r => r.id === run.id ? run : r);
          setCliRuns(updated);
          setCliOutput(run.output);
          if (run.status !== 'running') { setSelectedRunId(null); setCliRunning(false); }
        }
      } catch { /* ignore */ }
    }, 2000);

    return () => { if (runPollRef.current) clearInterval(runPollRef.current); };
  }, [selectedRunId, cliRuns]);

  // ---- 操作 ----
  const startWeb = async () => {
    setStartingWeb(true);
    try {
      const result = await srv.startOpenCodeWeb(startPort, startCors);
      if (result.reused) {
        message.success(`复用已有 opencode serve: ${result.url}`);
      } else {
        message.success(`opencode serve 已启动: ${result.url}`);
      }
      // 自动选中
      setSelectedUrl(result.url);
      localStorage.setItem(OPENCODE_URL_KEY, result.url);
      await loadStatus();
    } catch (e: any) {
      message.error(e?.response?.data?.message || '启动 opencode serve 失败');
    } finally {
      setStartingWeb(false);
    }
  };

  const stopWeb = async (port: number) => {
    try {
      await srv.stopOpenCodeWeb(port);
      message.success(`已停止端口 ${port} 的 opencode serve`);
      if (selectedUrl.startsWith(`http://127.0.0.1:${port}`)) {
        setSelectedUrl('');
        localStorage.removeItem(OPENCODE_URL_KEY);
      }
      await loadStatus();
    } catch (e: any) {
      message.error(e?.response?.data?.message || '停止失败');
    }
  };

  const runCli = async () => {
    const p = cliPrompt.trim();
    if (!p) return;
    setCliRunning(true);
    setCliOutput('');
    setSelectedRunId(null);
    try {
      const run = await srv.runOpenCodeCli(p);
      setCliRuns(prev => [run, ...prev]);
      if (run.status === 'done' || run.status === 'error') {
        setCliOutput(run.output);
        setCliRunning(false);
      } else {
        // 仍在运行中，等待轮询
        setSelectedRunId(run.id);
      }
      setCliPrompt('');
    } catch (e: any) {
      message.error(e?.response?.data?.message || 'CLI 执行失败');
      setCliRunning(false);
    }
  };

  const selectService = (url: string) => {
    setSelectedUrl(url);
    localStorage.setItem(OPENCODE_URL_KEY, url);
    message.success(`已选择 opencode 服务: ${url}`);
  };

  // ---- 渲染 ----
  if (!status) {
    return <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* ===== 安装状态 ===== */}
      <Card size="small" title={<><ApiOutlined /> OpenCode 本地服务</>}
        extra={<Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={loadStatus}>刷新</Button>}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="安装状态">
              {status.installed
                ? <Tag color="green">已安装</Tag>
                : <Tag color="red">未安装</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="版本">{status.version || '-'}</Descriptions.Item>
            <Descriptions.Item label="路径" span={2}>
              <Text code copyable>{status.path || '-'}</Text>
            </Descriptions.Item>
          </Descriptions>

          {!status.installed && (
            <Alert type="warning" showIcon
              message="未检测到 opencode CLI"
              description="请先安装 opencode：npm i -g @opencode-ai/cli，或参考 https://docs.opencode.ai" />
          )}
        </Space>
      </Card>

      {/* ===== Web Server ===== */}
      {status.installed && (
        <Card size="small" title={<><RocketOutlined /> Web 服务</>}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* 启动区域 */}
            <Space wrap>
              <Text>端口：</Text>
              <Input type="number" size="small" style={{ width: 80 }} value={startPort}
                onChange={e => setStartPort(Number(e.target.value) || 4096)} />
              <Text>CORS：</Text>
              <Input size="small" style={{ width: 220 }} value={startCors}
                onChange={e => setStartCors(e.target.value)} />
              <Button type="primary" icon={<PlayCircleOutlined />} loading={startingWeb}
                onClick={startWeb}>
                启动 Web
              </Button>
            </Space>

            {/* 运行中的实例 */}
            <div>
              <Text type="secondary">运行中的实例：</Text>
              {status.running_instances.length === 0 && (
                <div><Text type="secondary">- 无运行中实例 -</Text></div>
              )}
              {status.running_instances.map((inst: OpenCodeWebInstance) => (
                <Card key={inst.pid} size="small" style={{ marginTop: 8 }}
                  styles={{ body: { padding: '8px 12px' } }}>
                  <Space wrap>
                    <Tag color="green">运行中</Tag>
                    <Text strong copyable>{inst.url}</Text>
                    <Text type="secondary">PID: {inst.pid}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      启动于 {inst.started_at ? fmtDateTime(new Date(inst.started_at * 1000)) : '-'}
                    </Text>
                    <Button size="small" type="primary" ghost
                      onClick={() => selectService(inst.url)}>
                      {selectedUrl === inst.url ? '✓ 已选中' : '设为对话服务'}
                    </Button>
                    <Button size="small" danger icon={<StopOutlined />}
                      onClick={() => stopWeb(inst.port)}>停止</Button>
                  </Space>
                </Card>
              ))}
            </div>

            {/* 当前选中的服务 */}
            {selectedUrl && (
              <Alert type="info" showIcon
                message="当前对话工作台使用此 OpenCode 服务"
                description={<Text code copyable>{selectedUrl}</Text>} />
            )}
          </Space>
        </Card>
      )}

      {/* ===== CLI 一次性执行 ===== */}
      {status.installed && (
        <Card size="small" title={<><SendOutlined /> CLI 一次性执行</>}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space.Compact style={{ width: '100%' }}>
              <TextArea
                rows={2}
                placeholder="输入 prompt，例如：用 Python 写一个冒泡排序"
                value={cliPrompt}
                onChange={e => setCliPrompt(e.target.value)}
                onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); runCli(); } }}
                disabled={cliRunning}
              />
            </Space.Compact>
            <Button type="primary" icon={<SendOutlined />} loading={cliRunning}
              onClick={runCli} disabled={!cliPrompt.trim()}>
              执行
            </Button>

            {/* 输出 */}
            {cliOutput && (
              <Card size="small" title="输出" styles={{ body: { padding: 8 } }}>
                <pre style={{
                  background: '#1e1e1e', color: '#d4d4d4', padding: 12, borderRadius: 4,
                  maxHeight: 400, overflow: 'auto', fontSize: 12, margin: 0, whiteSpace: 'pre-wrap',
                }}>
                  {cliOutput}
                </pre>
              </Card>
            )}

            {/* CLI 运行历史 */}
            {cliRuns.length > 0 && (
              <div>
                <Text type="secondary">历史执行记录：</Text>
                {cliRuns.slice(0, 10).map(r => (
                  <Card key={r.id} size="small" hoverable
                    style={{ marginTop: 6 }}
                    styles={{ body: { padding: '6px 10px' } }}
                    onClick={() => { setSelectedRunId(r.id); setCliOutput(r.output); }}>
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space>
                        <Tag color={r.status === 'done' ? 'green' : r.status === 'error' ? 'red' : r.status === 'running' ? 'blue' : 'default'}>
                          {r.status}
                        </Tag>
                        <Text ellipsis={{ tooltip: true }} style={{ maxWidth: 500 }}>{r.prompt}</Text>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {fmtDateTime(new Date(r.started_at * 1000))}
                        {r.finished_at && ` · 耗时 ${fmtDuration((r.finished_at - r.started_at) * 1000)}`}
                      </Text>
                    </Space>
                  </Card>
                ))}
              </div>
            )}
          </Space>
        </Card>
      )}
    </div>
  );
}
