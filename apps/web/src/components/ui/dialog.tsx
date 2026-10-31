"use client";

import { useEffect, useId, useRef } from "react";
import { Button } from "./button";
import { Icon } from "../icon";

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  className = "",
  dismissible = true,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  dismissible?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`dialog ${className}`}
      aria-labelledby={`${id}-title`}
      aria-describedby={description ? `${id}-description` : undefined}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return;
        // Keep the cycle inside the modal, including browsers that otherwise
        // move focus to browser chrome at the first/last control.
        const controls = Array.from(
          event.currentTarget.querySelectorAll<HTMLElement>(
            "a[href], button, input, select, textarea, [tabindex]",
          ),
        ).filter(
          (element) =>
            element.tabIndex >= 0 &&
            !element.matches(":disabled, [hidden], [inert]") &&
            element.getClientRects().length > 0,
        );
        const first = controls[0];
        const last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (dismissible) onClose();
      }}
      onClose={onClose}
    >
      <div className="dialog-header">
        <h2 id={`${id}-title`}>{title}</h2>
        <Button
          variant="ghost"
          className="icon-button"
          aria-label="Close dialog"
          disabled={!dismissible}
          onClick={onClose}
        >
          <Icon name="close" />
        </Button>
      </div>
      {description && (
        <p id={`${id}-description`} className="dialog-description">
          {description}
        </p>
      )}
      <div className="dialog-content">{children}</div>
    </dialog>
  );
}
