import { useCallback, useEffect, useRef, useState } from 'react';

type SpeechRec = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((ev: SpeechResultEvent) => void) | null;
  onerror: ((ev: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechResultEvent = {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
};

function getCtor(): (new () => SpeechRec) | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRec;
    webkitSpeechRecognition?: new () => SpeechRec;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function speechSupported(): boolean {
  return getCtor() != null;
}

/** 浏览器语音识别。最终结果追加进草稿，不覆盖；Chrome 会在停顿后结束，需要时自动续上。 */
export function useSpeechDictation(onFinal: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const wanted = useRef(false);
  const recRef = useRef<SpeechRec | null>(null);
  const cb = useRef(onFinal);
  cb.current = onFinal;
  const supported = speechSupported();

  const stop = useCallback(() => {
    wanted.current = false;
    try {
      recRef.current?.stop();
    } catch {
      /* ignore */
    }
    recRef.current = null;
    setListening(false);
  }, []);

  const start = useCallback(() => {
    const Ctor = getCtor();
    if (!Ctor) return;
    stop();
    const rec = new Ctor();
    rec.lang = 'zh-CN';
    rec.continuous = true;
    rec.interimResults = false;
    rec.onresult = (ev) => {
      let chunk = '';
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const row = ev.results[i];
        if (row?.isFinal) chunk += row[0]?.transcript || '';
      }
      const t = chunk.trim();
      if (t) cb.current(t);
    };
    rec.onerror = () => {
      /* onend 会处理续听 / 收尾 */
    };
    rec.onend = () => {
      if (!wanted.current) {
        setListening(false);
        return;
      }
      try {
        rec.start();
      } catch {
        wanted.current = false;
        setListening(false);
      }
    };
    recRef.current = rec;
    wanted.current = true;
    setListening(true);
    try {
      rec.start();
    } catch {
      wanted.current = false;
      setListening(false);
    }
  }, [stop]);

  const toggle = useCallback(() => {
    if (listening) stop();
    else start();
  }, [listening, start, stop]);

  useEffect(() => () => stop(), [stop]);

  return { supported, listening, toggle, stop };
}
