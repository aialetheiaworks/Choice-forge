import { ROLES, type DisplayField, type FieldValueInput, type LogFieldEntry, type RawField, type Role } from "../types";

/** Mirrors app.py's "✅ Yes, this is right" path: accept every field exactly
 * as the pipeline produced it, no edits. */
export function resolveAsIs(
  displayFields: Record<Role, DisplayField>,
  rawFields: Record<Role, RawField>,
): [Record<Role, FieldValueInput>, Record<Role, LogFieldEntry>] {
  const finalFields = {} as Record<Role, FieldValueInput>;
  const logFields = {} as Record<Role, LogFieldEntry>;
  for (const role of ROLES) {
    const orig = displayFields[role];
    finalFields[role] = { text: orig.text, blank: orig.blank, not_applicable: false };
    logFields[role] = {
      original_value: rawFields[role].value,
      original_status: rawFields[role].status,
      original_confidence: rawFields[role].confidence,
      blank: orig.blank,
      not_applicable: false,
      needs_review: orig.needs_review,
      multi_span: orig.multi_span,
      final_value: orig.blank ? null : orig.text,
      user_edited: false,
      ai_suggested: false,
      ai_suggestion_shown: null,
    };
  }
  return [finalFields, logFields];
}
