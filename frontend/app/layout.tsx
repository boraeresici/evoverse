import type { Metadata } from "next";
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
import "./globals.css";

export const metadata: Metadata = {
  title: "Evoverse",
  description: "Persistent Artificial Life Observatory"
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
            <Link href="/auth">
              <KeyRound size={17} aria-hidden="true" />
              <span>Auth</span>
            </Link>
            <Link href="/admin/config">
              <SlidersHorizontal size={17} aria-hidden="true" />
              <span>Admin</span>
            </Link>
            <UsageModal />
          </nav>
        </header>
        {children}
        <AppFooter />
      </body>
    </html>
  );
}
