/**
 * MessagePart — opencode-style 消息 part 渲染 (受 useOcSettings 控制).
 */
import { useState } from 'react';
import type { OcPart } from '../types';
import { useOcSettings } from '../hooks/useOcSettings';

interface P {
  part: OcPart;
}

function TextView({ text }: { text: string }) {
  return <div className="oc-part-text">{text}</div>;
}

function ReasoningView({ text }: { text: string }) {
  return <div className="oc-part-reasoning">{text}</div>;
}

const EDIT_TOOLS = new Set(['edit', 'write', 'patch', 'multiedit']);
const SHELL_TOOLS = new Set(['bash', 'shell', 'run']);

function ToolView({ part }: { part: OcPart & { type: 'tool' } }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const p = part as any;
  const status = p.state?.status || 'pending';
  const input = p.state?.input;
  const output = p.state?.output;
  const err = p.state?.error;
  const toolName = String(p.tool || '').toLowerCase();

  const { settings } = useOcSettings();
  const isEdit = EDIT_TOOLS.has(toolName);
  const isShell = SHELL_TOOLS.has(toolName);
  const defaultOpen =
    (isEdit && settings.expandEditTool) ||
    (isShell && settings.expandShellTool) ||
    status === 'error';

  const [open, setOpen] = useState<boolean>(defaultOpen);
  const hasBody = input || output || err;

  return (
    <div className="oc-part-tool">
      <button
        type="button"
        className="oc-part-tool-head"
        onClick={() => hasBody && setOpen((v) => !v)}
        style={{
          cursor: hasBody ? 'pointer' : 'default',
          border: 'none',
          background: 'inherit',
          textAlign: 'left',
          width: '100%',
        }}
      >
        <span className="oc-part-tool-name">{p.tool}</span>
        <span className="oc-part-tool-status" data-status={status}>{status}</span>
      </button>
      {hasBody && open && (
        <div className="oc-part-tool-body">
          {input && (
            <div>
              <div className="oc-part-tool-block-title">Input</div>
              <pre>{typeof input === 'string' ? input : JSON.stringify(input, null, 2)}</pre>
            </div>
          )}
          {output && (
            <div>
              <div className="oc-part-tool-block-title">Output</div>
              <pre>{typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</pre>
            </div>
          )}
          {err && (
            <div>
              <div className="oc-part-tool-block-title">Error</div>
              <pre style={{ color: 'var(--danger, #a5361e)' }}>{err}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FileView({ part }: { part: OcPart & { type: 'file' } }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const p = part as any;
  return <span className="oc-part-file">📎 {p.filename || p.url || 'file'}</span>;
}

export default function MessagePart({ part }: P) {
  const { settings } = useOcSettings();
  switch (part.type) {
    case 'text':
      return <TextView text={(part as { text: string }).text || ''} />;
    case 'reasoning':
      if (!settings.showReasoningSummaries) return null;
      return <ReasoningView text={(part as { text: string }).text || ''} />;
    case 'tool':
      return <ToolView part={part as OcPart & { type: 'tool' }} />;
    case 'file':
      return <FileView part={part as OcPart & { type: 'file' }} />;
    case 'step-start':
    case 'step-finish':
    case 'snapshot':
    case 'patch':
      return null;
    default:
      return null;
  }
}
