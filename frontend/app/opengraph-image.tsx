import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const alt = "Evoverse — Persistent Artificial Life Observatory";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Dynamically generated social-share card, so no binary asset needs to live in
// the repo. Uses system fonts only to stay self-contained.
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "80px",
          background: "linear-gradient(135deg, #14110c 0%, #241d12 60%, #3a2c14 100%)",
          color: "#f4f1ea",
          fontFamily: "sans-serif"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              border: "3px solid #e9b949",
              display: "flex"
            }}
          />
          <div style={{ fontSize: 34, letterSpacing: 2, color: "#e9b949" }}>EVOVERSE</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 76, fontWeight: 700, lineHeight: 1.05, maxWidth: 980 }}>
            Persistent Artificial Life Observatory
          </div>
          <div style={{ fontSize: 32, color: "#c9c1b0", maxWidth: 900 }}>
            Watch Alpha evolve through a deterministic tick engine — and travel its history.
          </div>
        </div>
        <div style={{ fontSize: 26, color: "#8f8677" }}>evoverse.studiobinary.co</div>
      </div>
    ),
    { ...size }
  );
}
