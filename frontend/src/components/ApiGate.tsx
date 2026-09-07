import { useEffect, useRef, useState } from "react";
import { useConnectionStore } from "../store/useConnectionStore";
import { Button } from "./Button";

export function ApiGate() {
  const { baseUrl, status, error, connect } = useConnectionStore();
  const [draft, setDraft] = useState(baseUrl);

  // Auto-reconnect once on mount using the remembered URL, so returning to
  // an already-configured server doesn't require a manual click every time.
  // Guarded with a ref (not `status`) so this fires exactly once — a
  // dependency on `status` would re-fire after every failed attempt.
  const triedAutoConnect = useRef(false);
  useEffect(() => {
    if (!triedAutoConnect.current) {
      triedAutoConnect.current = true;
      connect(baseUrl);
    }
  }, [baseUrl, connect]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = draft.trim().replace(/\/$/, "");
    if (trimmed) connect(trimmed);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-6">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-2 font-mono text-xs tracking-[0.2em] text-brass-400 uppercase">
            CHOICE Forge
          </div>
          <h1 className="font-serif text-2xl text-parchment">Connect to your API server</h1>
          <p className="mt-2 font-sans text-sm text-ink-300">
            Enter the address of your locally running backend to continue.
          </p>
        </div>

        <form onSubmit={submit} className="flex flex-col gap-3">
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="http://localhost:8000"
            className="w-full rounded-md border border-ink-600 bg-ink-900 px-4 py-3 font-mono text-sm text-parchment outline-none placeholder:text-ink-400 focus:border-brass-500"
          />
          <Button type="submit" size="lg" disabled={status === "checking"}>
            {status === "checking" ? "Connecting…" : "Connect"}
          </Button>
        </form>

        {status === "error" && (
          <div className="mt-4 rounded-md border border-rust-700 bg-rust-900/40 p-3 font-sans text-sm text-rust-200">
            {error}
            <div className="mt-1 text-xs text-rust-300">
              Make sure the API is running — from the project root:{" "}
              <code className="font-mono">uvicorn api:app --port 8000</code>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
