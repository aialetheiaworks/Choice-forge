import { useState } from "react";
import {
  NOT_APPLICABLE_ELIGIBLE_ROLES,
  ROLES,
  ROLE_LABELS,
  type CompoundQueryInfo,
  type DisplayField,
  type FieldValueInput,
  type LogFieldEntry,
  type RawField,
  type Role,
} from "../types";
import { Button } from "./Button";

export function EditForm({
  displayFields,
  rawFields,
  compound,
  hasBlanks,
  onContinue,
  onReject,
}: {
  displayFields: Record<Role, DisplayField>;
  rawFields: Record<Role, RawField>;
  compound: CompoundQueryInfo;
  hasBlanks: boolean;
  onContinue: (
    finalFields: Record<Role, FieldValueInput>,
    logFields: Record<Role, LogFieldEntry>,
  ) => void;
  onReject: (
    reason: string | null,
    finalFields: Record<Role, FieldValueInput>,
    logFields: Record<Role, LogFieldEntry>,
  ) => void;
}) {
  const [inputs, setInputs] = useState<Record<Role, string>>(() =>
    Object.fromEntries(ROLES.map((r) => [r, displayFields[r].blank ? "" : displayFields[r].text])) as Record<
      Role,
      string
    >,
  );
  const [notApplicable, setNotApplicable] = useState<Partial<Record<Role, boolean>>>({});
  const [isCompound, setIsCompound] = useState(false);
  const [reason, setReason] = useState("");

  const resolve = (): [Record<Role, FieldValueInput>, Record<Role, LogFieldEntry>] => {
    const finalFields = {} as Record<Role, FieldValueInput>;
    const logFields = {} as Record<Role, LogFieldEntry>;
    for (const role of ROLES) {
      const orig = displayFields[role];
      const eligible = NOT_APPLICABLE_ELIGIBLE_ROLES.has(role);
      const na = eligible && !!notApplicable[role];
      const submitted = inputs[role].trim();
      // cleared a field that had a (possibly low-confidence) prediction in
      // it -> the user is rejecting that guess; treat the field as blank.
      const cleared = !na && !orig.blank && submitted === "";
      const userEdited =
        !na && ((!!submitted && (orig.blank || submitted !== orig.text)) || cleared);

      let resolvedText: string;
      let resolvedBlank: boolean;
      if (na) {
        resolvedText = "";
        resolvedBlank = true;
      } else if (cleared) {
        resolvedText = "";
        resolvedBlank = true;
      } else {
        resolvedText = userEdited ? submitted : orig.text;
        resolvedBlank = userEdited ? false : orig.blank;
      }

      finalFields[role] = { text: resolvedText, blank: resolvedBlank, not_applicable: na };
      logFields[role] = {
        original_value: rawFields[role].value,
        original_status: rawFields[role].status,
        original_confidence: rawFields[role].confidence,
        blank: resolvedBlank,
        not_applicable: na,
        needs_review: orig.needs_review,
        multi_span: orig.multi_span,
        final_value: resolvedBlank ? null : resolvedText,
        user_edited: userEdited,
        ai_suggested: false,
        ai_suggestion_shown: null,
      };
    }
    return [finalFields, logFields];
  };

  const submit = (e: React.FormEvent, action: "continue" | "reject") => {
    e.preventDefault();
    const [finalFields, logFields] = resolve();
    if (action === "continue") onContinue(finalFields, logFields);
    else onReject(reason.trim() || null, finalFields, logFields);
  };

  return (
    <form className="flex flex-col gap-4">
      <p className="font-sans text-sm text-ink-300">
        {hasBlanks
          ? "Fill in what's missing below, then continue."
          : "Update anything that's wrong below, then continue."}
      </p>

      {compound.is_possible_compound && (
        <label className="flex items-start gap-2 rounded-md border border-brass-700 bg-brass-900/30 p-3 text-sm text-brass-200">
          <input
            type="checkbox"
            checked={isCompound}
            onChange={(e) => setIsCompound(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            This query actually describes more than one separate decision bundled together.
            <span className="mt-1 block font-sans text-xs text-brass-300/80">{compound.message}</span>
          </span>
        </label>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {ROLES.map((role) => {
          const f = displayFields[role];
          const eligible = NOT_APPLICABLE_ELIGIBLE_ROLES.has(role);
          const disabled = !!notApplicable[role];
          return (
            <div key={role} className="flex flex-col gap-1.5">
              <label className="flex items-center gap-1.5 font-mono text-[11px] tracking-wide text-ink-400 uppercase">
                {ROLE_LABELS[role]}
                {f.needs_review && <span className="text-rust-400">⚠</span>}
              </label>
              <input
                value={inputs[role]}
                disabled={disabled}
                onChange={(e) => setInputs((s) => ({ ...s, [role]: e.target.value }))}
                placeholder={f.blank ? f.text : undefined}
                className="rounded-md border border-ink-600 bg-ink-900 px-3 py-2 font-serif text-sm text-parchment outline-none placeholder:text-ink-500 focus:border-brass-500 disabled:opacity-40"
              />
              {f.low_confidence && !disabled && (
                <span className="font-sans text-[11px] text-rust-400">
                  low confidence ({f.confidence.toFixed(2)}) — check or correct this guess
                </span>
              )}
              {eligible && (f.blank || f.low_confidence) && (
                <label className="flex items-center gap-1.5 font-sans text-xs text-ink-400">
                  <input
                    type="checkbox"
                    checked={!!notApplicable[role]}
                    onChange={(e) =>
                      setNotApplicable((s) => ({ ...s, [role]: e.target.checked }))
                    }
                  />
                  Not applicable — never stated
                </label>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="font-mono text-[11px] tracking-wide text-ink-400 uppercase">
          If starting over, what went wrong? (optional)
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
          className="resize-none rounded-md border border-ink-600 bg-ink-900 px-3 py-2 font-sans text-sm text-parchment outline-none focus:border-brass-500"
        />
      </div>

      <div className="flex flex-wrap justify-end gap-3">
        <Button type="button" variant="secondary" onClick={(e) => submit(e, "reject")}>
          This is way off — start over
        </Button>
        <Button type="button" variant="primary" onClick={(e) => submit(e, "continue")}>
          Continue with my corrections
        </Button>
      </div>
    </form>
  );
}
