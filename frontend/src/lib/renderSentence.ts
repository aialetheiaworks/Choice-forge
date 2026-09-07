import type { FieldValueInput } from "../types";

/** Faithful TS port of prompt_synthesis.py's render_sentence(), used only to
 * log a "rejected" resolution client-side without spending an LLM call
 * (api.py's /assemble always invokes the LLM — matches the project's
 * one-call-per-confirm discipline, see TOOLTIP_INTEGRATION_PLAN.md Phase C). */

const MAGNITUDE_SELF_PREPOSITIONS = new Set(["by", "to", "into", "from", "up", "down"]);
const TIME_SELF_PREPOSITIONS = new Set([
  "by",
  "within",
  "before",
  "during",
  "in",
  "on",
  "at",
  "through",
  "until",
]);

function capitalize(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}

function clauseText(f: FieldValueInput): string {
  return (f.text || "").trim();
}

function omitClause(f: FieldValueInput): boolean {
  return f.not_applicable || !clauseText(f);
}

function prefixedClause(prefix: string, f: FieldValueInput, selfPrepositions: Set<string>): string {
  const text = f.text;
  if (!f.blank) {
    const firstWord = text.trim().split(/\s+/)[0]?.toLowerCase() ?? "";
    if (selfPrepositions.has(firstWord)) return text;
  }
  return `${prefix} ${text}`;
}

function targetPhrase(fields: Record<string, FieldValueInput>): string {
  const measure = fields.measure;
  const obj = fields.object;
  if (!measure.blank && !obj.blank && measure.text !== obj.text) {
    return `${measure.text} of ${obj.text}`;
  }
  if (!measure.blank) return measure.text;
  if (!obj.blank) return obj.text;
  return measure.text;
}

export function renderSentence(fields: Record<string, FieldValueInput>): string {
  const subject = capitalize(clauseText(fields.actor));
  const intentText = clauseText(fields.intent);
  const target = targetPhrase(fields).trim();

  let core: string;
  if (target && intentText.toLowerCase().includes(target.toLowerCase())) {
    core = `${subject} wants to ${intentText}`;
  } else if (target) {
    core = `${subject} wants to ${intentText} ${target}`;
  } else {
    core = `${subject} wants to ${intentText}`;
  }

  const leadClauses: string[] = [];
  if (!omitClause(fields.magnitude)) {
    leadClauses.push(prefixedClause("by", fields.magnitude, MAGNITUDE_SELF_PREPOSITIONS));
  }
  if (!omitClause(fields.time)) {
    leadClauses.push(prefixedClause("within", fields.time, TIME_SELF_PREPOSITIONS));
  }

  const trailingClauses: string[] = [];
  if (!omitClause(fields.scope)) {
    trailingClauses.push(`by targeting ${clauseText(fields.scope)}`);
  }
  if (!omitClause(fields.constraints)) {
    trailingClauses.push(`while subject to this constraint: ${clauseText(fields.constraints)}`);
  }
  if (!omitClause(fields.context)) {
    trailingClauses.push(`because ${clauseText(fields.context)}`);
  }

  let sentence = core;
  if (leadClauses.length) sentence += " " + leadClauses.join(" ");
  if (trailingClauses.length) sentence += " " + trailingClauses.join(", ");
  sentence = sentence.split(/\s+/).join(" ").replace(/[ ,]+$/, "");
  return capitalize(sentence) + ".";
}
