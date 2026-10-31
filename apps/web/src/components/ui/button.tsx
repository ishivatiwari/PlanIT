import Link from "next/link";
import type { ComponentProps } from "react";

type Variant = "primary" | "secondary" | "ghost";

export function Button({
  variant = "primary",
  loading = false,
  loadingLabel = "Working...",
  className = "",
  children,
  disabled,
  type = "button",
  ...props
}: ComponentProps<"button"> & {
  variant?: Variant;
  loading?: boolean;
  loadingLabel?: string;
}) {
  return (
    <button
      {...props}
      type={type}
      className={`button button--${variant} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {loading ? (
        <>
          <span className="spinner" aria-hidden="true" />
          {loadingLabel}
        </>
      ) : (
        children
      )}
    </button>
  );
}

export function ButtonLink({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant }) {
  return (
    <Link {...props} className={`button button--${variant} ${className}`} />
  );
}
