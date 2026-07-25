/**
 * OpenCode 对话工作台的公共导出.
 * 页面层只需 `import { OpencodeGuard, ChatWorkspaceShell } from '@/features/opencode'`.
 */
export { default as OpencodeGuard } from './components/OpencodeGuard';
export { default as ChatWorkspaceShell } from './components/ChatWorkspaceShell';
export { default as SessionListSidebar } from './components/SessionListSidebar';
export { default as ChatMessageList } from './components/ChatMessageList';
export { default as ChatComposer } from './components/ChatComposer';
export { default as PermissionDialog } from './components/PermissionDialog';
export { default as AgentModeSwitcher } from './components/AgentModeSwitcher';
export { default as ModelSwitcher } from './components/ModelSwitcher';
export { default as SettingsDialog } from './components/SettingsDialog';

export * as opencodeClient from './client';
export { useOpencodeStore } from './stores/opencodeStore';

export type * from './types';
