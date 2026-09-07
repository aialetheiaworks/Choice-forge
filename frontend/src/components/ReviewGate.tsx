import { Button } from "./Button";

export function ReviewGate({
  promptText,
  error,
  onApprove,
  onFixFields,
}: {
  promptText: string;
  error: string | null;
  onApprove: () => void;
  onFixFields: () => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="mb-1 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">
          Your master prompt
        </div>
        <p className="mb-2 font-sans text-sm text-ink-300">
          We assembled the fields you confirmed into one objective statement. Check it reads
          right — it's what drives the reflection prompts next.
        </p>
        <div className="rounded-md border border-ink-700 bg-ink-900 p-4 font-serif text-lg leading-relaxed text-parchment">
          {promptText}
        </div>
        {error && (
          <p className="mt-2 font-sans text-xs text-rust-300">
            AI assembly was unavailable, so this is the template version. ({error})
          </p>
        )}
      </div>
      <div className="flex gap-3">
        <Button onClick={onApprove}>Looks right — continue</Button>
        <Button variant="secondary" onClick={onFixFields}>
          Not quite — fix the fields
        </Button>
      </div>
    </div>
  );
}
