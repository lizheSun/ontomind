export { default as SourcesListPage } from './SourcesListPage';
export { default as SourceFormDrawer } from './components/SourceFormDrawer';
// Preserve the existing default (the /data-platform → /data-platform/sources
// redirect stub introduced in T20) so App.tsx keeps resolving.
export { default } from './index.tsx';
