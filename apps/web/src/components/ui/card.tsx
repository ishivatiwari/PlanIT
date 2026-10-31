import type { ComponentProps } from "react";

export function Card({ className = "", ...props }: ComponentProps<"div">) {
  return <div {...props} className={`card ${className}`} />;
}

export function Badge({
  tone = "neutral",
  className = "",
  children,
}: {
  tone?: "neutral" | "good" | "warning";
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span className={`badge badge--${tone} ${className}`}>{children}</span>
  );
}
