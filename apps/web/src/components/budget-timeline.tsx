"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { formatMoney, parseMinor } from "@/lib/money";
import { RequireAccount } from "./auth-provider";
import { Button, ButtonLink } from "./ui/button";
import { Card } from "./ui/card";
import { LoadingState, Message } from "./ui/feedback";
import { SelectField, TextAreaField, TextField } from "./ui/field";

type Currency = "INR" | "USD" | "EUR" | "GBP" | "JPY";
type Summary = {
  currency: Currency;
  ceiling_minor: number | null;
  estimated_minor: number;
  planned_minor: number;
  actual_minor: number;
  reserve_minor: number;
  remaining_minor: number | null;
  projected_overrun_minor: number;
  scenario: string;
  savings_alternatives: string[];
  category_totals: { category: string; planned_minor: number }[];
};
type Event = {
  title: string;
  currency: Currency;
  revision: number;
  status: string;
};
type Task = {
  id: string;
  title: string;
  status: string;
  owner: string;
  priority: string;
  due_at: string | null;
  critical: boolean;
  delayed: boolean;
};

export function BudgetTimeline({ eventId }: { eventId: string }) {
  const [event, setEvent] = useState<Event | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [scenario, setScenario] = useState("balanced");
  const [loading, setLoading] = useState(true);
  const [budget, setBudget] = useState({
    category: "",
    description: "",
    estimated: "",
    planned: "",
    actual: "",
  });
  const [task, setTask] = useState({
    title: "",
    owner: "",
    priority: "normal",
    dueAt: "",
    description: "",
  });
  const [saving, setSaving] = useState<"budget" | "task" | string | null>(null);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [loadedEvent, loadedSummary, loadedTasks] = await Promise.all([
        api<Event>(`/events/${eventId}`),
        api<Summary>(`/events/${eventId}/budget?scenario=${scenario}`),
        api<Task[]>(`/events/${eventId}/timeline`),
      ]);
      setEvent(loadedEvent);
      setSummary(loadedSummary);
      setTasks(loadedTasks);
      setError("");
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setLoading(false);
    }
  }, [eventId, scenario]);
  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  async function addBudget(submission: FormEvent<HTMLFormElement>) {
    submission.preventDefault();
    if (!event || !summary) return;
    try {
      setSaving("budget");
      await api(`/events/${eventId}/budget/items?scenario=${scenario}`, {
        method: "POST",
        revision: event.revision,
        data: {
          category: budget.category,
          description: budget.description,
          estimated_minor: parseMinor(budget.estimated, summary.currency) ?? 0,
          planned_minor: parseMinor(budget.planned, summary.currency) ?? 0,
          actual_minor: parseMinor(budget.actual, summary.currency) ?? 0,
          scenario,
        },
      });
      setBudget({
        category: "",
        description: "",
        estimated: "",
        planned: "",
        actual: "",
      });
      await refresh();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(null);
    }
  }

  async function addTask(submission: FormEvent<HTMLFormElement>) {
    submission.preventDefault();
    if (!event) return;
    try {
      setSaving("task");
      await api(`/events/${eventId}/timeline/tasks`, {
        method: "POST",
        revision: event.revision,
        data: {
          title: task.title,
          owner: task.owner,
          priority: task.priority,
          description: task.description,
          due_at: task.dueAt ? new Date(task.dueAt).toISOString() : null,
        },
      });
      setTask({
        title: "",
        owner: "",
        priority: "normal",
        dueAt: "",
        description: "",
      });
      await refresh();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(null);
    }
  }

  return (
    <RequireAccount>
      {loading ? (
        <LoadingState label="Opening deterministic budget and timeline..." />
      ) : (
        <main className="workspace-main">
          <ButtonLink href={`/events/${eventId}`} variant="ghost">
            Back to event
          </ButtonLink>
          <div className="page-intro event-page-heading">
            <div>
              <p className="eyebrow">Deterministic planning</p>
              <h1>{event?.title}</h1>
              <p className="section-description">
                Persisted budget totals and task deadlines. Values are
                recalculated by the server.
              </p>
            </div>
            <div className="button-row">
              <ButtonLink
                href={`/api/v1/events/${eventId}/export?format=markdown`}
                variant="secondary"
              >
                Export plan &amp; checklist
              </ButtonLink>
              <ButtonLink
                href={`/api/v1/events/${eventId}/export?format=json`}
                variant="ghost"
              >
                Export JSON
              </ButtonLink>
            </div>
          </div>
          {error && (
            <Message tone="error" title="Could not load planning data" announce>
              {error}
            </Message>
          )}
          <div className="planning-columns">
            <Card>
              <div className="card-heading">
                <h2>Budget {summary?.currency}</h2>
                <label>
                  Scenario
                  <select
                    value={scenario}
                    onChange={(e) => setScenario(e.target.value)}
                  >
                    <option value="economical">Economical</option>
                    <option value="balanced">Balanced</option>
                    <option value="premium">Premium</option>
                  </select>
                </label>
              </div>
              {summary && (
                <>
                  <dl className="metric-list">
                    <div>
                      <dt>Estimated</dt>
                      <dd>
                        {formatMoney(summary.estimated_minor, summary.currency)}
                      </dd>
                    </div>
                    <div>
                      <dt>Planned</dt>
                      <dd>
                        {formatMoney(summary.planned_minor, summary.currency)}
                      </dd>
                    </div>
                    <div>
                      <dt>Actual</dt>
                      <dd>
                        {formatMoney(summary.actual_minor, summary.currency)}
                      </dd>
                    </div>
                    <div>
                      <dt>Reserve</dt>
                      <dd>
                        {formatMoney(summary.reserve_minor, summary.currency)}
                      </dd>
                    </div>
                    <div>
                      <dt>
                        {summary.projected_overrun_minor
                          ? "Projected overrun"
                          : "Remaining"}
                      </dt>
                      <dd>
                        {formatMoney(
                          summary.projected_overrun_minor ||
                            summary.remaining_minor ||
                            0,
                          summary.currency,
                        )}
                      </dd>
                    </div>
                  </dl>
                  <h3>Planned by category</h3>
                  <div
                    className="budget-bars"
                    aria-label="Planned budget by category"
                  >
                    {summary.category_totals.map((item) => {
                      const max = Math.max(
                        ...summary.category_totals.map(
                          (entry) => entry.planned_minor,
                        ),
                        1,
                      );
                      return (
                        <div className="budget-bar-row" key={item.category}>
                          <span>{item.category}</span>
                          <span className="budget-bar-track">
                            <span
                              className="budget-bar-fill"
                              style={{
                                width: `${Math.round((item.planned_minor / max) * 100)}%`,
                              }}
                            />
                          </span>
                          <strong>
                            {formatMoney(item.planned_minor, summary.currency)}
                          </strong>
                        </div>
                      );
                    })}
                  </div>
                  {summary.savings_alternatives.map((alternative) => (
                    <p className="notice" key={alternative}>
                      {alternative}
                    </p>
                  ))}
                </>
              )}
            </Card>
            <Card>
              <h2>Timeline and run sheet</h2>
              {tasks.length === 0 ? (
                <p>
                  No persisted tasks yet. Generated preparation suggestions
                  remain in the draft until you add them here.
                </p>
              ) : (
                <ul className="task-list">
                  {tasks.map((task) => (
                    <li key={task.id}>
                      <strong>{task.title}</strong>
                      <span>
                        {task.status} · {task.priority}
                        {task.owner && ` · ${task.owner}`}
                      </span>
                      {task.due_at && (
                        <time>{new Date(task.due_at).toLocaleString()}</time>
                      )}
                      {task.delayed && <b>Delayed</b>}
                      {task.critical && <b>Critical</b>}
                    </li>
                  ))}
                </ul>
              )}
              <Button onClick={() => void refresh()}>
                Refresh persisted data
              </Button>
            </Card>
          </div>
          {event?.status !== "archived" && (
            <section
              className="planning-columns"
              aria-label="Add budget and timeline records"
            >
              <Card>
                <form className="plan-form" onSubmit={addBudget}>
                  <h2>Add budget line</h2>
                  <p className="section-description">
                    Amounts are recorded in {summary?.currency} and recalculated
                    on the server.
                  </p>
                  <div className="form-grid">
                    <TextField
                      required
                      label="Category"
                      value={budget.category}
                      onChange={(e) =>
                        setBudget({ ...budget, category: e.target.value })
                      }
                      placeholder="Catering"
                    />
                    <TextField
                      required
                      label="Description"
                      value={budget.description}
                      onChange={(e) =>
                        setBudget({ ...budget, description: e.target.value })
                      }
                      placeholder="Dinner service"
                    />
                    <TextField
                      label="Estimated"
                      inputMode="decimal"
                      value={budget.estimated}
                      onChange={(e) =>
                        setBudget({ ...budget, estimated: e.target.value })
                      }
                    />
                    <TextField
                      label="Planned"
                      inputMode="decimal"
                      value={budget.planned}
                      onChange={(e) =>
                        setBudget({ ...budget, planned: e.target.value })
                      }
                    />
                    <TextField
                      label="Actual"
                      inputMode="decimal"
                      value={budget.actual}
                      onChange={(e) =>
                        setBudget({ ...budget, actual: e.target.value })
                      }
                    />
                  </div>
                  <Button
                    type="submit"
                    loading={saving === "budget"}
                    loadingLabel="Adding budget line..."
                  >
                    Add budget line
                  </Button>
                </form>
              </Card>
              <Card>
                <form className="plan-form" onSubmit={addTask}>
                  <h2>Add timeline task</h2>
                  <p className="section-description">
                    Deadlines must occur before the event begins.
                  </p>
                  <div className="form-grid">
                    <TextField
                      required
                      label="Task"
                      value={task.title}
                      onChange={(e) =>
                        setTask({ ...task, title: e.target.value })
                      }
                      placeholder="Confirm caterer"
                    />
                    <TextField
                      label="Owner"
                      value={task.owner}
                      onChange={(e) =>
                        setTask({ ...task, owner: e.target.value })
                      }
                      placeholder="Asha"
                    />
                    <SelectField
                      label="Priority"
                      value={task.priority}
                      onChange={(e) =>
                        setTask({ ...task, priority: e.target.value })
                      }
                    >
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </SelectField>
                    <TextField
                      label="Due by"
                      type="datetime-local"
                      value={task.dueAt}
                      onChange={(e) =>
                        setTask({ ...task, dueAt: e.target.value })
                      }
                    />
                  </div>
                  <TextAreaField
                    label="Details"
                    value={task.description}
                    onChange={(e) =>
                      setTask({ ...task, description: e.target.value })
                    }
                    placeholder="Useful context for this task"
                  />
                  <Button
                    type="submit"
                    loading={saving === "task"}
                    loadingLabel="Adding task..."
                  >
                    Add task
                  </Button>
                </form>
              </Card>
            </section>
          )}
        </main>
      )}
    </RequireAccount>
  );
}
