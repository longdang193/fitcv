import React, { useMemo } from "react";

export function isSafeUrl(url: string): boolean {
  if (!url || typeof url !== "string") return false;
  const trimmed = url.trim();
  if (trimmed.startsWith("#") || trimmed.startsWith("/")) return true;

  try {
    const parsed = new URL(trimmed, "http://localhost");
    const proto = parsed.protocol.toLowerCase();
    return ["https:", "http:", "mailto:", "tel:"].includes(proto);
  } catch {
    return false;
  }
}

export function sanitizeUrl(url: string): string {
  if (isSafeUrl(url)) {
    return url.trim();
  }
  return "#";
}

export function renderInlineMarkdown(text: string, keyPrefix: string = "inline"): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const tokenRegex = /(`[^`]+`)|(\[[^\]]+\]\([^)]+\))|(\*{3}[^*]+\*{3})|(\*{2}[^*]+\*{2})|(__[^_]+__)|(\*[^*]+\*)|(_[^_]+_)/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let counter = 0;

  while ((match = tokenRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    const key = `${keyPrefix}-${counter++}`;

    if (token.startsWith("`") && token.endsWith("`")) {
      nodes.push(
        <code key={key} className="cv-inline-code">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("[") && token.includes("](")) {
      const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      if (linkMatch) {
        const linkText = linkMatch[1];
        const rawUrl = linkMatch[2].trim();
        const safe = isSafeUrl(rawUrl);
        if (safe) {
          nodes.push(
            <a
              key={key}
              href={sanitizeUrl(rawUrl)}
              target="_blank"
              rel="noopener noreferrer"
              className="cv-link"
            >
              {linkText}
            </a>
          );
        } else {
          nodes.push(
            <span key={key} className="cv-unsafe-link-text" title="Blocked unsafe URL scheme">
              {linkText}
            </span>
          );
        }
      } else {
        nodes.push(token);
      }
    } else if (token.startsWith("***") && token.endsWith("***")) {
      nodes.push(
        <strong key={key}>
          <em>{renderInlineMarkdown(token.slice(3, -3), `${key}-bi`)}</em>
        </strong>
      );
    } else if (
      (token.startsWith("**") && token.endsWith("**")) ||
      (token.startsWith("__") && token.endsWith("__"))
    ) {
      nodes.push(
        <strong key={key}>
          {renderInlineMarkdown(token.slice(2, -2), `${key}-b`)}
        </strong>
      );
    } else if (
      (token.startsWith("*") && token.endsWith("*")) ||
      (token.startsWith("_") && token.endsWith("_"))
    ) {
      nodes.push(
        <em key={key}>
          {renderInlineMarkdown(token.slice(1, -1), `${key}-i`)}
        </em>
      );
    } else {
      nodes.push(token);
    }

    lastIndex = tokenRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.substring(lastIndex));
  }

  return nodes;
}

export function parseSafeMarkdown(markdown: string): React.ReactNode[] {
  if (!markdown) return [];

  const lines = markdown.split(/\r?\n/);
  const elements: React.ReactNode[] = [];
  let index = 0;
  let blockKey = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index++;
      continue;
    }

    if (line.trim().startsWith("```")) {
      const lang = line.trim().slice(3).trim();
      const codeLines: string[] = [];
      index++;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index++;
      }
      if (index < lines.length && lines[index].trim().startsWith("```")) {
        index++;
      }
      elements.push(
        <pre key={`code-${blockKey++}`} className="cv-code-block" data-language={lang || undefined}>
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      continue;
    }

    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(line);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      const inline = renderInlineMarkdown(headingText, `h${level}-${blockKey}`);
      switch (level) {
        case 1:
          elements.push(<h1 key={`h-${blockKey++}`} className="cv-h1">{inline}</h1>);
          break;
        case 2:
          elements.push(<h2 key={`h-${blockKey++}`} className="cv-h2">{inline}</h2>);
          break;
        case 3:
          elements.push(<h3 key={`h-${blockKey++}`} className="cv-h3">{inline}</h3>);
          break;
        case 4:
          elements.push(<h4 key={`h-${blockKey++}`} className="cv-h4">{inline}</h4>);
          break;
        case 5:
          elements.push(<h5 key={`h-${blockKey++}`} className="cv-h5">{inline}</h5>);
          break;
        case 6:
        default:
          elements.push(<h6 key={`h-${blockKey++}`} className="cv-h6">{inline}</h6>);
          break;
      }
      index++;
      continue;
    }

    if (/^(\*{3,}|-{3,}|_{3,})$/.test(line.trim())) {
      elements.push(<hr key={`hr-${blockKey++}`} className="cv-divider" />);
      index++;
      continue;
    }

    if (line.startsWith(">")) {
      const quoteLines: string[] = [];
      while (index < lines.length && lines[index].startsWith(">")) {
        quoteLines.push(lines[index].replace(/^>\s?/, ""));
        index++;
      }
      elements.push(
        <blockquote key={`quote-${blockKey++}`} className="cv-blockquote">
          {quoteLines.map((ql, qIdx) => (
            <p key={`qp-${qIdx}`}>{renderInlineMarkdown(ql, `qp-${blockKey}-${qIdx}`)}</p>
          ))}
        </blockquote>
      );
      continue;
    }

    if (line.trim().startsWith("|") && index + 1 < lines.length && /^\|?\s*:?-+:?\s*(\|:?-+:?\s*)+\|?$/.test(lines[index + 1].trim())) {
      const headerRow = line.trim().split("|").filter((_, i, arr) => i !== 0 && i !== arr.length - 1).map((col) => col.trim());
      index += 2;
      const bodyRows: string[][] = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        const cols = lines[index].trim().split("|").filter((_, i, arr) => i !== 0 && i !== arr.length - 1).map((col) => col.trim());
        bodyRows.push(cols);
        index++;
      }
      elements.push(
        <div key={`tbl-wrap-${blockKey++}`} className="cv-table-wrapper" style={{ overflowX: "auto" }}>
          <table className="cv-table">
            <thead>
              <tr>
                {headerRow.map((col, cIdx) => (
                  <th key={`th-${cIdx}`}>{renderInlineMarkdown(col, `th-${blockKey}-${cIdx}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, rIdx) => (
                <tr key={`tr-${rIdx}`}>
                  {row.map((col, cIdx) => (
                    <td key={`td-${rIdx}-${cIdx}`}>{renderInlineMarkdown(col, `td-${blockKey}-${rIdx}-${cIdx}`)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    if (/^\s*[-*+]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*[-*+]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*[-*+]\s+/, ""));
        index++;
      }
      elements.push(
        <ul key={`ul-${blockKey++}`} className="cv-ul">
          {items.map((item, iIdx) => (
            <li key={`li-${iIdx}`}>{renderInlineMarkdown(item, `uli-${blockKey}-${iIdx}`)}</li>
          ))}
        </ul>
      );
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*\d+\.\s+/, ""));
        index++;
      }
      elements.push(
        <ol key={`ol-${blockKey++}`} className="cv-ol">
          {items.map((item, iIdx) => (
            <li key={`oli-${iIdx}`}>{renderInlineMarkdown(item, `oli-${blockKey}-${iIdx}`)}</li>
          ))}
        </ol>
      );
      continue;
    }

    const pLines: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].trim().startsWith("#") &&
      !lines[index].trim().startsWith("```") &&
      !lines[index].trim().startsWith(">") &&
      !/^\s*[-*+]\s+/.test(lines[index]) &&
      !/^\s*\d+\.\s+/.test(lines[index]) &&
      !/^(\*{3,}|-{3,}|_{3,})$/.test(lines[index].trim()) &&
      !lines[index].trim().startsWith("|")
    ) {
      pLines.push(lines[index]);
      index++;
    }

    if (pLines.length > 0) {
      elements.push(
        <p key={`p-${blockKey++}`} className="cv-p">
          {pLines.map((pl, plIdx) => (
            <React.Fragment key={`pl-${plIdx}`}>
              {plIdx > 0 && <br />}
              {renderInlineMarkdown(pl, `p-${blockKey}-${plIdx}`)}
            </React.Fragment>
          ))}
        </p>
      );
    }
  }

  return elements;
}

export interface SafeRendererProps {
  content: string;
  mediaType?: string;
  className?: string;
  rawMode?: boolean;
}

export const SafeMarkdownRenderer: React.FC<SafeRendererProps> = ({
  content,
  mediaType = "text/markdown",
  className = "",
  rawMode = false,
}) => {
  const isPlainText = mediaType.toLowerCase().startsWith("text/plain");

  const renderedContent = useMemo(() => {
    if (rawMode || isPlainText) {
      return (
        <pre
          className="cv-plain-text"
          style={{
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontSize: 13,
            lineHeight: 1.5,
            margin: 0,
          }}
        >
          {content}
        </pre>
      );
    }

    return (
      <div className="cv-markdown-rendered">
        {parseSafeMarkdown(content)}
      </div>
    );
  }, [content, mediaType, rawMode, isPlainText]);

  return (
    <div
      className={`safe-cv-renderer ${className}`.trim()}
      data-testid="safe-cv-renderer"
      data-media-type={mediaType}
      data-raw-mode={rawMode ? "true" : "false"}
    >
      {renderedContent}
    </div>
  );
};
export default SafeMarkdownRenderer;
