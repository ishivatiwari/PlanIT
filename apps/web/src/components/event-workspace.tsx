"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { EventPage, EventRead } from "@/lib/api-types";
import { formatMoney } from "@/lib/money";
import { RequireAccount, useAuth } from "./auth-provider";
import { EventForm } from "./event-form";
import { Icon } from "./icon";
import { Button, ButtonLink } from "./ui/button";
import { Badge, Card } from "./ui/card";
import { Dialog } from "./ui/dialog";
import { SelectField } from "./ui/field";
import { LoadingState, Message } from "./ui/feedback";

export function eventDate(event: EventRead) {
  return event.starts_at
    ? new Intl.DateTimeFormat("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: event.timezone,
      }).format(new Date(event.starts_at))
    : "Date to be decided";
}

function EventCards({
  filter = "active",
  compact = false,
}: {
  filter?: string;
  compact?: boolean;
}) {
  const [events, setEvents] = useState<EventRead[]>([]),
    [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true),
    [more, setMore] = useState(false),
    [error, setError] = useState("");
  const load = useCallback(
    (next?: string, signal?: AbortSignal) => {
      return api<EventPage>(
        `/events?status=${filter}&limit=${compact ? 3 : 12}${next ? `&cursor=${encodeURIComponent(next)}` : ""}`,
        { signal },
      )
        .then((data) => {
          if (signal?.aborted) return;
          setEvents((previous) =>
            next ? [...previous, ...data.items] : data.items,
          );
          setCursor(data.next_cursor);
          setError("");
        })
        .catch((failure: unknown) => {
          if (!signal?.aborted) setError(errorMessage(failure));
        })
        .finally(() => {
          if (!signal?.aborted) {
            setLoading(false);
            setMore(false);
          }
        });
    },
    [compact, filter],
  );
  useEffect(() => {
    const controller = new AbortController();
    void load(undefined, controller.signal);
    return () => controller.abort();
  }, [load]);
  if (loading) return <LoadingState label="Loading your events..." />;
  return (
    <>
      {error && (
        <Message tone="error" title="Events could not be loaded" announce>
          <p>{error}</p>
          <Button
            variant="secondary"
            onClick={() => {
              setLoading(true);
              void load();
            }}
          >
            Try again
          </Button>
        </Message>
      )}
      {!error && !events.length && (
        <Card className="empty-events">
          <span className="empty-icon">
            <Icon name="calendar" />
          </span>
          <h3>
            {filter === "archived"
              ? "No archived events."
              : "Your next celebration starts here."}
          </h3>
          <p>
            {filter === "archived"
              ? "Events you archive will stay available here as read-only records."
              : "Create an event, save the details you know, and return when the rest takes shape."}
          </p>
          {filter !== "archived" && (
            <ButtonLink href="/events/new">Create your first event</ButtonLink>
          )}
        </Card>
      )}
      <div className="event-grid">
        {events.map((event) => (
          <Card key={event.id} className="event-card">
            <div className="status-card-top">
              <span className="occasion-icon">
                <Icon
                  name={
                    event.event_type === "wedding"
                      ? "heart"
                      : event.event_type === "birthday"
                        ? "calendar"
                        : "people"
                  }
                />
              </span>
              <Badge>{event.status}</Badge>
            </div>
            <h3>
              <ButtonLink variant="ghost" href={`/events/${event.id}`}>
                {event.title}
              </ButtonLink>
            </h3>
            <p>{eventDate(event)}</p>
            <p className="event-location">
              {event.location || "Location to be decided"}
            </p>
            <div className="event-card-facts">
              <span>
                {event.guest_count == null
                  ? "Guests undecided"
                  : `${event.guest_count.toLocaleString("en-IN")} guests`}
              </span>
              <span>
                {formatMoney(event.budget_ceiling_minor, event.currency)}
              </span>
            </div>
          </Card>
        ))}
      </div>
      {!compact && cursor && (
        <div className="list-more">
          <Button
            variant="secondary"
            loading={more}
            loadingLabel="Loading more..."
            onClick={() => {
              setMore(true);
              void load(cursor);
            }}
          >
            Load more events
          </Button>
        </div>
      )}
      {!compact && events.length > 0 && (
        <p className="caption">
          {events.length} {events.length === 1 ? "event" : "events"} shown.
        </p>
      )}
    </>
  );
}

function EventList() {
  const [filter, setFilter] = useState("active");
  return (
    <>
      <div className="page-intro event-page-heading">
        <div>
          <span className="eyebrow">All your moments, in one place</span>
          <h1>My events</h1>
          <p>
            Your saved celebrations, from first ideas to finished gatherings.
          </p>
        </div>
        <ButtonLink href="/events/new">
          Create event <Icon name="arrow" />
        </ButtonLink>
      </div>
      <div className="event-toolbar">
        <SelectField
          label="Show events"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="active">Current events</option>
          <option value="archived">Archived events</option>
          <option value="all">All events</option>
        </SelectField>
      </div>
      <EventCards key={filter} filter={filter} />
    </>
  );
}

export function EventsWorkspace() {
  return (
    <RequireAccount>
      <EventList />
    </RequireAccount>
  );
}

export function DashboardEvents() {
  const auth = useAuth();
  return (
    <section className="section-block" aria-labelledby="saved-events">
      <div className="section-heading">
        <h2 id="saved-events">Your events</h2>
        <ButtonLink href="/events" variant="ghost">
          View all events <Icon name="arrow" />
        </ButtonLink>
      </div>
      {auth.session ? (
        <EventCards key={auth.session.user.id} compact />
      ) : (
        <Card>
          <h3>A home for the moments that matter.</h3>
          <p className="section-description">
            Sign in to create and manage your saved events.
          </p>
          <ButtonLink href="/sign-in" variant="secondary">
            Sign in to your workspace
          </ButtonLink>
        </Card>
      )}
    </section>
  );
}

function LoadedEvent({ id, edit }: { id: string; edit: boolean }) {
  const auth = useAuth();
  const [event, setEvent] = useState<EventRead | null>(null),
    [error, setError] = useState("");
  const [loading, setLoading] = useState(true),
    [archiveOpen, setArchiveOpen] = useState(false),
    [archiving, setArchiving] = useState(false),
    [archiveError, setArchiveError] = useState("");
  const [notice, setNotice] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (notice) heading.current?.focus();
  }, [notice]);
  const load = useCallback(
    (signal?: AbortSignal) => {
      return api<EventRead>(`/events/${encodeURIComponent(id)}`, { signal })
        .then((data) => {
          if (signal?.aborted) return;
          setEvent(data);
          setError("");
        })
        .catch((failure: unknown) => {
          if (!signal?.aborted) setError(errorMessage(failure));
        })
        .finally(() => {
          if (!signal?.aborted) setLoading(false);
        });
    },
    [id],
  );
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);
  if (loading) return <LoadingState label="Loading your event..." />;
  if (error || !event)
    return (
      <>
        <div className="page-intro">
          <h1>We couldn&apos;t open this event.</h1>
        </div>
        <Message tone="error" title="Event unavailable" announce>
          {error || "This event could not be found."}
        </Message>
        <div className="button-row section-block">
          <ButtonLink href="/events">Back to my events</ButtonLink>
          <Button
            variant="secondary"
            onClick={() => {
              setLoading(true);
              void load();
            }}
          >
            Try again
          </Button>
        </div>
      </>
    );
  if (edit && event.status !== "archived") return <EventForm event={event} />;
  async function archive() {
    if (!event || !auth.session) return;
    setArchiving(true);
    setArchiveError("");
    try {
      setEvent(
        await api<EventRead>(`/events/${event.id}/archive`, {
          method: "POST",
          data: {},
          csrf: auth.session.csrf_token,
          revision: event.revision,
        }),
      );
      setArchiveOpen(false);
      setNotice("Event archived. Its saved details remain available here.");
    } catch (failure) {
      setArchiveError(errorMessage(failure));
    } finally {
      setArchiving(false);
    }
  }
  return (
    <>
      <ButtonLink variant="ghost" href="/events">
        Back to my events
      </ButtonLink>
      <div className="page-intro event-page-heading">
        <div>
          <span className="eyebrow">
            {event.event_type === "community"
              ? "Community event"
              : event.event_type}
          </span>
          <h1 ref={heading} tabIndex={-1}>
            {event.title}
          </h1>
          <Badge>{event.status}</Badge>
        </div>
        {event.status !== "archived" && (
          <div className="button-row">
            <ButtonLink href={`/events/${event.id}/edit`}>
              Edit event
            </ButtonLink>
            <ButtonLink
              href={`/events/${event.id}/planning`}
              variant="secondary"
            >
              Plan with AI
            </ButtonLink>
            <Button variant="secondary" onClick={() => setArchiveOpen(true)}>
              Archive
            </Button>
          </div>
        )}
      </div>
      {notice && (
        <Message tone="success" title="Event archived" announce>
          {notice}
        </Message>
      )}
      {event.status === "archived" && (
        <p className="section-description">
          This event is archived and read-only.
        </p>
      )}
      <div className="detail-grid">
        <Card>
          <h2>At a glance</h2>
          <dl className="detail-list">
            <div>
              <dt>Starts</dt>
              <dd>{eventDate(event)}</dd>
            </div>
            <div>
              <dt>Ends</dt>
              <dd>
                {event.ends_at
                  ? new Intl.DateTimeFormat("en-IN", {
                      dateStyle: "medium",
                      timeStyle: "short",
                      timeZone: event.timezone,
                    }).format(new Date(event.ends_at))
                  : "Not set"}
              </dd>
            </div>
            <div>
              <dt>Timezone</dt>
              <dd>{event.timezone}</dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>{event.location || "Not decided"}</dd>
            </div>
            <div>
              <dt>Guest count</dt>
              <dd>
                {event.guest_count?.toLocaleString("en-IN") ?? "Not decided"}
              </dd>
            </div>
            <div>
              <dt>Budget ceiling</dt>
              <dd>{formatMoney(event.budget_ceiling_minor, event.currency)}</dd>
            </div>
          </dl>
        </Card>
        <Card>
          <h2>A welcoming gathering</h2>
          <dl className="detail-list">
            <div>
              <dt>Dietary needs</dt>
              <dd>
                {event.dietary_needs === null
                  ? "Not decided"
                  : event.dietary_needs || "No dietary needs"}
              </dd>
            </div>
            <div>
              <dt>Accessibility needs</dt>
              <dd>
                {event.accessibility_needs === null
                  ? "Not decided"
                  : event.accessibility_needs || "No accessibility needs"}
              </dd>
            </div>
            <div>
              <dt>Preferences</dt>
              <dd>
                {event.preferences.length ? (
                  <ul>
                    {event.preferences.map((value, index) => (
                      <li key={index}>{value}</li>
                    ))}
                  </ul>
                ) : (
                  "No preferences recorded"
                )}
              </dd>
            </div>
          </dl>
        </Card>
      </div>
      <p className="caption">
        <ButtonLink variant="ghost" href={`/events/${event.id}/planning`}>
          View planning drafts
        </ButtonLink>
        <ButtonLink variant="ghost" href={`/events/${event.id}/vendors`}>
          Vendor studio
        </ButtonLink>
        <ButtonLink variant="ghost" href={`/events/${event.id}/replan`}>
          Replan a change
        </ButtonLink>
        <ButtonLink variant="ghost" href={`/events/${event.id}/budget`}>
          Budget & timeline
        </ButtonLink>
        Draft suggestions are estimates. Vendor services and bookings are not
        enabled.
      </p>
      <Dialog
        open={archiveOpen}
        dismissible={!archiving}
        onClose={() => {
          if (!archiving) setArchiveOpen(false);
        }}
        title="Archive this event?"
        description="Your saved details will remain available in Archived events, as a read-only record."
      >
        <p>{event.title}</p>
        {archiveError && (
          <Message tone="error" title="Event was not archived" announce>
            {archiveError}
          </Message>
        )}
        <div className="dialog-actions button-row">
          <Button
            variant="secondary"
            disabled={archiving}
            onClick={() => setArchiveOpen(false)}
          >
            Keep event
          </Button>
          <Button
            loading={archiving}
            loadingLabel="Archiving..."
            onClick={() => void archive()}
          >
            Archive event
          </Button>
        </div>
      </Dialog>
    </>
  );
}

export function EventScreen({
  id,
  edit = false,
}: {
  id: string;
  edit?: boolean;
}) {
  return (
    <RequireAccount>
      <LoadedEvent key={`${id}:${edit}`} id={id} edit={edit} />
    </RequireAccount>
  );
}
