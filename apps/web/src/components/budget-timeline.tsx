"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { EventRead as Event, TaskRead as Task } from "@/lib/api-types";
import { formatMoney, parseMinor } from "@/lib/money";
import { RequireAccount, useAuth } from "./auth-provider";
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

export function BudgetTimeline({ eventId }: { eventId: string }) {
  return (
    <RequireAccount>
      <BudgetTimelineContent key={eventId} eventId={eventId} />
    </RequireAccount>
  );
}

function BudgetTimelineContent({ eventId }: { eventId: string }) {
  const { session } = useAuth();
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
  const [saving, setSaving] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const largestCategory = Math.max(
    ...(summary?.category_totals.map((item) => item.planned_minor) ?? []),
    1,
  );
  const refresh = useCallback(
    async (
      scope: "all" | "event" | "timeline" = "all",
      selectedScenario = "balanced",
      signal?: AbortSignal,
    ) => {
      try {
        const [loadedEvent, loadedSummary, loadedTasks] = await Promise.all([
          api<Event>(`/events/${eventId}`, { signal }),
          scope === "all"
            ? api<Summary>(
                `/events/${eventId}/budget?scenario=${selectedScenario}`,
                { signal },
              )
            : undefined,
          scope !== "event"
            ? api<Task[]>(`/events/${eventId}/timeline`, { signal })
            : undefined,
        ]);
        if (signal?.aborted) return;
        setEvent(loadedEvent);
        if (loadedSummary) setSummary(loadedSummary);
        if (loadedTasks) setTasks(loadedTasks);
        setError("");
      } catch (failure) {
        if (!signal?.aborted) setError(errorMessage(failure));
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [eventId],
  );
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(
      () => void refresh("all", "balanced", controller.signal),
      0,
    );
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [refresh]);

  async function changeScenario(selected: string) {
    if (saving) return;
    setSaving("scenario");
    setNotice("");
    try {
      const loaded = await api<Summary>(
        `/events/${eventId}/budget?scenario=${selected}`,
      );
      setSummary(loaded);
      setScenario(selected);
      setError("");
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(null);
    }
  }

  async function addBudget(submission: FormEvent<HTMLFormElement>) {
    submission.preventDefault();
    if (!event || !summary || !session || saving) return;
    try {
      setSaving("budget");
      setNotice("");
      const savedSummary = await api<Summary>(
        `/events/${eventId}/budget/items?scenario=${scenario}`,
        {
          method: "POST",
          csrf: session.csrf_token,
          revision: event.revision,
          data: {
            category: budget.category,
            description: budget.description,
            estimated_minor:
              parseMinor(budget.estimated, summary.currency) ?? 0,
            planned_minor: parseMinor(budget.planned, summary.currency) ?? 0,
            actual_minor: parseMinor(budget.actual, summary.currency) ?? 0,
            scenario,
          },
        },
      );
      setBudget({
        category: "",
        description: "",
        estimated: "",
        planned: "",
        actual: "",
      });
      setSummary(savedSummary);
      await refresh("event");
      setNotice("Budget line saved.");
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(null);
    }
  }

  async function addTask(submission: FormEvent<HTMLFormElement>) {
    submission.preventDefault();
    if (!event || !session || saving) return;
    try {
      setSaving("task");
      setNotice("");
      await api(`/events/${eventId}/timeline/tasks`, {
        method: "POST",
        csrf: session.csrf_token,
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
      await refresh("timeline");
      setNotice("Timeline task saved.");
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(null);
    }
  }

  async function updateTask(taskId: string, status: string) {
    if (!event || !session || saving) return;
    setSaving(taskId);
    setNotice("");
    try {
      await api(`/events/${eventId}/timeline/tasks/${taskId}`, {
        method: "PATCH",
        csrf: session.csrf_token,
        revision: event.revision,
        data: { status },
      });
      await refresh("timeline");
      setNotice("Task progress saved.");
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(null);
    }
  }

  return (
    <>
      {loading ? (
        <LoadingState label="Opening deterministic budget and timeline..." />
      ) : (
        <div className="workspace-main">
          <ButtonLink href={`/events/${eventId}`} variant="ghost">
            Back to event
          </ButtonLink>
          <div className="page-intro event-page-heading">
            <div>
              <p className="eyebrow">Deterministic planning</p>
              <h1>{event?.title ?? "Budget and timeline"}</h1>
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
            <Message tone="error" title="Planning needs attention" announce>
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
                    disabled={saving !== null}
                    onChange={(e) => void changeScenario(e.target.value)}
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
                            summary.remaining_minor,
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
                      return (
                        <div className="budget-bar-row" key={item.category}>
                          <span>{item.category}</span>
                          <span className="budget-bar-track">
                            <span
                              className="budget-bar-fill"
                              style={{
                                width: `${Math.round((item.planned_minor / largestCategory) * 100)}%`,
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
                      {event?.status !== "archived" && (
                        <SelectField
                          label={`Progress for ${task.title}`}
                          value={task.status}
                          disabled={saving !== null}
                          onChange={(e) =>
                            void updateTask(task.id, e.target.value)
                          }
                        >
                          <option value="todo">To do</option>
                          <option value="in_progress">In progress</option>
                          <option value="done">Done</option>
                          <option value="cancelled">Cancelled</option>
                        </SelectField>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <Button
                disabled={saving !== null}
                onClick={() => void refresh("all", scenario)}
              >
                Refresh persisted data
              </Button>
            </Card>
          </div>
          {notice && <Message tone="success" title={notice} announce />}
          {event && summary && event.status !== "archived" && (
            <section
              className="planning-columns"
              aria-label="Add budget and timeline records"
            >
              <Card>
                <form className="plan-form" onSubmit={addBudget}>
                  <fieldset disabled={saving !== null}>
                    <h2>Add budget line</h2>
                    <p className="section-description">
                      Amounts are recorded in {summary?.currency} and
                      recalculated on the server.
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
                  </fieldset>
                </form>
              </Card>
              <Card>
                <form className="plan-form" onSubmit={addTask}>
                  <fieldset disabled={saving !== null}>
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
                        hint="Enter the deadline in your device's local timezone."
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
                  </fieldset>
                </form>
              </Card>
            </section>
          )}
        </div>
      )}
    </>
  );
}
