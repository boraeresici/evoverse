import type { Metadata } from "next";
import { HelpCircle } from "lucide-react";
import { MarkdownBlocks } from "@/components/MarkdownArticle";
import { getFaqCategories } from "@/lib/markdown";

export const metadata: Metadata = {
  title: "FAQ | Evoverse",
  description: "Scientific and usage questions about Alpha, answered."
};

export default async function FaqPage() {
  const categories = await getFaqCategories("faq.md");

  return (
    <main className="page-shell info-page faq-page">
      <section className="page-title">
        <p className="eyebrow">Help</p>
        <h1>Frequently asked questions</h1>
        <p className="faq-lede">
          Scientific and usage questions about Alpha. Entries are managed in Markdown
          (<code>frontend/content/faq.md</code>) and can be extended any time.
        </p>
      </section>

      {categories.map((category) => (
        <section className="faq-category" key={category.category}>
          <h2>{category.category}</h2>
          <div className="faq-list">
            {category.questions.map((entry) => (
              <details className="faq-item" id={entry.id} key={entry.id}>
                <summary>
                  <HelpCircle size={16} aria-hidden="true" />
                  <span>{entry.question}</span>
                </summary>
                <div className="faq-answer">
                  <MarkdownBlocks blocks={entry.answer} />
                </div>
              </details>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
