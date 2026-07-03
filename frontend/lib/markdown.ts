import { readFile } from "node:fs/promises";
import { join } from "node:path";

export type MarkdownBlock =
  | {
      type: "heading";
      level: 1 | 2 | 3;
      text: string;
    }
  | {
      type: "paragraph";
      text: string;
    }
  | {
      type: "list";
      items: string[];
    };

export async function getMarkdownPage(fileName: string): Promise<MarkdownBlock[]> {
  const markdown = await readFile(join(process.cwd(), "content", fileName), "utf8");
  return parseMarkdown(markdown);
}

export type FaqEntry = {
  id: string;
  question: string;
  answer: MarkdownBlock[];
};

export type FaqCategory = {
  category: string;
  questions: FaqEntry[];
};

/**
 * Read a FAQ markdown file and group it into an accordion structure: level-1
 * headings are categories, level-2 headings are questions, and everything until
 * the next heading is that question's answer. Add entries by editing the md file.
 */
export async function getFaqCategories(fileName = "faq.md"): Promise<FaqCategory[]> {
  const blocks = await getMarkdownPage(fileName);
  const categories: FaqCategory[] = [];
  let current: FaqCategory | null = null;
  let entry: FaqEntry | null = null;

  for (const block of blocks) {
    if (block.type === "heading" && block.level === 1) {
      current = { category: block.text, questions: [] };
      categories.push(current);
      entry = null;
    } else if (block.type === "heading" && block.level === 2) {
      if (!current) {
        current = { category: "General", questions: [] };
        categories.push(current);
      }
      entry = { id: faqSlug(block.text), question: block.text, answer: [] };
      current.questions.push(entry);
    } else if (entry) {
      entry.answer.push(block);
    }
  }

  return categories.filter((category) => category.questions.length > 0);
}

function faqSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

function parseMarkdown(markdown: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  let paragraph: string[] = [];
  let list: string[] = [];

  function flushParagraph() {
    if (!paragraph.length) {
      return;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    paragraph = [];
  }

  function flushList() {
    if (!list.length) {
      return;
    }
    blocks.push({ type: "list", items: list });
    list = [];
  }

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({
        type: "heading",
        level: heading[1].length as 1 | 2 | 3,
        text: heading[2]
      });
      continue;
    }

    if (trimmed.startsWith("- ")) {
      flushParagraph();
      list.push(trimmed.slice(2));
      continue;
    }

    flushList();
    paragraph.push(trimmed);
  }

  flushParagraph();
  flushList();
  return blocks;
}
