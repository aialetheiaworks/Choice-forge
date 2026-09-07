export const ROLES = [
  "actor",
  "object",
  "intent",
  "scope",
  "measure",
  "magnitude",
  "time",
  "constraints",
  "context",
] as const;

export type Role = (typeof ROLES)[number];

export const NOT_APPLICABLE_ELIGIBLE_ROLES: ReadonlySet<Role> = new Set([
  "scope",
  "magnitude",
  "time",
  "constraints",
  "context",
]);

export const ROLE_LABELS: Record<Role, string> = {
  actor: "Actor",
  object: "Object",
  intent: "Intent",
  scope: "Scope",
  measure: "Measure",
  magnitude: "Magnitude",
  time: "Time",
  constraints: "Constraints",
  context: "Context",
};

export interface RawField {
  value: string | string[] | null;
  status: "explicit" | "missing";
  confidence: number;
  source_text: string | null;
  flagged_for_review: boolean;
  guard_note: string | null;
  multi_span: boolean;
}

export interface DisplayField {
  text: string;
  blank: boolean;
  multi_span: boolean;
  dropped_values: boolean;
  /** value is shown but the pipeline scored it below the review threshold */
  low_confidence: boolean;
  needs_review: boolean;
  confidence: number;
  status: "explicit" | "missing";
  not_applicable: boolean;
}

export interface CompoundQueryInfo {
  is_possible_compound: boolean;
  multi_span_roles: Role[];
  message: string | null;
}

export interface ExtractResponse {
  query: string;
  fields: Record<Role, RawField>;
  display_fields: Record<Role, DisplayField>;
  template_master_prompt: string;
  blanks: Role[];
  low_confidence: Role[];
  needs_review: Role[];
  possible_compound_query: CompoundQueryInfo;
}

export interface FieldValueInput {
  text: string;
  blank: boolean;
  not_applicable: boolean;
}

export interface AssembleResponse {
  master_prompt: string;
  template_master_prompt: string;
  used_llm: boolean;
  error: string | null;
}

export interface BucketMatch {
  name: string;
  prompt: string;
  score?: number;
  matched_terms?: string[];
  tooltip_line?: string;
  [key: string]: unknown;
}

export interface TooltipResponse {
  ranked: BucketMatch[];
  error: string | null;
}

export interface LogFieldEntry {
  original_value: string | string[] | null;
  original_status: string;
  original_confidence: number;
  blank: boolean;
  not_applicable: boolean;
  needs_review: boolean;
  multi_span: boolean;
  final_value: string | null;
  user_edited: boolean;
  ai_suggested: boolean;
  ai_suggestion_shown: string | null;
}

export type ResolutionPath = "confirmed_as_is" | "confirmed_with_edits" | "rejected";

export interface LogResponse {
  method: "github" | "local_fallback";
  error: string | null;
}

export interface HealthResponse {
  status: string;
  models_loaded: boolean;
  roles: Role[];
}
