import { LoadingState } from "@/components/LoadingState";

export default function Loading() {
  return (
    <LoadingState
      eyebrow="Compare"
      title="Comparing regions"
      message="Reading region snapshots and current Alpha state."
    />
  );
}
