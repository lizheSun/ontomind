/** HTML → Markdown 转换（粘贴企微/Word/网页） */
import { Readability } from '@mozilla/readability';
import DOMPurify from 'dompurify';
import TurndownService from 'turndown';
import { gfm } from 'turndown-plugin-gfm';

export interface ConvertResult {
  markdown: string;
  title?: string;
  warnings: string[];
}

function bytesOfDataUri(src: string): number {
  const i = src.indexOf(',');
  if (i < 0) return 0;
  const b64 = src.slice(i + 1);
  return Math.floor((b64.length * 3) / 4);
}

export function markdownFromPlainText(text: string): string {
  return (text || '').replace(/\r\n/g, '\n').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}

export function htmlToMarkdown(
  html: string,
  opts?: { extractArticle?: boolean },
): ConvertResult {
  const warnings: string[] = [];
  let title: string | undefined;

  const clean = DOMPurify.sanitize(html || '', {
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
    FORBID_ATTR: ['onclick', 'onload', 'onerror', 'onmouseover', 'onfocus', 'onblur'],
  });

  const doc = new DOMParser().parseFromString(clean, 'text/html');
  title = doc.querySelector('title')?.textContent?.trim() || undefined;
  let root: HTMLElement = doc.body;

  if (opts?.extractArticle) {
    try {
      const clone = doc.cloneNode(true) as Document;
      const article = new Readability(clone).parse();
      if (article?.content) {
        title = article.title || title;
        root = new DOMParser().parseFromString(article.content, 'text/html').body;
      }
    } catch {
      warnings.push('Readability 提取失败，已使用全文');
    }
  }

  root.querySelectorAll('o\\:p').forEach((el) => {
    const parent = el.parentNode;
    while (el.firstChild) parent?.insertBefore(el.firstChild, el);
    el.remove();
  });

  let imgCount = 0;
  let imgBytes = 0;
  root.querySelectorAll('img').forEach((img) => {
    const src = img.getAttribute('src') || '';
    if (src.startsWith('data:')) {
      imgCount += 1;
      imgBytes += bytesOfDataUri(src);
    }
  });
  if (imgCount > 0) {
    warnings.push(`检测到 ${imgCount} 张内嵌图片，体积约 ${Math.max(1, Math.round(imgBytes / 1024))} KB`);
  }

  let mergeCells = 0;
  root.querySelectorAll('td[rowspan], td[colspan], th[rowspan], th[colspan]').forEach((cell) => {
    mergeCells += 1;
    cell.removeAttribute('rowspan');
    cell.removeAttribute('colspan');
  });
  if (mergeCells > 0) {
    warnings.push(`合并单元格已展开为普通表格（${mergeCells} 处）`);
  }

  root.querySelectorAll('img.Wiris, math').forEach((el) => {
    const alt = el.getAttribute('alt') || el.getAttribute('data-latex');
    if (alt) {
      el.replaceWith(doc.createTextNode(`$${alt}$`));
    } else {
      warnings.push('公式无法还原为 LaTeX，已丢弃');
      el.remove();
    }
  });

  const td = new TurndownService({
    headingStyle: 'atx',
    codeBlockStyle: 'fenced',
    bulletListMarker: '-',
  });
  td.use(gfm);
  td.addRule('unwrapSpan', {
    filter: (node) => node.nodeName === 'SPAN' && !(node as HTMLElement).getAttribute('class'),
    replacement: (content) => content,
  });

  let markdown = td.turndown(root.innerHTML || '');
  markdown = markdown.replace(/\n{3,}/g, '\n\n').replace(/[ \t]+$/gm, '').trim();

  if (!title) {
    const h1 = markdown.match(/^#\s+(.+)$/m);
    if (h1) title = h1[1].trim();
  }

  return { markdown, title, warnings };
}
