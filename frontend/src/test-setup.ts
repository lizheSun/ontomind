import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Monaco 在 jsdom 里跑不了 worker，用轻量 stub。任何 SqlEditor smoke test
// 只需要断言组件挂载不报错。
vi.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: (props: {
    value?: string;
    onChange?: (v: string) => void;
    height?: number | string;
    ['data-testid']?: string;
  }) => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const React = require('react');
    return React.createElement('textarea', {
      'data-testid': props['data-testid'] || 'monaco-mock',
      value: props.value ?? '',
      onChange: (e: any) => props.onChange?.(e.target.value),
      style: { height: props.height ?? 300 },
    });
  },
  Editor: (props: any) => {
    const React = require('react');
    return React.createElement('textarea', {
      'data-testid': 'monaco-mock',
      value: props.value ?? '',
      onChange: (e: any) => props.onChange?.(e.target.value),
    });
  },
  loader: { config: () => {} },
}));

vi.mock('monaco-editor', () => ({}));
vi.mock('monaco-sql-languages', () => ({
  LanguageIdEnum: { MYSQL: 'mysql', PG: 'pgsql' },
  setupLanguageFeatures: () => {},
}));

// jsdom lacks matchMedia — AntD ConfigProvider touches it.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
