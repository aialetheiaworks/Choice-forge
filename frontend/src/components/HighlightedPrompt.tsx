import { useMemo } from "react";
import type { BucketMatch } from "../types";
import { buildHighlightSegments, bucketColorVar } from "../lib/highlight";
import { HoverTip, HoverTipProvider } from "./HoverTip";

export function HighlightedPrompt({ text, ranked }: { text: string; ranked: BucketMatch[] }) {
  const segments = useMemo(() => buildHighlightSegments(text, ranked), [text, ranked]);

  return (
    <HoverTipProvider>
      <p className="font-serif text-lg leading-relaxed text-(--color-parchment)">
        {segments.map((seg, i) => {
          if (seg.bucketIndex === null) {
            return <span key={i}>{seg.text}</span>;
          }
          const bucket = ranked[seg.bucketIndex];
          const color = bucketColorVar(seg.bucketIndex);
          return (
            <HoverTip
              key={i}
              title={bucket.name}
              body={bucket.tooltip_line || bucket.prompt}
              accentColor={color}
            >
              <mark className="bucket-match" style={{ textDecorationColor: color, color }}>
                {seg.text}
              </mark>
            </HoverTip>
          );
        })}
      </p>
    </HoverTipProvider>
  );
}
