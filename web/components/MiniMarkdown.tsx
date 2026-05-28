// Minimal Markdown renderer for the advisor narrative — handles only the subset
// the prompt produces (##/### headings, **bold**, ordered/unordered lists, ---,
// paragraphs). Deliberately tiny: avoids pulling in a markdown dependency.

import { Fragment } from 'react';

function renderInline(text: string, keyPrefix: string) {
  // Split on **bold** markers, render odd segments as <strong>.
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <strong key={`${keyPrefix}-b-${i}`} className="font-semibold text-gray-900">
        {part}
      </strong>
    ) : (
      <Fragment key={`${keyPrefix}-t-${i}`}>{part}</Fragment>
    )
  );
}

export default function MiniMarkdown({ text }: { text: string }) {
  const lines = text.split('\n');
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flushList = () => {
    if (!list) return;
    const items = list.items.map((it, i) => (
      <li key={`li-${blocks.length}-${i}`} className="text-[13px] leading-relaxed text-gray-600">
        {renderInline(it, `li-${blocks.length}-${i}`)}
      </li>
    ));
    blocks.push(
      list.ordered ? (
        <ol key={`ol-${blocks.length}`} className="ml-5 list-decimal space-y-1">
          {items}
        </ol>
      ) : (
        <ul key={`ul-${blocks.length}`} className="ml-5 list-disc space-y-1">
          {items}
        </ul>
      )
    );
    list = null;
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      return;
    }
    if (trimmed === '---') {
      flushList();
      blocks.push(<hr key={`hr-${idx}`} className="my-3 border-gray-100" />);
      return;
    }
    if (trimmed.startsWith('### ')) {
      flushList();
      blocks.push(
        <h4 key={`h4-${idx}`} className="mt-3 text-[13px] font-semibold text-gray-800">
          {renderInline(trimmed.slice(4), `h4-${idx}`)}
        </h4>
      );
      return;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      blocks.push(
        <h3 key={`h3-${idx}`} className="mt-4 text-[14px] font-bold text-gray-900">
          {renderInline(trimmed.slice(3), `h3-${idx}`)}
        </h3>
      );
      return;
    }
    const ordered = /^\d+\.\s+/.test(trimmed);
    const unordered = /^[-*]\s+/.test(trimmed);
    if (ordered || unordered) {
      const item = trimmed.replace(/^(\d+\.|[-*])\s+/, '');
      if (!list || list.ordered !== ordered) {
        flushList();
        list = { ordered, items: [] };
      }
      list.items.push(item);
      return;
    }
    flushList();
    blocks.push(
      <p key={`p-${idx}`} className="text-[13px] leading-relaxed text-gray-600">
        {renderInline(trimmed, `p-${idx}`)}
      </p>
    );
  });
  flushList();

  return <div className="space-y-2">{blocks}</div>;
}
