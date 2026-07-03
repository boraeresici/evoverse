import { LoadingState } from "@/components/LoadingState";

export default function Loading() {
  return (
    <LoadingState
      eyebrow="Dynamic Report"
      title="Comparing Alpha snapshots"
      message="Reading historical and current state into chart-ready series."
    />
  );
}
