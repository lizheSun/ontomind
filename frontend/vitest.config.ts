import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    passWithNoTests: true,
    setupFiles: [fileURLToPath(new URL('./src/test-setup.ts', import.meta.url))],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/components/common/**', 'src/services/**', 'src/stores/**'],
    },
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
  },
});
