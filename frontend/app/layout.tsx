import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import {
  Activity,
  Bell,
  Columns3,
  GitBranch,
  KeyRound,
  Orbit,
  RadioTower,
  Sparkles,
  SlidersHorizontal
} from "lucide-react";
import { AppFooter } from "@/components/AppFooter";
import { UsageModal } from "@/components/UsageModal";
import { Analytics } from "@/components/Analytics";
import "./globals.css";

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://evoverse.studiobinary.co";

const description =
  "Evoverse is a persistent artificial life observatory. Watch Alpha — a seeded universe where regions, species, and populations evolve through a deterministic tick engine — and travel its history.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Evoverse — Persistent Artificial Life Observatory",
    template: "%s"
  },
  description,
  applicationName: "Evoverse",
  authors: [{ name: "Bora ERESICI", url: "https://studiobinary.co" }],
  creator: "Bora ERESICI",
  keywords: [
    "artificial life",
    "ALife",
    "cellular automata",
    "Conway's Game of Life",
    "emergence",
    "evolution simulation",
    "Evoverse",
    "Alpha universe"
  ],
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    url: siteUrl,
    siteName: "Evoverse",
    title: "Evoverse — Persistent Artificial Life Observatory",
    description,
    locale: "en_US"
  },
  twitter: {
    card: "summary_large_image",
    title: "Evoverse — Persistent Artificial Life Observatory",
    description
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <header className="app-header">
          <Link className="brand-mark" href="/" aria-label="Evoverse Alpha">
            <Orbit size={22} aria-hidden="true" />
            <span>Evoverse</span>
          </Link>
          <nav className="main-nav" aria-label="Primary">
            <Link href="/chronicle">
              <RadioTower size={17} aria-hidden="true" />
              <span>Chronicle</span>
            </Link>
            <Link href="/universe">
              <Orbit size={17} aria-hidden="true" />
              <span>Universe</span>
            </Link>
            <Link href="/genesis">
              <Sparkles size={17} aria-hidden="true" />
              <span>Genesis</span>
            </Link>
            <Link href="/reports">
              <Activity size={17} aria-hidden="true" />
              <span>Reports</span>
            </Link>
            <Link href="/compare">
              <Columns3 size={17} aria-hidden="true" />
              <span>Compare</span>
            </Link>
            <Link href="/species/sp-0001">
              <GitBranch size={17} aria-hidden="true" />
              <span>Species</span>
            </Link>
            <Link href="/notifications" aria-label="Notifications">
              <Bell size={17} aria-hidden="true" />
            </Link>
            {/* Auth-state-dependent routes: never prefetch, so a logged-out
                prefetch can't cache a session-less view that survives sign-in. */}
            <Link href="/auth" prefetch={false}>
              <KeyRound size={17} aria-hidden="true" />
              <span>Auth</span>
            </Link>
            <Link href="/admin/config" prefetch={false}>
              <SlidersHorizontal size={17} aria-hidden="true" />
              <span>Admin</span>
            </Link>
            <UsageModal />
          </nav>
        </header>
        {children}
        <AppFooter />
        <Suspense fallback={null}>
          <Analytics />
        </Suspense>
      </body>
    </html>
  );
}
