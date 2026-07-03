import { LoadingState } from "@/components/LoadingState";

export default function Loading() {
  return (
    <LoadingState
      eyebrow="Universe"
      title="Mapping Alpha regions"
      message="Reading the latest region field and stability signal."
    />
  );
}
