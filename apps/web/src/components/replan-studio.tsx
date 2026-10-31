"use client";

import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { PlanDocument } from "@/lib/api-types";
import { RequireAccount, useAuth } from "./auth-provider";
import { formatMoney, parseMinor, type Currency } from "@/lib/money";
import { TextField } from "./ui/field";
import { Button, ButtonLink } from "./ui/button";
import { Card } from "./ui/card";
import { LoadingState, Message } from "./ui/feedback";

type Event = {
  title: string;
  revision: number;
  currency: Currency;
  status: string;
};
type Proposal = {
  id: string;
  change_type: string;
  impact: Record<string, unknown>;
  alternative: PlanDocument;
  status: string;
  accepted_plan_id: string | null;
};
export function ReplanStudio({ eventId }: { eventId: string }) {
  return (
    <RequireAccount>
      <ReplanContent key={eventId} eventId={eventId} />
    </RequireAccount>
  );
}

function ReplanContent({ eventId }: { eventId: string }) {
  const { session } = useAuth();
  const [saving, setSaving] = useState(false);
  const [category, setCategory] = useState("Catering");
  const [taskId, setTaskId] = useState("");
  const [tasks, setTasks] = useState<{ id: string; title: string }[]>([]);
  const [event, setEvent] = useState<Event | null>(null);
  const [kind, setKind] = useState("guest_count");
  const [value, setValue] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try {
      const [loadedEvent, loadedTasks] = await Promise.all([
        api<Event>(`/events/${eventId}`),
        api<{ id: string; title: string }[]>(`/events/${eventId}/timeline`),
      ]);
      setEvent(loadedEvent);
      setTasks(loadedTasks);
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [eventId]);
  useEffect(() => {
    const t = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(t);
  }, [refresh]);
  async function propose() {
    if (!event || !session || saving) return;
    setSaving(true);
    try {
      if (!value.trim())
        throw new Error("Enter a change detail before analysing the impact.");
      const details =
        kind === "guest_count"
          ? { guest_count: Number(value) }
          : kind === "budget_constraint"
            ? { budget_ceiling_minor: parseMinor(value, event.currency) }
            : kind === "quote_increase"
              ? { category, increase_minor: parseMinor(value, event.currency) }
              : kind === "date_change"
                ? { start_local: value }
                : kind === "task_delay"
                  ? { task_id: taskId, delay_days: Number(value) }
                  : { note: value };
      setProposal(
        await api<Proposal>(`/events/${eventId}/replans`, {
          method: "POST",
          csrf: session.csrf_token,
          revision: event.revision,
          data: { change_type: kind, details },
        }),
      );
      setMessage("");
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }
  async function close(action: "approve" | "reject") {
    if (!proposal || !event || !session || saving) return;
    setSaving(true);
    try {
      setProposal(
        await api<Proposal>(
          `/events/${eventId}/replans/${proposal.id}/${action}`,
          {
            method: "POST",
            csrf: session.csrf_token,
            revision: event.revision,
            data: {},
          },
        ),
      );
      await refresh();
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      {loading ? (
        <LoadingState label="Opening adaptive replanning..." />
      ) : (
        <div className="workspace-main">
          <ButtonLink href={`/events/${eventId}`} variant="ghost">
            Back to event
          </ButtonLink>
          <p className="eyebrow">Adaptive replanning</p>
          <h1>{event?.title ?? "Replanning"}</h1>
          <p className="section-description">
            Every proposal starts from the current authorized plan. Review the
            impact and trade-offs before accepting it.
          </p>
          {message && (
            <Message tone="error" title="Replanning needs attention" announce>
              {message}
            </Message>
          )}
          <Card className="replan-card">
            <form
              className="plan-form"
              onSubmit={(submission) => {
                submission.preventDefault();
                void propose();
              }}
            >
              <fieldset
                disabled={saving || !event || event.status === "archived"}
              >
                <h2>Describe a change</h2>
                <label>
                  Scenario
                  <select
                    value={kind}
                    onChange={(e) => {
                      setKind(e.target.value);
                      setValue("");
                    }}
                  >
                    <option value="guest_count">Guest count change</option>
                    <option value="venue_change">
                      Venue cancellation or replacement
                    </option>
                    <option value="quote_increase">
                      Vendor quote increase
                    </option>
                    <option value="date_change">Event date change</option>
                    <option value="task_delay">Task delay</option>
                    <option value="budget_constraint">
                      New budget constraint
                    </option>
                  </select>
                </label>
                {kind === "quote_increase" && (
                  <TextField
                    label="Budget category"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  />
                )}
                {kind === "task_delay" && (
                  <label>
                    Delayed task
                    <select
                      value={taskId}
                      onChange={(e) => setTaskId(e.target.value)}
                    >
                      <option value="">Choose a task</option>
                      {tasks.map((task) => (
                        <option key={task.id} value={task.id}>
                          {task.title}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {(kind === "budget_constraint" ||
                  kind === "quote_increase") && (
                  <p>Enter an amount in {event?.currency}, without commas.</p>
                )}
                <label>
                  Change detail
                  <input
                    type={kind === "date_change" ? "datetime-local" : "text"}
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    placeholder={
                      kind === "guest_count"
                        ? "New guest count"
                        : "Amount or note"
                    }
                  />
                </label>
                <Button type="submit" loading={saving}>
                  Analyse impact
                </Button>
              </fieldset>
            </form>
          </Card>
          {proposal && (
            <Card className="replan-card">
              <h2>Before and after review</h2>
              <p>Status: {proposal.status}</p>
              <dl className="metric-list">
                <div>
                  <dt>Previous allocation</dt>
                  <dd>
                    {event &&
                      formatMoney(
                        Number(proposal.impact.before_total_minor),
                        event.currency,
                      )}
                  </dd>
                </div>
                <div>
                  <dt>Proposed allocation</dt>
                  <dd>
                    {event &&
                      formatMoney(
                        Number(proposal.impact.after_total_minor),
                        event.currency,
                      )}
                  </dd>
                </div>
              </dl>
              {["affected", "warnings", "assumptions", "tradeoffs"].map(
                (key) => (
                  <div key={key}>
                    <h3>
                      {key === "tradeoffs"
                        ? "Trade-offs"
                        : key.charAt(0).toUpperCase() + key.slice(1)}
                    </h3>
                    <ul>
                      {(Array.isArray(proposal.impact[key])
                        ? (proposal.impact[key] as string[])
                        : []
                      ).map((text, index) => (
                        <li key={index}>{text}</li>
                      ))}
                    </ul>
                  </div>
                ),
              )}
              <h3>Proposed alternative</h3>
              <p>{proposal.alternative.summary}</p>
              <ul>
                {proposal.alternative.budget_categories.map((item, index) => (
                  <li key={index}>
                    {item.category}:{" "}
                    {event &&
                      formatMoney(item.estimated_amount_minor, event.currency)}
                    {" — "}
                    {item.description}
                  </li>
                ))}
              </ul>
              <p>
                These are estimates. Completed work and the prior version remain
                preserved.
              </p>
              {proposal.status === "pending" && (
                <div>
                  <Button
                    disabled={saving || event?.status === "archived"}
                    onClick={() => void close("approve")}
                  >
                    Accept proposed changes
                  </Button>{" "}
                  <Button
                    disabled={saving || event?.status === "archived"}
                    onClick={() => void close("reject")}
                    variant="ghost"
                  >
                    Reject proposal
                  </Button>
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </>
  );
}
