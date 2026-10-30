import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

/** Các kiểu chữ dùng để hiển thị công thức toán (KaTeX). */
export type MathFontId = 'katex' | 'serif' | 'sans';

export const MATH_FONTS: { id: MathFontId; label: string; hint: string }[] = [
  { id: 'katex', label: 'Mặc định (KaTeX)', hint: 'Chuẩn sách giáo khoa' },
  { id: 'serif', label: 'Serif học thuật', hint: 'Cambria / STIX / Times' },
  { id: 'sans', label: 'Hiện đại (Sans)', hint: 'Be Vietnam Pro / Segoe UI' },
];

const FONT_STORAGE_KEY = 'mindora_math_font';

export function getMathFont(): MathFontId {
  try {
    const saved = localStorage.getItem(FONT_STORAGE_KEY);
    if (saved === 'serif' || saved === 'sans' || saved === 'katex') return saved;
  } catch {
    /* bỏ qua khi trình duyệt chặn storage */
  }
  return 'katex';
}

export function setMathFont(font: MathFontId) {
  try {
    localStorage.setItem(FONT_STORAGE_KEY, font);
  } catch {
    /* bỏ qua khi trình duyệt chặn storage */
  }
}

/**
 * Tự đóng các delimiter toán còn dở khi AI đang streaming (VD: mới nhận
 * được `$$` mở mà chưa có `$$` đóng). Tránh KaTeX/remark-math parse vỡ
 * khiến cả đoạn chat hiển thị sai trong lúc chờ token tiếp theo.
 */
function balanceMathDelimiters(text: string): string {
  // Tách code block ```...``` ra để không đếm nhầm `$` trong code.
  const parts = text.split(/(```[\s\S]*?(?:```|$))/g);
  for (let i = 0; i < parts.length; i += 2) {
    let chunk = parts[i];
    const displayPairs = chunk.match(/\$\$/g) ?? [];
    if (displayPairs.length % 2 === 1) chunk += '$$';
    const openBracket = (chunk.match(/\\\[/g) ?? []).length;
    const closeBracket = (chunk.match(/\\\]/g) ?? []).length;
    if (openBracket > closeBracket) chunk += '\\]'.repeat(openBracket - closeBracket);
    const openParen = (chunk.match(/\\\(/g) ?? []).length;
    const closeParen = (chunk.match(/\\\)/g) ?? []).length;
    if (openParen > closeParen) chunk += '\\)'.repeat(openParen - closeParen);
    parts[i] = chunk;
  }
  return parts.join('');
}

function normalizeMathDelimiters(text: string): string {
  const parts = text.split(/(```[\s\S]*?(?:```|$))/g);
  for (let i = 0; i < parts.length; i += 2) {
    parts[i] = parts[i]
      .replace(/\\\[/g, () => '$$')
      .replace(/\\\]/g, () => '$$')
      .replace(/\\\(/g, '$')
      .replace(/\\\)/g, '$')
      .replace(
        /\[\s*((?:[A-Za-z]\s*=\s*)?\\begin\{(?:p|b|B|v|V)?matrix\}[\s\S]*?\\end\{(?:p|b|B|v|V)?matrix\})\s*\]/g,
        (_match, formula: string) => `$$${formula}$$`,
      )
      .replace(
        /(\\begin\{(?:p|b|B|v|V)?matrix\})([\s\S]*?)(\\end\{(?:p|b|B|v|V)?matrix\})/g,
        (_match, start: string, rows: string, end: string) =>
          `${start}${rows.replace(/(?<!\\)\\\s+(?=[^\\])/g, '\\\\ ')}${end}`,
      );
  }
  return parts.join('');
}

export function MathMarkdown({ content, font }: { content: string; font: MathFontId }) {
  const safeContent = useMemo(
    () => normalizeMathDelimiters(balanceMathDelimiters(content)),
    [content],
  );
  return (
    <div className={`math-body math-font-${font}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
      >
        {safeContent}
      </ReactMarkdown>
    </div>
  );
}
