/**
 * 通用组件（2026-08-03 深度精简后只剩 4 个）
 *
 * 🗑️ 已删除的组件（随四模块下线成为孤儿）：
 * - `SqlEditor` / `ResultGrid` / `SchemaTree` / `DataTable` / `monaco-setup`
 *   （数据平台专用，拖着 monaco-editor 6.9MB worker）
 * - `AgentChatPanel` / `AgentPicker`（对话工作台 / Agent Looper 专用）
 * - `PageHeader` / `SectionTitle` / `StatCard` / `TagPill` / `DangerConfirm`（无人引用）
 */
export { GlassPanel } from './GlassPanel';
export { EmptyState } from './EmptyState';
export { CmdKOmnibar } from './CmdKOmnibar';
export type { CmdKOmnibarProps } from './CmdKOmnibar';
export { BrandMark } from './BrandMark';
export { PageHeader } from './PageHeader';
export { StatusDot } from './StatusDot';
export {
  ZenGodToggle,
  useUIMode,
  useProgressiveDisclosure,
  setUIMode,
} from './ZenGodToggle';
export type { UIMode, ZenGodToggleProps } from './ZenGodToggle';
