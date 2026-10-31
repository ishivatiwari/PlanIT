"use client";

import { useId, type ComponentProps } from "react";

type FieldProps = { label: string; hint?: string; error?: string };

export function TextAreaField({
  label,
  hint,
  error,
  id,
  className = "",
  ...props
}: ComponentProps<"textarea"> & FieldProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const description =
    [
      props["aria-describedby"],
      hint && `${fieldId}-hint`,
      error && `${fieldId}-error`,
    ]
      .filter(Boolean)
      .join(" ") || undefined;
  return (
    <div className="field">
      <label htmlFor={fieldId}>
        {label}
        {props.required && <span className="field-required"> (required)</span>}
      </label>
      {hint && (
        <p className="field-hint" id={`${fieldId}-hint`}>
          {hint}
        </p>
      )}
      <textarea
        {...props}
        id={fieldId}
        rows={props.rows ?? 3}
        className={`input ${className}`}
        aria-describedby={description}
        aria-invalid={error ? true : props["aria-invalid"]}
      />
      {error && (
        <p className="field-error" id={`${fieldId}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

export function TextField({
  label,
  hint,
  error,
  id,
  className = "",
  "aria-describedby": describedBy,
  ...props
}: ComponentProps<"input"> & FieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const description =
    [describedBy, hint && `${inputId}-hint`, error && `${inputId}-error`]
      .filter(Boolean)
      .join(" ") || undefined;
  return (
    <div className="field">
      <label htmlFor={inputId}>
        {label}
        {props.required && <span className="field-required"> (required)</span>}
      </label>
      {hint && (
        <p className="field-hint" id={`${inputId}-hint`}>
          {hint}
        </p>
      )}
      <input
        {...props}
        id={inputId}
        className={`input ${className}`}
        aria-describedby={description}
        aria-invalid={error ? true : props["aria-invalid"]}
      />
      {error && (
        <p className="field-error" id={`${inputId}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

export function SelectField({
  label,
  hint,
  error,
  id,
  className = "",
  "aria-describedby": describedBy,
  children,
  ...props
}: ComponentProps<"select"> & FieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const description =
    [describedBy, hint && `${inputId}-hint`, error && `${inputId}-error`]
      .filter(Boolean)
      .join(" ") || undefined;
  return (
    <div className="field">
      <label htmlFor={inputId}>
        {label}
        {props.required && <span className="field-required"> (required)</span>}
      </label>
      {hint && (
        <p className="field-hint" id={`${inputId}-hint`}>
          {hint}
        </p>
      )}
      <select
        {...props}
        id={inputId}
        className={`input select ${className}`}
        aria-describedby={description}
        aria-invalid={error ? true : props["aria-invalid"]}
      >
        {children}
      </select>
      {error && (
        <p className="field-error" id={`${inputId}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}
