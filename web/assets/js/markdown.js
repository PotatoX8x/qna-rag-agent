const INLINE_RE = /`([^`]+)`|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_]+)_|\[([^\]]+)\]\(([^)]+)\)/;

function renderInline(text, container) {
  let rest = text;
  while (rest.length) {
    const m = INLINE_RE.exec(rest);
    if (!m) {
      container.appendChild(document.createTextNode(rest));
      break;
    }
    if (m.index > 0) container.appendChild(document.createTextNode(rest.slice(0, m.index)));

    if (m[1] !== undefined) {
      const code = document.createElement('code');
      code.textContent = m[1];
      container.appendChild(code);
    } else if (m[2] !== undefined || m[3] !== undefined) {
      const strong = document.createElement('strong');
      strong.textContent = m[2] ?? m[3];
      container.appendChild(strong);
    } else if (m[4] !== undefined || m[5] !== undefined) {
      const em = document.createElement('em');
      em.textContent = m[4] ?? m[5];
      container.appendChild(em);
    } else if (m[6] !== undefined) {
      const a = document.createElement('a');
      a.href = m[7];
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = m[6];
      container.appendChild(a);
    }

    rest = rest.slice(m.index + m[0].length);
  }
}

const UL_RE = /^[-*+]\s+/;
const OL_RE = /^\d+\.\s+/;
const HEADER_RE = /^(#{1,6})\s+(.*)$/;
const QUOTE_RE = /^>\s?/;

export function renderMarkdown(text) {
  const root = document.createDocumentFragment();
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === '') {
      i++;
      continue;
    }

    if (line.trim().startsWith('```')) {
      const lang = line.trim().slice(3).trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      const pre = document.createElement('pre');
      const code = document.createElement('code');
      if (lang) code.className = `lang-${lang}`;
      code.textContent = codeLines.join('\n');
      pre.appendChild(code);
      root.appendChild(pre);
      continue;
    }

    const headerMatch = HEADER_RE.exec(line);
    if (headerMatch) {
      const level = Math.min(headerMatch[1].length + 3, 6);
      const h = document.createElement(`h${level}`);
      renderInline(headerMatch[2], h);
      root.appendChild(h);
      i++;
      continue;
    }

    if (QUOTE_RE.test(line)) {
      const quoteLines = [];
      while (i < lines.length && QUOTE_RE.test(lines[i])) {
        quoteLines.push(lines[i].replace(QUOTE_RE, ''));
        i++;
      }
      const bq = document.createElement('blockquote');
      const p = document.createElement('p');
      renderInline(quoteLines.join(' '), p);
      bq.appendChild(p);
      root.appendChild(bq);
      continue;
    }

    if (UL_RE.test(line)) {
      const ul = document.createElement('ul');
      while (i < lines.length && UL_RE.test(lines[i])) {
        const li = document.createElement('li');
        renderInline(lines[i].replace(UL_RE, ''), li);
        ul.appendChild(li);
        i++;
      }
      root.appendChild(ul);
      continue;
    }

    if (OL_RE.test(line)) {
      const ol = document.createElement('ol');
      while (i < lines.length && OL_RE.test(lines[i])) {
        const li = document.createElement('li');
        renderInline(lines[i].replace(OL_RE, ''), li);
        ol.appendChild(li);
        i++;
      }
      root.appendChild(ol);
      continue;
    }

    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].trim().startsWith('```') &&
      !HEADER_RE.test(lines[i]) &&
      !UL_RE.test(lines[i]) &&
      !OL_RE.test(lines[i]) &&
      !QUOTE_RE.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    const p = document.createElement('p');
    renderInline(paraLines.join(' '), p);
    root.appendChild(p);
  }

  return root;
}
