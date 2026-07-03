import { Info } from "lucide-react";

type InfoTipProps = {
  text: string;
  label?: string;
};

/**
 * Small accessible "(i)" info tooltip. Pure CSS reveal on hover/focus; the tip
 * text is also exposed to assistive tech through the trigger's aria-label, so it
 * needs no client JS and works inside server components.
 */
export function InfoTip({ text, label }: InfoTipProps) {
  return (
    <span className="info-tip">
      <button
        type="button"
        className="info-tip-trigger"
        aria-label={label ? `${label}. ${text}` : text}
      >
        <Info size={13} aria-hidden="true" />
      </button>
      <span className="info-tip-bubble" role="tooltip">
        {text}
      </span>
    </span>
  );
}
