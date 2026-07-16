import type { MetadataRoute } from "next";

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://evoverse.studiobinary.co";

// Public, indexable surfaces only. Admin, auth, notifications, and per-entity
// species/region routes are intentionally excluded (see robots.ts).
const routes: Array<{ path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"] }> = [
  { path: "", priority: 1, changeFrequency: "daily" },
  { path: "/universe", priority: 0.9, changeFrequency: "daily" },
  { path: "/chronicle", priority: 0.8, changeFrequency: "daily" },
  { path: "/genesis", priority: 0.7, changeFrequency: "monthly" },
  { path: "/purpose", priority: 0.7, changeFrequency: "monthly" },
  { path: "/science", priority: 0.7, changeFrequency: "daily" },
  { path: "/resources", priority: 0.6, changeFrequency: "monthly" },
  { path: "/faq", priority: 0.6, changeFrequency: "monthly" },
  { path: "/reports", priority: 0.6, changeFrequency: "weekly" },
  { path: "/compare", priority: 0.5, changeFrequency: "weekly" }
];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map(({ path, priority, changeFrequency }) => ({
    url: `${siteUrl}${path}`,
    changeFrequency,
    priority
  }));
}
