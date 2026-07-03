import Link from "next/link";
import packageJson from "../package.json";

const appVersion = process.env.NEXT_PUBLIC_APP_VERSION ?? packageJson.version;

export function AppFooter() {
  return (
    <footer className="app-footer">
      <div className="footer-brand">
        <a href="https://studiobinary.co" rel="noreferrer" target="_blank">
          STUDIOBINARY [B01]
        </a>
        <span>studiobinary.co</span>
      </div>
      <nav aria-label="Project information">
        <Link href="/genesis">Genesis</Link>
        <Link href="/purpose">Purpose</Link>
        <Link href="/resources">Resources</Link>
        <Link href="/faq">FAQ</Link>
      </nav>
      <span className="version-tag">Evoverse v{appVersion} · planned &amp; built 2025–2026</span>
    </footer>
  );
}
