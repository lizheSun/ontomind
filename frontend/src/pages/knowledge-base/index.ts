import { createElement } from 'react';
import { Navigate } from 'react-router-dom';

export { default as KbLibraryLayout } from './KbLibraryLayout';
export { default as DataAssetsPage } from './DataAssetsPage';
export { default as CodeReposPage } from './CodeReposPage';
export { default as DocumentsPage } from './DocumentsPage';
export { default as ExperiencesPage } from './ExperiencesPage';
export { default as KbSearchPage } from './KbSearchPage';
export { default as EntryFormDrawer } from './components/EntryFormDrawer';
export type {
  SchemaKey,
  EntryField,
  EntryFormValues,
} from './components/EntryFormDrawer';

// Default export mirrors the /knowledge-base index redirect (kept in sync with
// `./index.tsx`) so this barrel can be used as `import Kb from '.../knowledge-base'`.
export default function KnowledgeBaseIndex() {
  return createElement(Navigate, {
    to: '/knowledge-base/data-assets',
    replace: true,
  });
}
