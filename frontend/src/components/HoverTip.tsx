import { Tooltip } from "@base-ui/react/tooltip";
import type { ReactNode } from "react";

export function HoverTipProvider({ children }: { children: ReactNode }) {
  return (
    <Tooltip.Provider delay={250} closeDelay={80}>
      {children}
    </Tooltip.Provider>
  );
}

export function HoverTip({
  children,
  title,
  body,
  accentColor,
}: {
  children: ReactNode;
  title: string;
  body: string;
  accentColor: string;
}) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger render={<span aria-label={title}>{children}</span>} />
      <Tooltip.Portal>
        <Tooltip.Positioner sideOffset={8} className="z-50">
          <Tooltip.Popup
            className="max-w-72 rounded-lg border p-3 shadow-xl transition-[transform,opacity] duration-150 data-[starting-style]:scale-95 data-[starting-style]:opacity-0 data-[ending-style]:scale-95 data-[ending-style]:opacity-0"
            style={{
              backgroundColor: "var(--color-ink-800)",
              borderColor: accentColor,
              transformOrigin: "var(--transform-origin)",
            }}
          >
            <div
              className="mb-1 font-sans text-[11px] font-semibold tracking-wide uppercase"
              style={{ color: accentColor }}
            >
              {title}
            </div>
            <div className="font-serif text-sm leading-snug text-(--color-parchment)">{body}</div>
          </Tooltip.Popup>
        </Tooltip.Positioner>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
