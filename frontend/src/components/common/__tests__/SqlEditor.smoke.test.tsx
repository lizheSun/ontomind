import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SqlEditor } from '../SqlEditor';

describe('SqlEditor (smoke)', () => {
  it('mounts without throwing (monaco stubbed by test-setup)', () => {
    const onChange = vi.fn();
    render(
      <SqlEditor
        value="SELECT 1"
        onChange={onChange}
        dialect="mysql"
        data-testid="editor"
      />,
    );
    // The mock in test-setup.ts renders a <textarea data-testid="monaco-mock"> inside our wrapper
    expect(screen.getByTestId('editor')).toBeInTheDocument();
  });

  it('forwards value + onChange through the mock', async () => {
    const onChange = vi.fn();
    render(
      <SqlEditor
        value="SELECT NOW()"
        onChange={onChange}
        dialect="postgresql"
        data-testid="editor2"
      />,
    );
    const textarea = await screen.findByTestId('monaco-mock');
    expect(textarea).toBeInTheDocument();
    expect((textarea as HTMLTextAreaElement).value).toBe('SELECT NOW()');
  });
});
