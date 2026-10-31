import { Icon } from "../icon";

export function Message({
  tone = "info",
  title,
  children,
  announce = false,
}: {
  tone?: "info" | "error" | "success";
  title: string;
  children?: React.ReactNode;
  announce?: boolean;
}) {
  return (
    <div
      className={`message message--${tone}`}
      role={announce ? (tone === "error" ? "alert" : "status") : undefined}
    >
      <Icon name={tone === "success" ? "check" : "info"} />
      <div>
        <p className="message-title">{title}</p>
        {children && <div className="message-description">{children}</div>}
      </div>
    </div>
  );
}

export function LoadingState({
  label = "Loading your workspace...",
}: {
  label?: string;
}) {
  return (
    <div className="loading-state" role="status" aria-busy="true">
      <p>
        <span className="spinner" aria-hidden="true" />
        {label}
      </p>
      <div className="skeleton-group" aria-hidden="true">
        <span className="skeleton skeleton--short" />
        <span className="skeleton" />
        <span className="skeleton skeleton--medium" />
      </div>
    </div>
  );
}
