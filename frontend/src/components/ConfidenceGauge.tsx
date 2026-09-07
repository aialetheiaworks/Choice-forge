function tierColor(confidence: number): string {
  if (confidence < 0.4) return "var(--color-rust-500)";
  if (confidence < 0.7) return "var(--color-brass-500)";
  return "var(--color-verdigris-500)";
}

export function ConfidenceGauge({ confidence }: { confidence: number }) {
  const filled = Math.round(confidence * 10);
  const color = tierColor(confidence);
  return (
    <span className="inline-flex items-center gap-2">
      <span className="gauge" aria-hidden="true">
        {Array.from({ length: 10 }, (_, i) => (
          <span
            key={i}
            style={{
              height: `${5 + i}px`,
              backgroundColor: i < filled ? color : undefined,
            }}
          />
        ))}
      </span>
      <span className="font-mono text-xs" style={{ color }}>
        {confidence.toFixed(2)}
      </span>
    </span>
  );
}
