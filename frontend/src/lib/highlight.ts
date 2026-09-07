import type { BucketMatch } from "../types";

export interface HighlightSegment {
  text: string;
  bucketIndex: number | null;
}

export const BUCKET_COLOR_COUNT = 7;

export function bucketColorVar(index: number): string {
  return `var(--color-bucket-${(index % BUCKET_COLOR_COUNT) + 1})`;
}

function escapeRegExp(term: string): string {
  return term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Splits `text` into plain / bucket-matched segments so the master prompt can
 * render each matched term underlined in its bucket's color, with the bucket
 * name + reflection prompt available on hover.
 *
 * `ranked` is assumed pre-sorted by relevance (as the Bucket Matching Engine
 * returns it) — when the same term appears in more than one bucket's
 * `matched_terms`, the higher-ranked bucket wins so overlapping claims don't
 * fight each other.
 */
export function buildHighlightSegments(text: string, ranked: BucketMatch[]): HighlightSegment[] {
  if (!text) return [];

  const termToBucket = new Map<string, number>();
  ranked.forEach((bucket, bucketIndex) => {
    for (const term of bucket.matched_terms ?? []) {
      const key = term.trim().toLowerCase();
      if (key && !termToBucket.has(key)) {
        termToBucket.set(key, bucketIndex);
      }
    }
  });

  if (termToBucket.size === 0) {
    return [{ text, bucketIndex: null }];
  }

  const terms = [...termToBucket.keys()].sort((a, b) => b.length - a.length);
  const pattern = new RegExp(`\\b(${terms.map(escapeRegExp).join("|")})\\b`, "gi");

  const segments: HighlightSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ text: text.slice(lastIndex, match.index), bucketIndex: null });
    }
    const bucketIndex = termToBucket.get(match[0].toLowerCase()) ?? null;
    segments.push({ text: match[0], bucketIndex });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), bucketIndex: null });
  }
  return segments;
}
