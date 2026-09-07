import { Button } from "./Button";

export function RejectedView({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-md border border-rust-700 bg-rust-900/30 p-4">
      <p className="mb-1 font-sans text-sm text-rust-200">
        Thanks — this helps us improve future results.
      </p>
      <p className="mb-3 font-sans text-sm text-ink-300">What would you like to do?</p>
      <Button onClick={onRetry}>Rephrase and try again</Button>
      <p className="mt-3 font-sans text-xs text-ink-400">
        Tip: try naming who's responsible, a specific number, and a deadline.
      </p>
    </div>
  );
}
