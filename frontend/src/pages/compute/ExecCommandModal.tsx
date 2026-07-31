/**
 * ExecCommandModal — 容器内一次性命令执行（非交互）.
 *
 * 输入命令 → 调 POST /exec → 展示 exit_code / stdout / stderr。
 * 适合快速跑一条命令（如 opencode --version / ls -la），无需完整终端。
 */
import { useState } from 'react';
import { Input, Modal, Tag } from 'antd';
import * as srv from '../../services/compute.service';

interface Props {
  open: boolean;
  onClose: () => void;
  nodeId: number | null;
  cid: string | null;
  containerName?: string;
}

export default function ExecCommandModal({ open, onClose, nodeId, cid, containerName }: Props) {
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState('');
  const [exitCode, setExitCode] = useState<number | null>(null);
  const [running, setRunning] = useState(false);

  const run = async () => {
    if (!command.trim() || nodeId == null || !cid) return;
    setRunning(true);
    setOutput('');
    setExitCode(null);
    try {
      const result = await srv.execContainerCommand(nodeId, cid, { command: command.trim() });
      const parts: string[] = [];
      if (result.stdout) parts.push(result.stdout);
      if (result.stderr) parts.push(`\x1b[33m[stderr]\x1b[0m\n${result.stderr}`);
      setOutput(parts.join('\n') || '(无输出)');
      setExitCode(result.exit_code);
    } catch (e: any) {
      setOutput(e?.response?.data?.message ?? String(e));
      setExitCode(-1);
    } finally {
      setRunning(false);
    }
  };

  const handleClose = () => {
    onClose();
    setOutput('');
    setExitCode(null);
    setCommand('');
  };

  return (
    <Modal
      title={`执行命令 · ${containerName ?? ''}`}
      open={open}
      onCancel={handleClose}
      footer={null}
      width={680}
      destroyOnHidden
    >
      <Input.Search
        size="large"
        placeholder="输入命令，如 ls -la / 或 opencode --version"
        enterButton="执行"
        loading={running}
        value={command}
        onChange={(e) => setCommand(e.target.value)}
        onSearch={() => void run()}
        onPressEnter={() => void run()}
        style={{ fontFamily: 'var(--font-mono)' }}
      />
      {exitCode !== null && (
        <div style={{ margin: '10px 0 6px' }}>
          <Tag color={exitCode === 0 ? 'green' : 'red'}>exit {exitCode}</Tag>
        </div>
      )}
      {(output || running) && (
        <pre className="exec-output">{output || (running ? '执行中...' : '')}</pre>
      )}
    </Modal>
  );
}
