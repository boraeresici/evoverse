import Link from "next/link";
import { Github } from "lucide-react";
import packageJson from "../package.json";

const appVersion = process.env.NEXT_PUBLIC_APP_VERSION ?? packageJson.version;
const REPO_URL = "https://github.com/boraeresici/evoverse";

export function AppFooter() {
  return (
    <footer className="app-footer">
      <div className="footer-brand">
        <a href="https://studiobinary.co" rel="noreferrer" target="_blank">
          STUDIOBINARY [B01]
        </a>
        <a href="https://studiobinary.co" rel="noreferrer" target="_blank">
          studiobinary.co
        </a>
      </div>
      <nav aria-label="Project information">
        <Link href="/genesis">Genesis</Link>
        <Link href="/purpose">Purpose</Link>
        <Link href="/resources">Resources</Link>
        <Link href="/faq">FAQ</Link>
        <a
          className="footer-repo"
          href={REPO_URL}
          rel="noreferrer"
          target="_blank"
          aria-label="Evoverse on GitHub"
          title="GitHub repository"
        >
          <Github size={16} aria-hidden="true" />
          <span>GitHub</span>
        </a>
      </nav>
      <span className="version-tag">Evoverse v{appVersion} · planned &amp; built 2025–2026</span>
    </footer>
  );
}
