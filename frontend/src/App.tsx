import { useState } from "react";
import { toast } from "sonner";
import { useConnectionStore } from "./store/useConnectionStore";
import * as api from "./api/client";
import { ApiGate } from "./components/ApiGate";
import { QueryScreen } from "./components/QueryScreen";
import { ExtractionDetails } from "./components/ExtractionDetails";
import { InitialGate } from "./components/InitialGate";
import { EditForm } from "./components/EditForm";
import { ReviewGate } from "./components/ReviewGate";
import { ConfirmedView } from "./components/ConfirmedView";
import { RejectedView } from "./components/RejectedView";
import { resolveAsIs } from "./lib/resolveFields";
import { renderSentence } from "./lib/renderSentence";
import type {
  BucketMatch,
  ExtractResponse,
  FieldValueInput,
  LogFieldEntry,
  ResolutionPath,
  Role,
} from "./types";

type Mode = "initial" | "editing" | "review_prompt";
type Decision = null | "confirmed" | "rejected";

interface PendingReview {
  finalFields: Record<Role, FieldValueInput>;
  logFields: Record<Role, LogFieldEntry>;
  resolutionPath: ResolutionPath;
  masterPromptLlm: string;
  masterPromptLlmError: string | null;
}

interface ConfirmedState {
  masterPrompt: string;
  error: string | null;
}

export default function App() {
  const { status: connStatus, baseUrl, disconnect } = useConnectionStore();

  const [query, setQuery] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [extractData, setExtractData] = useState<ExtractResponse | null>(null);

  const [mode, setMode] = useState<Mode>("initial");
  const [decision, setDecision] = useState<Decision>(null);
  const [assembling, setAssembling] = useState(false);
  const [pending, setPending] = useState<PendingReview | null>(null);
  const [rejectStreak, setRejectStreak] = useState(0);

  const [confirmed, setConfirmed] = useState<ConfirmedState | null>(null);
  const [ranked, setRanked] = useState<BucketMatch[]>([]);
  const [tooltipsLoading, setTooltipsLoading] = useState(false);
  const [tooltipsError, setTooltipsError] = useState<string | null>(null);

  if (connStatus !== "connected") {
    return <ApiGate />;
  }

  const resetFlow = () => {
    setExtractData(null);
    setMode("initial");
    setDecision(null);
    setPending(null);
    setConfirmed(null);
    setRanked([]);
    setTooltipsError(null);
  };

  /** "New query" in the header: unlike resetFlow (also used mid-run by
   * runQuery, which sets the new query text itself right after), this
   * clears the remembered query text too so the QueryScreen that reappears
   * starts genuinely blank instead of silently re-showing the last run's
   * text via QueryScreen's initialValue prop. */
  const startNewQuery = () => {
    resetFlow();
    setQuery("");
  };

  const runQuery = async (q: string) => {
    setQuery(q);
    setExtracting(true);
    resetFlow();
    try {
      const data = await api.extract(baseUrl, q);
      setExtractData(data);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setExtracting(false);
    }
  };

  const fetchTooltips = async (masterPrompt: string) => {
    setTooltipsLoading(true);
    setTooltipsError(null);
    try {
      const res = await api.tooltip(baseUrl, masterPrompt);
      setRanked(res.ranked);
      setTooltipsError(res.error);
    } catch (e) {
      setRanked([]);
      setTooltipsError(e instanceof Error ? e.message : String(e));
    } finally {
      setTooltipsLoading(false);
    }
  };

  const prepareReview = async (
    finalFields: Record<Role, FieldValueInput>,
    logFields: Record<Role, LogFieldEntry>,
    resolutionPath: ResolutionPath,
  ) => {
    setAssembling(true);
    try {
      const res = await api.assemble(baseUrl, query, finalFields);
      setPending({
        finalFields,
        logFields,
        resolutionPath,
        masterPromptLlm: res.master_prompt,
        masterPromptLlmError: res.error,
      });
      setMode("review_prompt");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setAssembling(false);
    }
  };

  const logAndFinish = async (
    finalFields: Record<Role, FieldValueInput>,
    logFields: Record<Role, LogFieldEntry>,
    resolutionPath: ResolutionPath,
    rejectReason: string | null,
    llmText: string | null,
    llmError: string | null,
  ) => {
    const isConfirmed = resolutionPath.startsWith("confirmed");
    const masterPromptFinal = renderSentence(finalFields);
    const entry = {
      timestamp: new Date().toISOString(),
      query,
      fields: logFields,
      master_prompt_shown: extractData?.template_master_prompt,
      master_prompt_final: masterPromptFinal,
      master_prompt_llm: llmText,
      master_prompt_llm_error: llmError,
      decision: isConfirmed ? "confirmed" : "rejected",
      resolution_path: resolutionPath,
      reject_reason: rejectReason,
      reject_streak_at_decision: rejectStreak,
      possible_compound_query_flagged: extractData?.possible_compound_query.is_possible_compound ?? false,
    };

    try {
      const logRes = await api.logEntry(baseUrl, entry);
      if (logRes.method !== "github") {
        toast.warning("Correction saved locally only — GITHUB_TOKEN isn't configured on the server.");
      }
    } catch (e) {
      toast.error(`Could not log this decision: ${e instanceof Error ? e.message : String(e)}`);
    }

    setPending(null);
    if (isConfirmed) {
      setRejectStreak(0);
      setDecision("confirmed");
      const finalText = llmText || masterPromptFinal;
      setConfirmed({ masterPrompt: finalText, error: llmError });
      fetchTooltips(finalText);
    } else {
      setRejectStreak((s) => s + 1);
      setDecision("rejected");
    }
  };

  const renderFlow = () => {
    if (extracting) {
      return <p className="font-sans text-sm text-ink-400">Reading your objective…</p>;
    }
    if (!extractData) return null;

    return (
      <div className="flex flex-col gap-6">
        {decision === null && (
          <div>
            <div className="mb-1 font-mono text-xs tracking-[0.2em] text-ink-400 uppercase">
              Your query
            </div>
            <div className="rounded-md border border-ink-700 bg-ink-900/60 p-4 font-serif text-base leading-relaxed text-ink-200">
              {extractData.query}
            </div>
          </div>
        )}

        {decision === null && (
          <div>
            <div className="mb-1 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">
              Here's what we understood
            </div>
            <div className="rounded-md border border-ink-700 bg-ink-900 p-4 font-serif text-lg leading-relaxed text-parchment">
              {mode === "review_prompt" && pending ? pending.masterPromptLlm : extractData.template_master_prompt}
            </div>
          </div>
        )}

        <ExtractionDetails fields={extractData.fields} />

        {decision === null && mode === "initial" && (
          <InitialGate
            blanks={extractData.blanks}
            lowConfidence={extractData.low_confidence}
            onFixFields={() => setMode("editing")}
            onAcceptAsIs={() => {
              const [finalFields, logFields] = resolveAsIs(extractData.display_fields, extractData.fields);
              prepareReview(finalFields, logFields, "confirmed_as_is");
            }}
          />
        )}

        {decision === null && mode === "editing" && (
          <EditForm
            displayFields={extractData.display_fields}
            rawFields={extractData.fields}
            compound={extractData.possible_compound_query}
            hasBlanks={extractData.blanks.length > 0}
            onContinue={(finalFields, logFields) => prepareReview(finalFields, logFields, "confirmed_with_edits")}
            onReject={(reason, finalFields, logFields) =>
              logAndFinish(finalFields, logFields, "rejected", reason, null, null)
            }
          />
        )}

        {decision === null && mode === "review_prompt" && pending && (
          <ReviewGate
            promptText={pending.masterPromptLlm}
            error={pending.masterPromptLlmError}
            onApprove={() =>
              logAndFinish(
                pending.finalFields,
                pending.logFields,
                pending.resolutionPath,
                null,
                pending.masterPromptLlm,
                pending.masterPromptLlmError,
              )
            }
            onFixFields={() => {
              setPending(null);
              setMode("editing");
            }}
          />
        )}

        {assembling && <p className="font-sans text-sm text-ink-400">Assembling your master prompt…</p>}

        {decision === "rejected" && (
          <RejectedView
            onRetry={() => {
              // Rephrase means rewriting the raw query, not re-editing the
              // fields that were just rejected — send them back to the
              // query box, pre-filled with the same text (resetFlow leaves
              // `query` untouched), same as app.py's rephrase button.
              resetFlow();
            }}
          />
        )}

        {decision === "confirmed" && confirmed && (
          <ConfirmedView
            promptText={confirmed.masterPrompt}
            promptError={confirmed.error}
            ranked={ranked}
            tooltipsLoading={tooltipsLoading}
            tooltipsError={tooltipsError}
            onRetryTooltips={() => fetchTooltips(confirmed.masterPrompt)}
          />
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-800 px-6 py-4">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <div className="font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">CHOICE Forge</div>
          <div className="flex items-center gap-3">
            {extractData && (
              <button
                onClick={startNewQuery}
                className="font-sans text-xs text-ink-400 transition-colors hover:text-parchment"
              >
                New query
              </button>
            )}
            <span className="font-mono text-[11px] text-ink-500">{baseUrl}</span>
            <button
              onClick={disconnect}
              className="font-sans text-xs text-ink-400 transition-colors hover:text-parchment"
            >
              Change server
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10">
        {!extractData && !extracting ? (
          <QueryScreen initialValue={query} loading={extracting} onRun={runQuery} />
        ) : (
          renderFlow()
        )}
      </main>
    </div>
  );
}
