import { useState } from "react";
import { Button } from "./Button";

const EXAMPLES = [
  "Cut support ticket backlog by 40% for enterprise accounts within the next sprint.",
  "Increase annual sales of premium office chairs by 30% within the next 12 months by targeting SMBs in India, while operating within a ₹20 lakh marketing budget.",
  "Reduce customer churn by 15% this quarter without increasing the overall ad spend.",
  "Launch a loyalty program for repeat customers by Q3 to improve retention.",
];

export function QueryScreen({
  initialValue,
  loading,
  onRun,
}: {
  initialValue: string;
  loading: boolean;
  onRun: (query: string) => void;
}) {
  const [value, setValue] = useState(initialValue);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed && !loading) onRun(trimmed);
  };

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <div className="mb-1 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">
          Objective statement
        </div>
        <h2 className="font-serif text-xl text-parchment">
          Describe the business decision you're working through.
        </h2>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          rows={4}
          placeholder="e.g. Cut support ticket backlog by 40% for enterprise accounts within the next sprint."
          className="w-full resize-none rounded-md border border-ink-600 bg-ink-900 px-4 py-3 font-serif text-base text-parchment outline-none placeholder:text-ink-400 focus:border-brass-500"
        />
        <div className="flex justify-end">
          <Button type="submit" size="lg" disabled={loading || !value.trim()}>
            {loading ? "Reading your objective…" : "Run"}
          </Button>
        </div>
      </form>

      <div className="mt-6">
        <div className="mb-2 font-mono text-xs tracking-wide text-ink-400 uppercase">Try one</div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setValue(ex)}
              className="rounded-full border border-ink-600 px-3 py-1.5 text-left font-sans text-xs text-ink-300 transition-colors duration-150 hover:border-brass-600 hover:text-brass-300"
            >
              {ex.length > 60 ? ex.slice(0, 57) + "…" : ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
