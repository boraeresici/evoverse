import { HelpCircle } from "lucide-react";

type PageHelpProps = {
  title?: string;
  points: Array<{ heading: string; body: string }>;
};

/**
 * Page-scoped, expandable help. Uses a native <details> element so it works in
 * server components with no client JS and stays collapsed until opened.
 */
export function PageHelp({ title = "How to read this page", points }: PageHelpProps) {
  return (
    <details className="page-help">
      <summary>
        <HelpCircle size={16} aria-hidden="true" />
        <span>{title}</span>
      </summary>
      <div className="page-help-body">
        {points.map((point) => (
          <div className="page-help-item" key={point.heading}>
            <strong>{point.heading}</strong>
            <p>{point.body}</p>
          </div>
        ))}
      </div>
    </details>
  );
}
