import { Button } from "./Button";
import type { Role } from "../types";

export function InitialGate({
  blanks,
  lowConfidence,
  onFixFields,
  onAcceptAsIs,
}: {
  blanks: Role[];
  lowConfidence: Role[];
  onFixFields: () => void;
  onAcceptAsIs: () => void;
}) {
  if (blanks.length > 0 || lowConfidence.length > 0) {
    const needFill = blanks.length > 0;
    return (
      <div className="rounded-md border border-brass-700 bg-brass-900/30 p-4">
        {needFill && (
          <p className="mb-2 font-sans text-sm text-brass-200">
            {blanks.length} field{blanks.length > 1 ? "s" : ""} still need your input:{" "}
            <span className="font-mono">{blanks.join(", ")}</span>.
          </p>
        )}
        {lowConfidence.length > 0 && (
          <p className="mb-3 font-sans text-sm text-brass-200">
            {lowConfidence.length} field{lowConfidence.length > 1 ? "s were" : " was"} extracted with
            low confidence — please check{" "}
            <span className="font-mono">{lowConfidence.join(", ")}</span> before continuing.
          </p>
        )}
        <Button onClick={onFixFields}>{needFill ? "Fill in the blanks" : "Review the fields"}</Button>
      </div>
    );
  }

  return (
    <div>
      <p className="mb-3 font-sans text-sm text-ink-300">Does this capture what you meant?</p>
      <div className="flex gap-3">
        <Button onClick={onAcceptAsIs}>Yes, this is right</Button>
        <Button variant="secondary" onClick={onFixFields}>
          Not quite — let me fix it
        </Button>
      </div>
    </div>
  );
}
