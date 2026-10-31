"use client";

import { useRef, useState, type FormEvent } from "react";
import { api, errorMessage } from "@/lib/api";
import type { PlanDocument, PlanRead } from "@/lib/api-types";
import { formatMoney, minorInput, parseMinor } from "@/lib/money";
import { useAuth } from "./auth-provider";
import { Button } from "./ui/button";
import { Card, Badge } from "./ui/card";
import { TextAreaField, TextField } from "./ui/field";
import { Message } from "./ui/feedback";

const clean = (rows: string[]) => rows.map((row) => row.trim()).filter(Boolean);
export function PlanEditor({
  initial,
  editable,
  onSaved,
}: {
  initial: PlanRead;
  editable: boolean;
  onSaved: (plan: PlanRead) => void;
}) {
  const auth = useAuth();
  const [plan, setPlan] = useState(initial),
    [document, setDocument] = useState<PlanDocument>(initial.document);
  const [amounts, setAmounts] = useState(
    initial.document.budget_categories.map((row) =>
      minorInput(row.estimated_amount_minor, initial.currency),
    ),
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [saved, setSaved] = useState(false),
    [dirty, setDirty] = useState(false);
  const notice = useRef<HTMLDivElement>(null);
  function change(value: PlanDocument) {
    setDocument(value);
    setDirty(true);
    setSaved(false);
  }
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!auth.session) return;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const prepared: PlanDocument = {
        ...document,
        budget_categories: document.budget_categories.map((row, i) => {
          const amount = parseMinor(amounts[i], plan.currency);
          if (amount === null)
            throw new Error(
              "Enter every category estimate, including zero if needed.",
            );
          return { ...row, estimated_amount_minor: amount };
        }),
        preparation_tasks: document.preparation_tasks.map((row) => ({
          ...row,
          checklist: clean(row.checklist),
        })),
        vendor_requirements: document.vendor_requirements.map((row) => ({
          ...row,
          checklist: clean(row.checklist),
          requirements: clean(row.requirements),
        })),
        themes: clean(document.themes),
        menus: clean(document.menus),
        decor: clean(document.decor),
        activities: clean(document.activities),
        assumptions: clean(document.assumptions),
        unresolved_questions: clean(document.unresolved_questions),
        conflicts: clean(document.conflicts),
      };
      const result = await api<PlanRead>(
        `/events/${plan.event_id}/plans/${plan.id}`,
        {
          method: "PATCH",
          data: { document: prepared },
          csrf: auth.session.csrf_token,
          revision: plan.revision,
        },
      );
      setPlan(result);
      setDocument(result.document);
      setDirty(false);
      setSaved(true);
      onSaved(result);
    } catch (e) {
      setError(errorMessage(e));
      requestAnimationFrame(() => notice.current?.focus());
    } finally {
      setBusy(false);
    }
  }
  const sections = [
    ["themes", "Themes"],
    ["menus", "Menu ideas"],
    ["decor", "Décor"],
    ["activities", "Activities"],
    ["assumptions", "Assumptions"],
    ["unresolved_questions", "Unresolved questions"],
    ["conflicts", "Conflicts to resolve"],
  ] as const;
  return (
    <form className="plan-editor" onSubmit={(e) => void save(e)}>
      <div className="section-heading">
        <h2>Review your initial plan.</h2>
        <Badge>
          {dirty
            ? "Unsaved changes"
            : plan.saved_at
              ? "Reviewed and saved"
              : "Needs review"}
        </Badge>
      </div>
      {plan.warnings.map((warning, i) => (
        <Message
          key={i}
          title={i === 0 ? "Estimates and assumptions" : "Review needed"}
        >
          {warning}
        </Message>
      ))}
      {(plan.explanations ?? []).length > 0 && (
        <Message title="Why these suggestions fit">
          <ul>
            {(plan.explanations ?? []).map((explanation, i) => (
              <li key={i}>{explanation}</li>
            ))}
          </ul>
        </Message>
      )}
      {!editable && (
        <Message title="Read-only draft">
          The event is archived or its details changed after this draft. You can
          still review the saved content.
        </Message>
      )}
      {error && (
        <div ref={notice} tabIndex={-1}>
          <Message tone="error" title="Plan not saved" announce>
            {error} Your edits remain here.
          </Message>
        </div>
      )}
      {saved && (
        <Message tone="success" title="Plan saved" announce>
          Your reviewed draft is saved. This does not approve costs or make
          bookings.
        </Message>
      )}
      <fieldset disabled={!editable || busy}>
        <legend className="sr-only">Editable plan sections</legend>
        <Card>
          <TextAreaField
            label="Event summary"
            required
            maxLength={1500}
            rows={4}
            value={document.summary}
            onChange={(e) => change({ ...document, summary: e.target.value })}
          />
        </Card>
        <Card>
          <h3>Budget category proposals</h3>
          <p>
            Initial amounts allocate your ceiling by priority. Edit them as your
            estimates improve; confirm real prices separately.
          </p>
          <p className="budget-summary">
            Saved estimate total:{" "}
            <strong>
              {formatMoney(plan.estimated_total_minor, plan.currency)}
            </strong>{" "}
            · Ceiling: {formatMoney(plan.budget_ceiling_minor, plan.currency)}
          </p>
          {document.budget_categories.map((row, i) => (
            <div className="plan-row" key={i}>
              <div className="form-grid">
                <TextField
                  label={`Category ${i + 1}`}
                  required
                  maxLength={80}
                  value={row.category}
                  onChange={(e) =>
                    change({
                      ...document,
                      budget_categories: document.budget_categories.map(
                        (r, n) =>
                          n === i ? { ...r, category: e.target.value } : r,
                      ),
                    })
                  }
                />
                <TextField
                  label={`Estimated amount ${i + 1} (${plan.currency})`}
                  required
                  inputMode="decimal"
                  value={amounts[i]}
                  onChange={(e) => {
                    setAmounts((old) =>
                      old.map((a, n) => (n === i ? e.target.value : a)),
                    );
                    setDirty(true);
                    setSaved(false);
                  }}
                />
                <TextField
                  label={`Estimate notes ${i + 1}`}
                  required
                  maxLength={160}
                  value={row.description}
                  onChange={(e) =>
                    change({
                      ...document,
                      budget_categories: document.budget_categories.map(
                        (r, n) =>
                          n === i ? { ...r, description: e.target.value } : r,
                      ),
                    })
                  }
                />
              </div>
              <Button
                variant="ghost"
                disabled={document.budget_categories.length === 1}
                onClick={() => {
                  change({
                    ...document,
                    budget_categories: document.budget_categories.filter(
                      (_, n) => n !== i,
                    ),
                  });
                  setAmounts((old) => old.filter((_, n) => n !== i));
                }}
              >
                Remove category {i + 1}
              </Button>
            </div>
          ))}
          <Button
            variant="secondary"
            disabled={document.budget_categories.length >= 12}
            onClick={() => {
              change({
                ...document,
                budget_categories: [
                  ...document.budget_categories,
                  { category: "", description: "", estimated_amount_minor: 0 },
                ],
              });
              setAmounts((old) => [...old, "0"]);
            }}
          >
            Add budget category
          </Button>
        </Card>
        <Card>
          <h3>Preparation timeline</h3>
          <p>
            Dates below are calculated from the saved event date. Review lead
            times; past dates are flagged.
          </p>
          {document.preparation_tasks.map((row, i) => (
            <div key={i} className="plan-row">
              <div className="form-grid">
                <TextField
                  label={`Task ${i + 1}`}
                  required
                  maxLength={160}
                  value={row.title}
                  onChange={(e) =>
                    change({
                      ...document,
                      preparation_tasks: document.preparation_tasks.map(
                        (r, n) =>
                          n === i ? { ...r, title: e.target.value } : r,
                      ),
                    })
                  }
                />
                <TextField
                  label={`Days before event ${i + 1}`}
                  type="number"
                  required
                  min={0}
                  max={365}
                  step={1}
                  value={row.days_before_event}
                  onChange={(e) =>
                    change({
                      ...document,
                      preparation_tasks: document.preparation_tasks.map(
                        (r, n) =>
                          n === i
                            ? {
                                ...r,
                                days_before_event: Number(e.target.value),
                              }
                            : r,
                      ),
                    })
                  }
                />
                <TextAreaField
                  label={`Task checklist ${i + 1}`}
                  value={row.checklist.join("\n")}
                  onChange={(e) =>
                    change({
                      ...document,
                      preparation_tasks: document.preparation_tasks.map(
                        (r, n) =>
                          n === i
                            ? { ...r, checklist: e.target.value.split("\n") }
                            : r,
                      ),
                    })
                  }
                  hint="One item per line."
                />
              </div>
              {!dirty && plan.schedule[i] && (
                <p className="caption">
                  Suggested date: {plan.schedule[i].due_on}
                  {plan.schedule[i].needs_rescheduling
                    ? " · Needs rescheduling"
                    : ""}
                </p>
              )}
              <Button
                variant="ghost"
                disabled={document.preparation_tasks.length === 1}
                onClick={() =>
                  change({
                    ...document,
                    preparation_tasks: document.preparation_tasks.filter(
                      (_, n) => n !== i,
                    ),
                  })
                }
              >
                Remove task {i + 1}
              </Button>
            </div>
          ))}
          <Button
            variant="secondary"
            disabled={document.preparation_tasks.length >= 20}
            onClick={() =>
              change({
                ...document,
                preparation_tasks: [
                  ...document.preparation_tasks,
                  { title: "", days_before_event: 0, checklist: [] },
                ],
              })
            }
          >
            Add preparation task
          </Button>
        </Card>
        <Card>
          <h3>Vendor requirements</h3>
          <p>
            Generic requirements to help you request quotes. No availability or
            quotation has been verified.
          </p>
          {document.vendor_requirements.map((row, i) => (
            <div key={i} className="plan-row">
              <TextField
                label={`Vendor category ${i + 1}`}
                required
                maxLength={80}
                value={row.category}
                onChange={(e) =>
                  change({
                    ...document,
                    vendor_requirements: document.vendor_requirements.map(
                      (r, n) =>
                        n === i ? { ...r, category: e.target.value } : r,
                    ),
                  })
                }
              />
              <div className="form-grid">
                {(["requirements", "checklist"] as const).map((field) => (
                  <TextAreaField
                    key={field}
                    label={`${field === "requirements" ? "Requirements" : "Vendor checklist"} ${i + 1}`}
                    value={row[field].join("\n")}
                    onChange={(e) =>
                      change({
                        ...document,
                        vendor_requirements: document.vendor_requirements.map(
                          (r, n) =>
                            n === i
                              ? { ...r, [field]: e.target.value.split("\n") }
                              : r,
                        ),
                      })
                    }
                    hint="One item per line."
                  />
                ))}
              </div>
              <Button
                variant="ghost"
                onClick={() =>
                  change({
                    ...document,
                    vendor_requirements: document.vendor_requirements.filter(
                      (_, n) => n !== i,
                    ),
                  })
                }
              >
                Remove vendor requirement {i + 1}
              </Button>
            </div>
          ))}
          <Button
            variant="secondary"
            disabled={document.vendor_requirements.length >= 10}
            onClick={() =>
              change({
                ...document,
                vendor_requirements: [
                  ...document.vendor_requirements,
                  { category: "", requirements: [], checklist: [] },
                ],
              })
            }
          >
            Add vendor requirement
          </Button>
        </Card>
        <Card>
          <h3>Personal touches and open questions</h3>
          <div className="form-grid">
            {sections.map(([name, label]) => (
              <TextAreaField
                key={name}
                label={label}
                rows={4}
                value={document[name].join("\n")}
                onChange={(e) =>
                  change({ ...document, [name]: e.target.value.split("\n") })
                }
                hint="One suggestion per line, up to 12; each up to 200 characters."
              />
            ))}
          </div>
        </Card>
        {editable && (
          <div className="form-actions">
            <Button
              type="submit"
              loading={busy}
              loadingLabel="Saving your review..."
            >
              Save reviewed plan
            </Button>
            <p className="caption">
              Totals and suggested dates are recalculated when saved. This
              remains a draft.
            </p>
          </div>
        )}
      </fieldset>
    </form>
  );
}
