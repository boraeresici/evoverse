import Link from "next/link";
import { ArrowRight, Compass, RadioTower, Sparkles } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { EventList } from "@/components/EventList";
import { MiniUniverseMap } from "@/components/MiniUniverseMap";
import { SpeciesStrip } from "@/components/SpeciesStrip";
import { StatusBand } from "@/components/StatusBand";
import { getLanding } from "@/lib/api";

export default async function HomePage() {
  const data = await getLanding();

  if (!data) {
    return <EmptyState title="Alpha is temporarily quiet" />;
  }

  return (
    <main>
      <section className="observatory-hero">
        <div className="hero-copy">
          <p className="eyebrow">Persistent Artificial Life Observatory</p>
          <h1>Evoverse</h1>
          <p className="hero-text">
            Alpha is running, mutating, collapsing, and branching into species-level history.
          </p>
          <div className="hero-actions">
            <Link className="primary-action" href="/universe">
              <Compass size={18} aria-hidden="true" />
              Enter Alpha
            </Link>
            <Link className="secondary-action" href="/chronicle">
              <RadioTower size={18} aria-hidden="true" />
              View Chronicle
            </Link>
            <Link className="secondary-action" href="/genesis">
              <Sparkles size={18} aria-hidden="true" />
              View Genesis
            </Link>
          </div>
        </div>
        <div className="hero-live">
          <StatusBand universe={data.universe} />
          <MiniUniverseMap regions={data.regions} />
        </div>
      </section>

      <section className="content-band">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Featured Chronicle</p>
            <h2>Signals From Alpha</h2>
          </div>
          <Link href="/chronicle">
            Full feed <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
        <EventList compact events={data.featuredEvents} />
      </section>

      <section className="content-band split-band">
        <div>
          <div className="section-heading compact-heading">
            <div>
              <p className="eyebrow">Species</p>
              <h2>Active Lineages</h2>
            </div>
          </div>
          <SpeciesStrip species={data.species} />
        </div>
        <div>
          <div className="section-heading compact-heading">
            <div>
              <p className="eyebrow">Recent</p>
              <h2>Latest Events</h2>
            </div>
          </div>
          <EventList compact events={data.chroniclePreview.slice(0, 4)} />
        </div>
      </section>
    </main>
  );
}
