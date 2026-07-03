"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";
import {
  Bell,
  Compass,
  HelpCircle,
  RadioTower,
  SlidersHorizontal,
  X
} from "lucide-react";

const STORAGE_KEY = "evoverse-basic-guide-seen";

const guideItems = [
  {
    title: "Enter Alpha",
    text: "Open the universe map, inspect regions, then follow the species or regions you care about.",
    icon: Compass
  },
  {
    title: "Read the Chronicle",
    text: "Chronicle streams the latest mutations, collapses, resources, and species signals as Alpha runs.",
    icon: RadioTower
  },
  {
    title: "Track Signals",
    text: "Notifications collect followed region and species activity for the local observer profile.",
    icon: Bell
  },
  {
    title: "Use Admin Carefully",
    text: "Config is read-only until validation, audit log, rollback, and worker/API separation are complete.",
    icon: SlidersHorizontal
  }
];

export function UsageModal() {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    setMounted(true);
  }, []);

  const closeModal = useCallback(() => {
    setOpen(false);
    window.localStorage.setItem(STORAGE_KEY, "true");
  }, []);

  useEffect(() => {
    if (!window.localStorage.getItem(STORAGE_KEY)) {
      setOpen(true);
    }
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeModal();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closeModal, open]);

  return (
    <>
      <button
        aria-label="Open basic guide"
        className="usage-help-button"
        onClick={() => setOpen(true)}
        title="Basic guide"
        type="button"
      >
        <HelpCircle size={17} aria-hidden="true" />
        <span>Guide</span>
      </button>

      {open && mounted
        ? createPortal(
        <div
          className="usage-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeModal();
            }
          }}
        >
          <section
            aria-describedby={descriptionId}
            aria-labelledby={titleId}
            aria-modal="true"
            className="usage-modal"
            role="dialog"
          >
            <header className="usage-modal-header">
              <div>
                <p className="eyebrow">Basic Guide</p>
                <h2 id={titleId}>Start with the live map, then follow the signals.</h2>
              </div>
              <button
                aria-label="Close basic guide"
                className="usage-close"
                onClick={closeModal}
                type="button"
              >
                <X size={18} aria-hidden="true" />
              </button>
            </header>
            <p className="usage-modal-copy" id={descriptionId}>
              Evoverse Alpha is a persistent artificial life observatory. These are the core
              surfaces for the current build.
            </p>
            <div className="usage-guide-grid">
              {guideItems.map((item) => {
                const Icon = item.icon;
                return (
                  <article className="usage-guide-item" key={item.title}>
                    <Icon size={18} aria-hidden="true" />
                    <div>
                      <h3>{item.title}</h3>
                      <p>{item.text}</p>
                    </div>
                  </article>
                );
              })}
            </div>
            <button className="primary-action usage-confirm" onClick={closeModal} type="button">
              Got it
            </button>
          </section>
        </div>,
            document.body
          )
        : null}
    </>
  );
}
