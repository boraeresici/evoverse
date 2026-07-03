import { LoadingState } from "@/components/LoadingState";

export default function Loading() {
  return (
    <LoadingState
      eyebrow="Species"
      title="Reading lineage detail"
      message="Collecting traits, forecast, regions, and species timeline."
    />
  );
}
