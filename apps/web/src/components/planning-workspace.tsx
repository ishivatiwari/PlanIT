"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type {
  AIStatus,
  EventRead,
  Extraction,
  IntakeDetails,
  PlanPage,
  PlanRead,
  RunRead,
} from "@/lib/api-types";
import { RequireAccount, useAuth } from "./auth-provider";
import { PlanEditor } from "./plan-editor";
import { Button, ButtonLink } from "./ui/button";
import { Card, Badge } from "./ui/card";
import { TextAreaField, TextField, SelectField } from "./ui/field";
import { LoadingState, Message } from "./ui/feedback";

const failureMessages: Record<string, string> = {
  AI_TIMEOUT:
    "The model took too long. Your existing plans are safe. Try again when ready.",
  AI_REFUSED:
    "The model could not help with this request. Rephrase the event details and try again.",
  AI_INVALID_OUTPUT:
    "The response did not pass validation. Nothing replaced your existing plan. Please try again.",
  AI_INCOMPLETE:
    "The response was incomplete. Try a shorter description or ask your administrator to review the output limit.",
  AI_CONFIGURATION_ERROR:
    "The AI service configuration needs attention. Your events and saved plans remain available.",
  AI_RATE_LIMITED: "The provider is busy. Wait a moment before trying again.",
  AI_INTERRUPTED:
    "This request was interrupted. Check saved drafts, then start a new request if needed.",
  EVENT_CHANGED:
    "Your event changed while this request was running. Reload its latest details before generating again.",
  APPROVED_PLAN_EXISTS:
    "An approved plan already exists. Initial generation cannot replace it.",
};

function IntakeReview({
  initial,
  busy,
  onGenerate,
}: {
  initial: Extraction;
  busy: boolean;
  onGenerate: (details: IntakeDetails) => void;
}) {
  const [details, setDetails] = useState(initial.details);
  const [confirmed, setConfirmed] = useState(false);
  function field<K extends keyof IntakeDetails>(
    name: K,
    value: IntakeDetails[K],
  ) {
    setDetails((old) => ({ ...old, [name]: value }));
    setConfirmed(false);
  }
  const textFields = [
    ["title", "Event name", "text"],
    ["location", "Location", "text"],
    ["start_local", "Start date and time", "datetime-local"],
    [
      "end_local",
      "End date and time (optional with duration)",
      "datetime-local",
    ],
    ["timezone", "Timezone", "text"],
    ["budget_amount", "Budget ceiling", "text"],
  ] as const;
  return (
    <Card className="planning-review">
      <h2>Make the details yours.</h2>
      <p className="section-description">
        Check the extracted details and answer anything missing. These details
        will be saved to the event only when generation succeeds.
      </p>
      {initial.questions.length > 0 && (
        <Message title="A few details to clarify">
          <ul>
            {initial.questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </Message>
      )}
      {initial.conflicts.length > 0 && (
        <Message tone="error" title="Resolve these conflicts before continuing">
          <ul>
            {initial.conflicts.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </Message>
      )}
      {initial.assumptions.length > 0 && (
        <Message title="Assumptions to check">
          <ul>
            {initial.assumptions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </Message>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (confirmed) onGenerate(details);
        }}
      >
        <fieldset disabled={busy}>
          <legend className="sr-only">Reviewed event details</legend>
          <div className="form-grid">
            {textFields.map(([name, label, type]) => (
              <TextField
                key={name}
                label={label}
                type={type}
                required={name !== "end_local"}
                value={details[name] ?? ""}
                onChange={(e) => field(name, e.target.value || null)}
                hint={
                  name === "budget_amount"
                    ? "An amount in the selected currency; common suffixes such as lakh are accepted. No currency conversion."
                    : name === "timezone"
                      ? "Use an IANA name such as Asia/Kolkata."
                      : undefined
                }
              />
            ))}
            <SelectField
              label="Event type"
              required
              value={details.event_type ?? ""}
              onChange={(e) =>
                field(
                  "event_type",
                  e.target.value as IntakeDetails["event_type"],
                )
              }
            >
              <option value="">Choose an occasion</option>
              <option value="wedding">Wedding</option>
              <option value="birthday">Birthday</option>
              <option value="community">Community event</option>
            </SelectField>
            <SelectField
              label="Currency"
              required
              value={details.currency ?? ""}
              onChange={(e) =>
                field("currency", e.target.value as IntakeDetails["currency"])
              }
            >
              <option value="">Choose currency</option>
              {["INR", "USD", "EUR", "GBP", "JPY"].map((code) => (
                <option key={code}>{code}</option>
              ))}
            </SelectField>
            <TextField
              label="Guest count"
              type="number"
              min={1}
              max={1000000}
              step={1}
              required
              value={details.guest_count ?? ""}
              onChange={(e) =>
                field(
                  "guest_count",
                  e.target.value === "" ? null : Number(e.target.value),
                )
              }
            />
            <TextField
              label="Duration in minutes"
              type="number"
              min={1}
              max={10080}
              step={1}
              required={!details.end_local}
              value={details.duration_minutes ?? ""}
              onChange={(e) =>
                field(
                  "duration_minutes",
                  e.target.value === "" ? null : Number(e.target.value),
                )
              }
              hint="If both end time and duration are supplied, they must agree."
            />
            {(["start_fold", "end_fold"] as const).map((name) => (
              <SelectField
                key={name}
                label={
                  name === "start_fold"
                    ? "Start time occurrence"
                    : "End time occurrence"
                }
                value={details[name] == null ? "" : String(details[name])}
                onChange={(e) =>
                  field(
                    name,
                    e.target.value === ""
                      ? null
                      : e.target.value === "1"
                        ? 1
                        : 0,
                  )
                }
                hint="Only needed when a clock change repeats the local time."
              >
                <option value="">Not specified</option>
                <option value="0">First occurrence</option>
                <option value="1">Second occurrence</option>
              </SelectField>
            ))}
            {(["dietary_needs", "accessibility_needs"] as const).map((name) => (
              <TextAreaField
                key={name}
                label={
                  name === "dietary_needs"
                    ? "Dietary needs"
                    : "Accessibility needs"
                }
                required
                maxLength={2000}
                value={details[name] === "" ? "None" : (details[name] ?? "")}
                onChange={(e) =>
                  field(
                    name,
                    e.target.value.toLowerCase() === "none"
                      ? ""
                      : e.target.value || null,
                  )
                }
                hint="Enter None if there are no needs; an unanswered field is unknown."
              />
            ))}
            {(["preferences", "constraints"] as const).map((name) => (
              <TextAreaField
                key={name}
                label={
                  name === "preferences"
                    ? "Preferences"
                    : "Constraints and must-haves"
                }
                value={details[name].join("\n")}
                onChange={(e) => field(name, e.target.value.split("\n"))}
                hint="One item per line. Resolve incompatible requirements before continuing."
              />
            ))}
          </div>
          <label className="consent-check">
            <input
              type="checkbox"
              required
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <span>
              I have checked these details and resolved conflicting
              requirements.
            </span>
          </label>
          <Button
            type="submit"
            disabled={!confirmed}
            loading={busy}
            loadingLabel="Generating your draft..."
          >
            Generate and save draft
          </Button>
          <p className="caption">
            Creates a separate editable draft. No vendors are contacted and no
            booking is made.
          </p>
        </fieldset>
      </form>
    </Card>
  );
}

function Workspace({ id }: { id: string }) {
  const auth = useAuth();
  const [event, setEvent] = useState<EventRead | null>(null),
    [status, setStatus] = useState<AIStatus | null>(null);
  const [plans, setPlans] = useState<PlanRead[]>([]),
    [nextBefore, setNextBefore] = useState<number | null>(null),
    [runs, setRuns] = useState<RunRead[]>([]);
  const [description, setDescription] = useState(""),
    [consent, setConsent] = useState(false),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [extraction, setExtraction] = useState<Extraction | null>(null),
    [selected, setSelected] = useState<PlanRead | null>(null),
    [reviewKey, setReviewKey] = useState(0);
  const pending = useRef<{ signature: string; key: string } | null>(null);
  const notice = useRef<HTMLDivElement>(null),
    review = useRef<HTMLDivElement>(null);
  const refresh = useCallback(
    () =>
      Promise.all([
        api<EventRead>(`/events/${id}`),
        api<AIStatus>("/ai/status"),
        api<PlanPage>(`/events/${id}/plans`),
        api<RunRead[]>(`/events/${id}/generations`),
      ])
        .then(([e, s, p, r]) => {
          setEvent(e);
          setStatus(s);
          setPlans(p.items);
          setNextBefore(p.next_before);
          setRuns(r);
        })
        .catch((e: unknown) => setError(errorMessage(e)))
        .finally(() => setLoading(false)),
    [id],
  );
  useEffect(() => {
    void refresh();
  }, [refresh]);
  useEffect(() => {
    if (error) notice.current?.focus();
  }, [error]);
  useEffect(() => {
    if (extraction || selected) review.current?.focus();
  }, [extraction, selected]);

  async function run(operation: "intake" | "generations", data: unknown) {
    if (!event || !auth.session) return;
    setBusy(true);
    setError("");
    const signature = JSON.stringify({
      operation,
      data,
      revision: event.revision,
    });
    if (pending.current?.signature !== signature)
      pending.current = { signature, key: crypto.randomUUID() };
    try {
      const result = await api<RunRead>(`/events/${id}/${operation}`, {
        method: "POST",
        data,
        csrf: auth.session.csrf_token,
        revision: event.revision,
        requestKey: pending.current.key,
        timeoutMs: 80000,
      });
      if (result.status !== "running") pending.current = null;
      if (result.status === "failed")
        throw new Error(
          failureMessages[result.error_code ?? ""] ??
            "The request failed. Your existing plans are safe. Please try again.",
        );
      if (result.status === "running")
        throw new Error(
          "This request is still running. Check recent requests before starting another.",
        );
      if (result.extraction) {
        setExtraction(result.extraction);
        setReviewKey((key) => key + 1);
        setSelected(null);
      }
      if (result.plan_id) {
        setSelected(
          await api<PlanRead>(`/events/${id}/plans/${result.plan_id}`),
        );
        setExtraction(null);
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
      void refresh();
    }
  }
  if (loading) return <LoadingState label="Opening your planning space..." />;
  if (!event)
    return (
      <Message tone="error" title="Planning space unavailable" announce>
        {error || "This event could not be found."}
        <Button onClick={() => void refresh()}>Try again</Button>
      </Message>
    );
  return (
    <>
      <ButtonLink variant="ghost" href={`/events/${id}`}>
        Back to event
      </ButtonLink>
      <div className="page-intro">
        <span className="eyebrow">A thoughtful first draft</span>
        <h1>Bring your celebration to life.</h1>
        <p>
          Describe {event.title.toLowerCase()} in your own words. Review the
          details, then shape a plan that feels like you.
        </p>
      </div>
      {error && (
        <div ref={notice} tabIndex={-1}>
          <Message tone="error" title="This step needs attention" announce>
            {error}
          </Message>
        </div>
      )}
      {status?.provider === "test_fixture" && (
        <Message title="Test fixture">
          These responses are isolated test data, not live AI output.
        </Message>
      )}
      {!status?.enabled && (
        <Message title="AI planning is not configured">
          Your saved drafts remain available. Set the backend OpenAI model and
          credentials to enable new generation.
        </Message>
      )}
      {event.status === "archived" && (
        <Message title="Archived event">
          Saved drafts are available to read. New generation and editing are
          disabled.
        </Message>
      )}
      {status?.enabled && event.status !== "archived" && (
        <Card>
          <h2>Tell us what you have in mind.</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run("intake", { description, consent: true });
            }}
          >
            <TextAreaField
              label="Describe your event"
              required
              minLength={10}
              maxLength={6000}
              rows={6}
              value={description}
              disabled={busy}
              onChange={(e) => setDescription(e.target.value)}
              hint="Include the date, duration, location, guests, budget and anything that would make it special. Missing details will become questions."
            />
            <label className="consent-check">
              <input
                type="checkbox"
                required
                checked={consent}
                disabled={busy}
                onChange={(e) => setConsent(e.target.checked)}
              />
              <span>
                Send this description and relevant event details to OpenAI to
                draft suggestions. Avoid guest names, contacts and other private
                information.
              </span>
            </label>
            <Button
              type="submit"
              disabled={!consent}
              loading={busy}
              loadingLabel="Working on your request..."
            >
              Extract event details
            </Button>
            <p className="caption">
              Requests have a time limit of {status.timeout_seconds} seconds and
              at most one automatic retry. Review every suggestion.
            </p>
          </form>
        </Card>
      )}
      {busy && (
        <LoadingState label="Considering the details. Your existing plans remain safe..." />
      )}
      <div ref={review} tabIndex={-1} className="planning-result">
        {extraction && (
          <IntakeReview
            key={reviewKey}
            initial={extraction}
            busy={busy}
            onGenerate={(details) =>
              void run("generations", {
                details: {
                  ...details,
                  preferences: details.preferences
                    .map((v) => v.trim())
                    .filter(Boolean),
                  constraints: details.constraints
                    .map((v) => v.trim())
                    .filter(Boolean),
                },
                confirmed: true,
                consent: true,
              })
            }
          />
        )}
        {selected && (
          <PlanEditor
            key={selected.id}
            initial={selected}
            editable={
              event.status !== "archived" &&
              selected.base_event_revision === event.revision
            }
            onSaved={(plan) => {
              setSelected(plan);
              void refresh();
            }}
          />
        )}
      </div>
      <section className="section-block" aria-labelledby="drafts-heading">
        <div className="section-heading">
          <h2 id="drafts-heading">Your saved drafts</h2>
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => void refresh()}
          >
            Check recent results
          </Button>
        </div>
        <p className="section-description">
          Generated drafts are saved automatically after validation. Your
          reviewed edits are saved separately with the Save reviewed plan
          button.
        </p>
        {!plans.length && (
          <p>
            No drafts yet. Your first plan will appear here after a successful
            generation.
          </p>
        )}
        <div className="event-grid">
          {plans.map((plan) => (
            <Card key={plan.id}>
              <Badge>
                {plan.saved_at ? "Reviewed and saved" : "Needs review"}
              </Badge>
              <h3>
                <ButtonLink
                  variant="ghost"
                  href={`/events/${id}/plans/${plan.id}`}
                >
                  {plan.title} · Draft {plan.sequence}
                </ButtonLink>
              </h3>
              <p className="caption">
                {plan.warnings.length > 1
                  ? "Check this draft's warnings before using it."
                  : "Planning estimates, ready for your review."}
              </p>
            </Card>
          ))}
        </div>
        {nextBefore && (
          <Button
            variant="secondary"
            onClick={() =>
              void api<PlanPage>(`/events/${id}/plans?before=${nextBefore}`)
                .then((p) => {
                  setPlans((old) => [...old, ...p.items]);
                  setNextBefore(p.next_before);
                })
                .catch((e: unknown) => setError(errorMessage(e)))
            }
          >
            Load older drafts
          </Button>
        )}
        {runs.length > 0 && (
          <details className="recent-runs">
            <summary>Recent planning requests</summary>
            <ul>
              {runs.map((r) => (
                <li key={r.id}>
                  {r.operation === "intake" ? "Intake" : "Draft generation"}:{" "}
                  {r.status}. {r.call_count} model{" "}
                  {r.call_count === 1 ? "call" : "calls"}
                  {r.latency_ms != null
                    ? `, ${(r.latency_ms / 1000).toFixed(1)} seconds`
                    : ""}
                  .
                  {r.error_code && (
                    <span>
                      {" "}
                      {failureMessages[r.error_code] ?? "Please try again."}
                    </span>
                  )}
                  {r.plan_id && (
                    <ButtonLink
                      variant="ghost"
                      href={`/events/${id}/plans/${r.plan_id}`}
                    >
                      Open draft
                    </ButtonLink>
                  )}
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>
    </>
  );
}

export function PlanningWorkspace({ id }: { id: string }) {
  return (
    <RequireAccount>
      <Workspace id={id} />
    </RequireAccount>
  );
}

function LoadedPlan({ id, planId }: { id: string; planId: string }) {
  const [data, setData] = useState<{ event: EventRead; plan: PlanRead } | null>(
      null,
    ),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      api<EventRead>(`/events/${id}`, { signal: controller.signal }),
      api<PlanRead>(`/events/${id}/plans/${planId}`, {
        signal: controller.signal,
      }),
    ])
      .then(([event, plan]) => {
        if (!controller.signal.aborted) setData({ event, plan });
      })
      .catch((e: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(e));
      });
    return () => controller.abort();
  }, [id, planId]);
  return (
    <>
      <ButtonLink href={`/events/${id}/planning`} variant="ghost">
        Back to planning
      </ButtonLink>
      {error ? (
        <Message tone="error" title="Draft unavailable" announce>
          {error}
        </Message>
      ) : !data ? (
        <LoadingState label="Loading your draft..." />
      ) : (
        <>
          <div className="page-intro">
            <span className="eyebrow">Draft {data.plan.sequence}</span>
            <h1>{data.plan.title}</h1>
            <p>Suggestions to shape together. All costs are estimates.</p>
          </div>
          <PlanEditor
            initial={data.plan}
            editable={
              data.event.status !== "archived" &&
              data.plan.base_event_revision === data.event.revision
            }
            onSaved={(plan) => setData({ ...data, plan })}
          />
        </>
      )}
    </>
  );
}
export function PlanScreen({ id, planId }: { id: string; planId: string }) {
  return (
    <RequireAccount>
      <LoadedPlan id={id} planId={planId} />
    </RequireAccount>
  );
}
