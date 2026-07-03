"use client";

import { useState } from "react";
import { Bell, BellOff, Loader2 } from "lucide-react";

type ObserverFollowControlProps = {
  entityId: string;
  entityType: "region" | "species";
  initialFollowing: boolean;
};

export function ObserverFollowControl({
  entityId,
  entityType,
  initialFollowing
}: ObserverFollowControlProps) {
  const [following, setFollowing] = useState(initialFollowing);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function toggleFollow() {
    setPending(true);
    setMessage(null);
    try {
      const response = await fetch("/api/observer/follow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entityId, entityType, follow: !following })
      });
      if (!response.ok) {
        throw new Error("Observer follow request failed");
      }
      setFollowing(!following);
      setMessage(following ? "Unfollowed" : "Following");
    } catch {
      setMessage("Observer link unavailable");
    } finally {
      setPending(false);
    }
  }

  const Icon = pending ? Loader2 : following ? BellOff : Bell;

  return (
    <div className="observer-follow-control">
      <button
        aria-pressed={following}
        className={following ? "observer-follow-button active" : "observer-follow-button"}
        disabled={pending}
        onClick={toggleFollow}
        type="button"
      >
        <Icon size={17} aria-hidden="true" />
        {pending ? "Saving" : following ? "Following" : "Follow"}
      </button>
      {message ? <span>{message}</span> : null}
    </div>
  );
}
