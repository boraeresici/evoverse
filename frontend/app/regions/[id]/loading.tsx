import { LoadingState } from "@/components/LoadingState";

export default function Loading() {
  return (
    <LoadingState
      eyebrow="Region"
      title="Reading region detail"
      message="Collecting population, catalyst, and timeline signals."
    />
  );
}
