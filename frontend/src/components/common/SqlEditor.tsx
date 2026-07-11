import { useCallback, useEffect, useMemo, useRef } from 'react';
import type React from 'react';
import Editor, { type OnMount, type BeforeMount } from '@monaco-editor/react';
import type * as MonacoNS from 'monaco-editor';
import {
  ONTOMIND_DARK_THEME_ID,
  configureMonaco,
  monacoLanguageForDialect,
  registerSchemaCompletion,
  type SchemaHint,
  type SupportedDialect,
} from './monaco-setup';

// monaco-sql-languages 的 side-effect contribution：这行必须发生在 mount 之前，
// 但只需一次。用 top-level dynamic import 结果会被 vitest 拉进来 → 我们改成
// 在 beforeMount 里再触发（延迟到浏览器）。
async function ensureSqlLanguages(): Promise<void> {
  await Promise.all([
    import('monaco-sql-languages/esm/languages/mysql/mysql.contribution'),
    import('monaco-sql-languages/esm/languages/pgsql/pgsql.contribution'),
  ]);
}

export interface SqlEditorProps {
  value: string;
  onChange: (v: string) => void;
  dialect: SupportedDialect;
  schema?: SchemaHint;
  onRun?: (value: string) => void;
  height?: number | string;
  readOnly?: boolean;
  'data-testid'?: string;
}

export const SqlEditor: React.FC<SqlEditorProps> = ({
  value,
  onChange,
  dialect,
  schema,
  onRun,
  height = 320,
  readOnly = false,
  'data-testid': testId,
}) => {
  const editorRef = useRef<MonacoNS.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof MonacoNS | null>(null);
  const disposeRef = useRef<MonacoNS.IDisposable | null>(null);
  const schemaRef = useRef<SchemaHint | undefined>(schema);
  // 保持 schemaRef 与最新 schema 同步（供 completion provider 通过 getSchema 读取）
  useEffect(() => {
    schemaRef.current = schema;
  }, [schema]);

  const languageId = useMemo(() => monacoLanguageForDialect(dialect), [dialect]);

  const beforeMount: BeforeMount = useCallback(async (monaco) => {
    configureMonaco(monaco);
    // 语言贡献异步注册，不阻塞 mount（若失败也不影响编辑功能，只是失去高亮）
    await ensureSqlLanguages().catch(() => {
      /* noop: SQL syntax will fall back to plain text */
    });
  }, []);

  const handleMount: OnMount = useCallback(
    (editor, monaco) => {
      editorRef.current = editor;
      monacoRef.current = monaco;
      // 注册 schema completion
      disposeRef.current = registerSchemaCompletion(
        monaco,
        languageId,
        () => schemaRef.current,
      );
      // Cmd/Ctrl+Enter → onRun
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
        const current = editor.getValue();
        onRun?.(current);
      });
    },
    [languageId, onRun],
  );

  useEffect(() => {
    return () => {
      disposeRef.current?.dispose();
      disposeRef.current = null;
    };
  }, []);

  return (
    <div
      data-testid={testId ?? 'sql-editor'}
      style={{
        borderRadius: 12,
        overflow: 'hidden',
        border: '1px solid var(--dp-panel-border, rgba(59,130,246,0.14))',
        background: 'var(--code-bg, #0a0f1f)',
      }}
    >
      <Editor
        beforeMount={beforeMount}
        onMount={handleMount}
        language={languageId}
        theme={ONTOMIND_DARK_THEME_ID}
        value={value}
        onChange={(v) => onChange(v ?? '')}
        height={height}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 13.5,
          fontFamily: 'var(--font-mono, ui-monospace, monospace)',
          lineNumbers: 'on',
          renderLineHighlight: 'all',
          scrollBeyondLastLine: false,
          smoothScrolling: true,
          padding: { top: 12, bottom: 12 },
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
        }}
      />
    </div>
  );
};
