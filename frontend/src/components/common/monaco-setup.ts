/**
 * Monaco 一次性初始化：注册 SQL 方言 + 深色主题 + worker 路由。
 *
 * 说明：@monaco-editor/react 默认从 CDN 懒加载 Monaco；本文件在 SqlEditor 挂载前
 * 调用一次 `configureMonaco(monaco)`（通过 beforeMount），把 monaco-sql-languages
 * 的 mysql/pgsql/sqlite 语言贡献注册进去，再定义 ontomind-dark 主题。
 */
import type * as MonacoNS from 'monaco-editor';

let configured = false;

export const ONTOMIND_DARK_THEME_ID = 'ontomind-dark' as const;

export type SupportedDialect = 'mysql' | 'postgresql' | 'sqlite';

/**
 * dialect → monaco languageId。monaco-sql-languages 提供了 mysql / pgsql / sqlite。
 * 输入 dialect 是我们对外的语义名，输出是 monaco 内部注册的 language id。
 */
export function monacoLanguageForDialect(dialect: SupportedDialect): string {
  if (dialect === 'mysql') return 'mysql';
  if (dialect === 'postgresql') return 'pgsql';
  return 'sql'; // sqlite 无专用注册，用通用 sql fallback
}

export function configureMonaco(monaco: typeof MonacoNS): void {
  if (configured) return;
  configured = true;

  // 定义 ontomind-dark 主题。颜色对齐 --code-bg / --code-fg / --accent-purple。
  monaco.editor.defineTheme(ONTOMIND_DARK_THEME_ID, {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'keyword.sql', foreground: 'a78bfa', fontStyle: 'bold' },
      { token: 'keyword', foreground: 'a78bfa', fontStyle: 'bold' },
      { token: 'string.sql', foreground: '34d399' },
      { token: 'string', foreground: '34d399' },
      { token: 'number.sql', foreground: 'fbbf24' },
      { token: 'number', foreground: 'fbbf24' },
      { token: 'comment.sql', foreground: '506080', fontStyle: 'italic' },
      { token: 'comment', foreground: '506080', fontStyle: 'italic' },
      { token: 'operator.sql', foreground: '60a5fa' },
      { token: 'identifier.sql', foreground: 'd1d9e6' },
    ],
    colors: {
      'editor.background': '#0a0f1f',
      'editor.foreground': '#d1d9e6',
      'editorLineNumber.foreground': '#506080',
      'editorLineNumber.activeForeground': '#8895b4',
      'editor.selectionBackground': '#3b82f633',
      'editor.lineHighlightBackground': '#111827',
      'editorCursor.foreground': '#60a5fa',
      'editorIndentGuide.background': '#1a2036',
      'editorIndentGuide.activeBackground': '#3b82f6',
      'editor.wordHighlightBackground': '#3b82f622',
      'scrollbarSlider.background': '#4b5f8033',
      'scrollbarSlider.hoverBackground': '#4b5f8066',
    },
  });

  // 语言贡献：monaco-sql-languages 的 side-effect import 会在被真正 import 时
  // 自行注册；此处只是提示存在（真正的 import 发生在 SqlEditor.tsx，避免在
  // vitest 里被强拉进来）。
}

/**
 * 供 SchemaTree / SqlEditor 共用的 schema shape。
 */
export interface SchemaHint {
  tables: {
    name: string;
    columns: { name: string; type?: string }[];
  }[];
}

/**
 * 注册一个基于 SchemaHint 的补全 provider。
 * - 遇到 `<table>.` → 推该表的列。
 * - 否则 → 推所有表名 + 常用 SELECT 关键字。
 * 返回 dispose 函数供 unmount 清理。
 */
export function registerSchemaCompletion(
  monaco: typeof MonacoNS,
  languageId: string,
  getSchema: () => SchemaHint | undefined,
): MonacoNS.IDisposable {
  return monaco.languages.registerCompletionItemProvider(languageId, {
    triggerCharacters: [' ', '.', ',', '\n'],
    provideCompletionItems: (model, position) => {
      const schema = getSchema();
      if (!schema) return { suggestions: [] };

      const word = model.getWordUntilPosition(position);
      const range: MonacoNS.IRange = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      const linePrefix = model
        .getLineContent(position.lineNumber)
        .slice(0, position.column - 1);
      const dotMatch = linePrefix.match(/(\w+)\.$/);

      if (dotMatch) {
        const tableName = dotMatch[1];
        const table = schema.tables.find(
          (t) => t.name.toLowerCase() === tableName.toLowerCase(),
        );
        if (!table) return { suggestions: [] };
        return {
          suggestions: table.columns.map((c) => ({
            label: c.name,
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: c.name,
            detail: c.type ?? 'column',
            range,
          })),
        };
      }

      const tableSug: MonacoNS.languages.CompletionItem[] = schema.tables.map(
        (t) => ({
          label: t.name,
          kind: monaco.languages.CompletionItemKind.Class,
          insertText: t.name,
          detail: `table (${t.columns.length} cols)`,
          range,
        }),
      );
      const keywords = [
        'SELECT',
        'FROM',
        'WHERE',
        'GROUP BY',
        'ORDER BY',
        'LIMIT',
        'JOIN',
        'LEFT JOIN',
        'INNER JOIN',
        'ON',
        'AS',
        'DISTINCT',
        'COUNT(*)',
        'SUM(',
        'AVG(',
        'MIN(',
        'MAX(',
      ].map<MonacoNS.languages.CompletionItem>((k) => ({
        label: k,
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: k,
        range,
      }));
      return { suggestions: [...tableSug, ...keywords] };
    },
  });
}
