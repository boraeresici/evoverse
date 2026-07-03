import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { MarkdownBlock } from "@/lib/markdown";

type MarkdownArticleProps = {
  blocks: MarkdownBlock[];
  eyebrow: string;
};

export function MarkdownArticle({ blocks, eyebrow }: MarkdownArticleProps) {
  return (
    <article className="markdown-article">
      <p className="eyebrow">{eyebrow}</p>
      <MarkdownBlocks blocks={blocks} />
    </article>
  );
}

export function MarkdownBlocks({ blocks }: { blocks: MarkdownBlock[] }) {
  return <>{blocks.map((block, index) => renderBlock(block, index))}</>;
}

function renderBlock(block: MarkdownBlock, index: number) {
  if (block.type === "heading") {
    if (block.level === 1) {
      return <h1 key={index}>{block.text}</h1>;
    }
    if (block.level === 2) {
      return <h2 key={index}>{block.text}</h2>;
    }
    return <h3 key={index}>{block.text}</h3>;
  }

  if (block.type === "list") {
    return (
      <ul key={index}>
        {block.items.map((item) => (
          <li key={item}>{renderInline(item)}</li>
        ))}
      </ul>
    );
  }

  return <p key={index}>{renderInline(block.text)}</p>;
}

function renderInline(text: string) {
  const segments: Array<string | { label: string; href: string }> = [];
  const linkPattern = /\[([^\]]+)\]\(([^)]+)\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = linkPattern.exec(text))) {
    if (match.index > lastIndex) {
      segments.push(text.slice(lastIndex, match.index));
    }
    segments.push({ label: match[1], href: match[2] });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push(text.slice(lastIndex));
  }

  return segments.map((segment, index) => {
    if (typeof segment === "string") {
      return segment;
    }

    const external = segment.href.startsWith("http");
    if (external) {
      return (
        <a href={segment.href} key={`${segment.href}-${index}`} rel="noreferrer" target="_blank">
          {segment.label}
          <ArrowUpRight size={14} aria-hidden="true" />
        </a>
      );
    }

    return (
      <Link href={segment.href} key={`${segment.href}-${index}`}>
        {segment.label}
      </Link>
    );
  });
}
