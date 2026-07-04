import Link from "next/link";
import { ArrowRight } from "lucide-react";

type InfoStatementProps = {
  eyebrow: string;
  headline: string;
  text: string;
  cta?: { href: string; label: string };
};

/**
 * Large right-side statement panel for info pages, mirroring the Genesis hero
 * voice. Sticky on desktop so the empty right column carries a distilled message
 * while the article is read on the left.
 */
export function InfoStatement({ eyebrow, headline, text, cta }: InfoStatementProps) {
  return (
    <aside className="info-statement">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{headline}</h2>
      <p>{text}</p>
      {cta ? (
        <Link className="primary-action" href={cta.href}>
          {cta.label}
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      ) : null}
    </aside>
  );
}
