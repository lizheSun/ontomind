/**
 * ChatComposer — opencode-style prompt input.
 *
 * 视觉：一个圆角边框容器包住 textarea + 底部工具条 (mode switcher / hints / model switcher / send).
 * 交互：`/` `@` 弹 popover；Enter 发送；Shift+Enter 换行；Esc 关 popover；
 *      popover 打开时 ↑↓Enter/Tab/Esc 让给 popover 处理；
 *      Cmd/Ctrl + . 循环切换 primary agent；
 *      Cmd/Ctrl + M 打开 model switcher.
 */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { message } from 'antd';
import * as oc from '../client';
import { useAgents } from '../hooks/useAgents';
import { useCommands } from '../hooks/useCommands';
import { useSendPrompt } from '../hooks/useSendPrompt';
import { useSessions } from '../hooks/useSessions';
import { useOpencodeStore } from '../stores/opencodeStore';
import ModelSwitcher from './ModelSwitcher';
import SlashPopover from './SlashPopover';
import MentionPopover from './MentionPopover';
import type { OcCommand } from '../types';

type PopKind = 'slash' | 'mention' | null;

interface TokenInfo {
  kind: PopKind;
  query: string;
  triggerStart: number;
  cursor: number;
}

const HIDDEN_AGENTS = new Set(['compaction', 'summary', 'title']);

function detectToken(value: string, cursor: number): TokenInfo {
  let i = cursor - 1;
  while (i >= 0) {
    const ch = value[i];
    if (ch === '\n' || ch === ' ' || ch === '\t') break;
    if (ch === '/' || ch === '@') {
      const before = i > 0 ? value[i - 1] : '';
      const okBefore = i === 0 || before === ' ' || before === '\n' || before === '\t';
      if (!okBefore) return { kind: null, query: '', triggerStart: -1, cursor };
      const query = value.slice(i + 1, cursor);
      if (/[\s]/.test(query)) return { kind: null, query: '', triggerStart: -1, cursor };
      return {
        kind: ch === '/' ? 'slash' : 'mention',
        query,
        triggerStart: i,
        cursor,
      };
    }
    i--;
  }
  return { kind: null, query: '', triggerStart: -1, cursor };
}

// 极简纸飞机（editorial：单线 + 内 fold line）
function IconSend() {
  return (
    <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2L2 7.2l4.6 1.6L14 2z" />
      <path d="M14 2L8.4 14l-1.8-5.2" />
      <path d="M6.6 8.8L14 2" />
    </svg>
  );
}
// 圆角方块
function IconStop() {
  return (
    <svg viewBox="0 0 16 16" width="11" height="11" fill="currentColor" aria-hidden="true">
      <rect x="4" y="4" width="8" height="8" rx="1.5" />
    </svg>
  );
}

export default function ChatComposer() {
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [cursor, setCursor] = useState(0);
  const [popoverEnabled, setPopoverEnabled] = useState(true);
  const [openModelTrigger, setOpenModelTrigger] = useState(0);
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  const activeSessionId = useOpencodeStore((s) => s.activeSessionId);
  const streaming = useOpencodeStore((s) => s.streaming);
  const currentAgent = useOpencodeStore((s) => s.currentAgent);
  const setCurrentAgent = useOpencodeStore((s) => s.setCurrentAgent);
  const send = useSendPrompt();
  const { create } = useSessions();
  const { commands, loading: cmdLoading } = useCommands();
  const { agents } = useAgents();

  const token = useMemo(() => detectToken(text, cursor), [text, cursor]);
  const showSlash = popoverEnabled && token.kind === 'slash';
  const showMention = popoverEnabled && token.kind === 'mention';

  useEffect(() => {
    setPopoverEnabled(true);
  }, [token.kind, token.query]);

  // 全局快捷键：Cmd/Ctrl+.  循环切换 primary agent；Cmd/Ctrl+M 打开模型切换
  useEffect(() => {
    const primaries = agents
      .filter((a) => a.mode === 'primary' && !HIDDEN_AGENTS.has(a.name))
      .map((a) => a.name)
      .sort((a, b) => {
        const rank = (n: string) => (n === 'build' ? 0 : n === 'plan' ? 1 : 2);
        return rank(a) - rank(b) || a.localeCompare(b);
      });

    const handler = (e: KeyboardEvent<Element> | globalThis.KeyboardEvent) => {
      const ev = e as globalThis.KeyboardEvent;
      const mod = ev.metaKey || ev.ctrlKey;
      if (!mod) return;
      if (ev.key === '.') {
        if (primaries.length < 2) return;
        ev.preventDefault();
        const idx = Math.max(0, primaries.indexOf(currentAgent));
        const next = primaries[(idx + 1) % primaries.length];
        setCurrentAgent(next);
      } else if (ev.key === 'm' || ev.key === 'M') {
        // 避免 Cmd+Shift+M 之类被吞
        if (ev.shiftKey || ev.altKey) return;
        ev.preventDefault();
        setOpenModelTrigger((v) => v + 1);
      }
    };
    window.addEventListener('keydown', handler as EventListener);
    return () => window.removeEventListener('keydown', handler as EventListener);
  }, [agents, currentAgent, setCurrentAgent]);

  const canSend = text.trim().length > 0 && !sending && !showSlash && !showMention;

  const submit = async () => {
    if (sending || showSlash || showMention) return;
    const value = text.trim();
    if (!value) return;
    setText('');
    setSending(true);
    try {
      let sid = activeSessionId;
      if (!sid) {
        const s = await create(value.slice(0, 30) || '新对话');
        sid = s.id;
      }
      await send(sid, value);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '发送失败');
      setText(value);
    } finally {
      setSending(false);
    }
  };

  const abort = async () => {
    if (!activeSessionId) return;
    try {
      await oc.abortSession(activeSessionId);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '中止失败');
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 中文输入法组词期间：Enter 是选字，不发送。
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const composing = (e as any).nativeEvent?.isComposing || e.keyCode === 229;
    if (composing) return;

    if (showSlash || showMention) {
      if (['ArrowUp', 'ArrowDown', 'Enter', 'Escape', 'Tab'].includes(e.key)) return;
    }
    if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      void submit();
    }
  };

  const replaceToken = (replacement: string) => {
    if (token.triggerStart < 0) return;
    let before = text.slice(0, token.triggerStart);
    const after = text.slice(token.cursor);
    // 防御：replacement 若以 trigger char 开头(@/) 且 before 末尾又是同一个 trigger char，
    // 说明是历史遗留状态导致 double-trigger，吞掉 before 末尾那个字符。
    const firstCh = replacement.charAt(0);
    if ((firstCh === '@' || firstCh === '/') && before.endsWith(firstCh)) {
      before = before.slice(0, -1);
    }
    const next = before + replacement + after;
    setText(next);
    const newCursor = before.length + replacement.length;
    requestAnimationFrame(() => {
      const el = taRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(newCursor, newCursor);
        setCursor(newCursor);
      }
    });
  };

  const onPickCommand = (cmd: OcCommand) => replaceToken(`/${cmd.name} `);
  const onPickFile = (val: string) => replaceToken(`${val} `);

  const trackCursor = (el: HTMLTextAreaElement) => setCursor(el.selectionStart ?? 0);

  return (
    <div className="oc-composer">
      <SlashPopover
        visible={showSlash}
        query={token.query}
        commands={commands}
        loading={cmdLoading}
        onSelect={onPickCommand}
        onClose={() => setPopoverEnabled(false)}
      />
      <MentionPopover
        visible={showMention}
        query={token.query}
        onSelect={onPickFile}
        onClose={() => setPopoverEnabled(false)}
      />
      <div className="oc-composer-inner">
        <textarea
          ref={taRef}
          value={text}
          placeholder={
            activeSessionId
              ? '发送消息…  / 命令  @ 文件'
              : '发送消息以开始新会话…  / 命令  @ 文件'
          }
          rows={2}
          onChange={(e) => {
            setText(e.target.value);
            trackCursor(e.target as HTMLTextAreaElement);
          }}
          onKeyDown={onKeyDown}
          onKeyUp={(e) => trackCursor(e.target as HTMLTextAreaElement)}
          onClick={(e) => trackCursor(e.target as HTMLTextAreaElement)}
          onSelect={(e) => trackCursor(e.target as HTMLTextAreaElement)}
        />
        <div className="oc-composer-toolbar">
          <div className="oc-composer-toolbar-left">
            <span className="oc-hint-chip">/</span>
            <span className="oc-hint-chip">@</span>
          </div>
          <div className="oc-composer-toolbar-right">
            <ModelSwitcher openTrigger={openModelTrigger} />
            {streaming && (
              <button className="oc-btn oc-btn-danger" onClick={() => void abort()}>
                <IconStop />
                <span>Stop</span>
              </button>
            )}
            <button
              className="oc-btn"
              disabled={!canSend}
              onClick={() => void submit()}
            >
              <IconSend />
              <span>{sending ? 'Sending…' : 'Send'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
