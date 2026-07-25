/**
 * OpenCode 数据类型 (v1.18.4).
 *
 * 类型语义与 SDK `@opencode-ai/sdk` 的 `types.gen.ts` 一致。
 * 只列前端实际用到的字段；opencode 端可能返回更多，用 `unknown` 兜底.
 */

// ============================================================
// 通用
// ============================================================
export interface OcHealth {
  healthy: boolean;
  version?: string;
}

// ============================================================
// Session
// ============================================================
export interface OcSession {
  id: string;
  parentID?: string | null;
  title?: string;
  version?: string;
  time?: {
    created: number;
    updated: number;
  };
  share?: {
    url?: string;
  };
  revert?: unknown;
}

// ============================================================
// Message / Part
// ============================================================
export type OcRole = 'user' | 'assistant' | 'system';

export interface OcMessageInfo {
  id: string;
  role: OcRole;
  sessionID: string;
  time?: {
    created: number;
    completed?: number;
  };
  modelID?: string;
  providerID?: string;
  error?: { name?: string; message?: string; [k: string]: unknown };
}

/** 消息 part 联合类型；未穷举完整列表，未知 type 走 fallback 渲染. */
export type OcPart =
  | OcTextPart
  | OcReasoningPart
  | OcToolPart
  | OcFilePart
  | OcStepStartPart
  | OcStepFinishPart
  | OcSnapshotPart
  | OcPatchPart
  | { type: string; [k: string]: unknown };

export interface OcTextPart {
  id?: string;
  type: 'text';
  text: string;
  synthetic?: boolean;
}

export interface OcReasoningPart {
  id?: string;
  type: 'reasoning';
  text: string;
}

export interface OcToolPart {
  id?: string;
  type: 'tool';
  tool: string;
  callID?: string;
  state?: {
    status: 'pending' | 'running' | 'completed' | 'error';
    input?: Record<string, unknown>;
    output?: string;
    metadata?: Record<string, unknown>;
    error?: string;
  };
}

export interface OcFilePart {
  id?: string;
  type: 'file';
  mime?: string;
  filename?: string;
  url?: string;
}

export interface OcStepStartPart {
  id?: string;
  type: 'step-start';
}

export interface OcStepFinishPart {
  id?: string;
  type: 'step-finish';
  tokens?: { input?: number; output?: number };
  cost?: number;
}

export interface OcSnapshotPart {
  id?: string;
  type: 'snapshot';
  hash?: string;
}

export interface OcPatchPart {
  id?: string;
  type: 'patch';
  files?: string[];
  hash?: string;
}

export interface OcMessagesEnvelope {
  info: OcMessageInfo;
  parts: OcPart[];
}

// ============================================================
// Prompt request
// ============================================================
export interface OcPromptBody {
  messageID?: string;
  model?: { providerID: string; modelID: string };
  agent?: string;
  noReply?: boolean;
  system?: string;
  tools?: unknown;
  parts: OcPart[];
  format?: {
    type: 'text' | 'json_schema';
    schema?: Record<string, unknown>;
    retryCount?: number;
  };
}

// ============================================================
// Permission
// ============================================================
export type OcPermissionResponse = 'once' | 'always' | 'reject';

export interface OcPermission {
  id: string;
  sessionID: string;
  messageID?: string;
  callID?: string;
  type: string; // e.g. "bash", "edit", "fetch"
  title: string;
  metadata?: Record<string, unknown>;
  time?: { created: number };
}

// ============================================================
// Agent / Command / Config
// ============================================================
export interface OcAgent {
  name: string;
  description?: string;
  mode?: string; // 'primary' | 'subagent' | ...
  model?: { providerID: string; modelID: string };
  tools?: Record<string, boolean>;
  prompt?: string;
}

export interface OcCommand {
  name: string;
  description?: string;
  template?: string;
  agent?: string;
  model?: { providerID: string; modelID: string };
}

export interface OcConfig {
  model?: string;
  theme?: string;
  shell?: string | null;
  [k: string]: unknown;
}

// ============================================================
// MCP
// ============================================================
export interface OcMcpStatus {
  name?: string;
  connected: boolean;
  error?: string;
  tools?: string[];
}
export type OcMcpStatusMap = Record<string, OcMcpStatus>;

// ============================================================
// SSE Events
// ============================================================
export type OcEvent =
  | { type: 'server.connected'; properties?: Record<string, unknown> }
  | {
      type: 'message.updated';
      properties: { info: OcMessageInfo };
    }
  | {
      type: 'message.part.updated';
      properties: { part: OcPart & { sessionID?: string; messageID?: string } };
    }
  | {
      type: 'message.removed';
      properties: { sessionID: string; messageID: string };
    }
  | {
      type: 'session.updated';
      properties: { info: OcSession };
    }
  | {
      type: 'session.error';
      properties: { sessionID?: string; error?: { message?: string } };
    }
  | {
      type: 'session.idle';
      properties: { sessionID: string };
    }
  | {
      type: 'permission.updated';
      properties: OcPermission;
    }
  | {
      type: 'permission.replied';
      properties: { sessionID: string; permissionID: string; response: OcPermissionResponse };
    }
  | {
      type: 'file.watcher.updated';
      properties?: Record<string, unknown>;
    }
  | { type: string; properties?: Record<string, unknown> };
