import { useState } from "react";
import { ROLES, ROLE_LABELS, type RawField } from "../types";
import { ConfidenceGauge } from "./ConfidenceGauge";

function displayValue(v: RawField["value"]): string {
  if (v === null) return "—";
  if (Array.isArray(v)) return v.join(", ");
  return v;
}

export function ExtractionDetails({ fields }: { fields: Record<string, RawField> }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-6 rounded-md border border-ink-700">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 font-sans text-sm text-ink-300 transition-colors hover:text-parchment"
      >
        <span>See extraction details</span>
        <span
          className="transition-transform duration-150 ease-[var(--ease-out-strong)]"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          ▾
        </span>
      </button>
      {open && (
        <div className="grid grid-cols-1 gap-2 border-t border-ink-700 p-4 sm:grid-cols-2">
          {ROLES.map((role) => {
            const f = fields[role];
            return (
              <div key={role} className="rounded-md border border-ink-700 bg-ink-900 p-3">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-mono text-[11px] tracking-wide text-ink-400 uppercase">
                    {ROLE_LABELS[role]}
                  </span>
                  <ConfidenceGauge confidence={f.confidence} />
                </div>
                <div className="font-serif text-sm text-parchment">{displayValue(f.value)}</div>
                {f.source_text && (
                  <div className="mt-1 font-mono text-[11px] text-ink-400">
                    from: "{f.source_text}"
                  </div>
                )}
                {f.multi_span && (
                  <div className="mt-1 font-sans text-[11px] text-brass-400">multiple candidates found</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
