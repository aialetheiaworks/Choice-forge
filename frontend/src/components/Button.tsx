import { cva, type VariantProps } from "class-variance-authority";
import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

const button = cva(
  "inline-flex items-center justify-center gap-2 rounded-md font-sans font-medium " +
    "transition-transform duration-150 ease-[var(--ease-out-strong)] active:scale-97 " +
    "disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 " +
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
  {
    variants: {
      variant: {
        primary:
          "bg-brass-500 text-ink-950 hover:bg-brass-400 focus-visible:outline-brass-300",
        secondary:
          "border border-ink-500 bg-transparent text-parchment hover:border-ink-400 hover:bg-ink-800 focus-visible:outline-ink-300",
        ghost:
          "bg-transparent text-ink-300 hover:bg-ink-800 hover:text-parchment focus-visible:outline-ink-400",
        danger:
          "border border-rust-700 bg-transparent text-rust-300 hover:bg-rust-900 focus-visible:outline-rust-400",
      },
      size: {
        md: "px-4 py-2 text-sm",
        lg: "px-5 py-3 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={clsx(button({ variant, size }), className)} {...props} />;
}
