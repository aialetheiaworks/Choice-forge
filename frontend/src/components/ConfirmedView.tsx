import type { BucketMatch } from "../types";
import { bucketColorVar } from "../lib/highlight";
import { HighlightedPrompt } from "./HighlightedPrompt";
import { Button } from "./Button";

export function ConfirmedView({
  promptText,
  promptError,
  ranked,
  tooltipsLoading,
  tooltipsError,
  onRetryTooltips,
}: {
  promptText: string;
  promptError: string | null;
  ranked: BucketMatch[];
  tooltipsLoading: boolean;
  tooltipsError: string | null;
  onRetryTooltips: () => void;
}) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="mb-2 inline-block rounded-full border border-verdigris-600 bg-verdigris-900/40 px-3 py-1 font-sans text-xs text-verdigris-200">
          Master prompt confirmed
        </div>
        <div className="rounded-md border border-ink-700 bg-ink-900 p-4">
          <HighlightedPrompt text={promptText} ranked={ranked} />
        </div>
        {promptError && (
          <p className="mt-2 font-sans text-xs text-rust-300">
            AI assembly was unavailable, so this is the template version. ({promptError})
          </p>
        )}
      </div>

      <div>
        <div className="mb-1 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">
          Before you go further — think about
        </div>
        <p className="mb-3 font-sans text-sm text-ink-300">
          Prompts drawn from an 80-topic business-thinking taxonomy, matched to your objective.
          Hover a highlighted word above to see why it matched.
        </p>

        {tooltipsLoading && (
          <p className="font-sans text-sm text-ink-400">
            Finding what else to think about… (first call can take up to a minute if the service
            was idle)
          </p>
        )}

        {!tooltipsLoading && tooltipsError && (
          <div className="flex items-center gap-3">
            <p className="font-sans text-sm text-rust-300">
              Reflection prompts aren't available right now. ({tooltipsError})
            </p>
            <Button variant="secondary" size="md" onClick={onRetryTooltips}>
              Try again
            </Button>
          </div>
        )}

        {!tooltipsLoading && !tooltipsError && ranked.length === 0 && (
          <p className="font-sans text-sm text-ink-400">No specific prompts surfaced for this objective.</p>
        )}

        {!tooltipsLoading && !tooltipsError && ranked.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {ranked.map((b, i) => (
              <span
                key={b.name + i}
                className="flex items-center gap-1.5 rounded-full border px-3 py-1 font-sans text-xs"
                style={{ borderColor: bucketColorVar(i), color: bucketColorVar(i) }}
              >
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: bucketColorVar(i) }}
                />
                {b.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
