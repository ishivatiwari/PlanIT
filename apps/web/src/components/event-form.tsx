"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { EventRead, EventWrite } from "@/lib/api-types";
import { currencies, minorInput, parseMinor, type Currency } from "@/lib/money";
import { useAuth } from "./auth-provider";
import { Button, ButtonLink } from "./ui/button";
import { Card } from "./ui/card";
import { SelectField, TextAreaField, TextField } from "./ui/field";
import { Message } from "./ui/feedback";

const needsChoice = (value: string | null | undefined) =>
  value == null ? "unknown" : value ? "details" : "none";

export function EventForm({
  event,
  type = "wedding",
}: {
  event?: EventRead;
  type?: EventWrite["event_type"];
}) {
  const auth = useAuth(),
    router = useRouter(),
    form = useRef<HTMLFormElement>(null);
  const [title, setTitle] = useState(event?.title ?? "");
  const [eventType, setEventType] = useState(event?.event_type ?? type);
  const [timezone, setTimezone] = useState(event?.timezone ?? "Asia/Kolkata");
  const [currency, setCurrency] = useState<Currency>(event?.currency ?? "INR");
  const [start, setStart] = useState(event?.start_local ?? ""),
    [end, setEnd] = useState(event?.end_local ?? "");
  const [startFold, setStartFold] = useState(
      event?.start_fold == null ? "" : String(event.start_fold),
    ),
    [endFold, setEndFold] = useState(
      event?.end_fold == null ? "" : String(event.end_fold),
    );
  const [location, setLocation] = useState(event?.location ?? ""),
    [guests, setGuests] = useState(event?.guest_count?.toString() ?? "");
  const [budget, setBudget] = useState(
    minorInput(event?.budget_ceiling_minor ?? null, event?.currency ?? "INR"),
  );
  const [preferences, setPreferences] = useState(
    event?.preferences.join("\n") ?? "",
  );
  const [dietaryChoice, setDietaryChoice] = useState(
      needsChoice(event?.dietary_needs),
    ),
    [accessChoice, setAccessChoice] = useState(
      needsChoice(event?.accessibility_needs),
    );
  const [dietary, setDietary] = useState(event?.dietary_needs ?? ""),
    [accessibility, setAccessibility] = useState(
      event?.accessibility_needs ?? "",
    );
  const [status, setStatus] = useState<EventWrite["status"]>(
    event && event.status !== "archived" ? event.status : "draft",
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [conflict, setConflict] = useState(false);
  async function submit(submission: FormEvent) {
    submission.preventDefault();
    if (!auth.session) return;
    setError("");
    setFields({});
    setBusy(true);
    setConflict(false);
    try {
      let amount: number | null;
      try {
        amount = parseMinor(budget, currency);
      } catch (failure) {
        throw new ApiError(422, "Check the budget amount.", [
          { path: "budget_ceiling_minor", message: errorMessage(failure) },
        ]);
      }
      if (
        guests &&
        (!/^\d+$/.test(guests) ||
          Number(guests) < 1 ||
          Number(guests) > 1000000)
      )
        throw new ApiError(422, "Check the guest count.", [
          {
            path: "guest_count",
            message: "Enter a whole number from 1 to 1,000,000.",
          },
        ]);
      const payload: EventWrite = {
        title,
        event_type: eventType,
        timezone,
        currency,
        start_local: start || null,
        end_local: end || null,
        start_fold: startFold === "" ? null : startFold === "1" ? 1 : 0,
        end_fold: endFold === "" ? null : endFold === "1" ? 1 : 0,
        location: location || null,
        guest_count: guests ? Number(guests) : null,
        budget_ceiling_minor: amount,
        preferences: preferences
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
        dietary_needs:
          dietaryChoice === "unknown"
            ? null
            : dietaryChoice === "none"
              ? ""
              : dietary,
        accessibility_needs:
          accessChoice === "unknown"
            ? null
            : accessChoice === "none"
              ? ""
              : accessibility,
        status,
      };
      const saved = await api<EventRead>(
        event ? `/events/${event.id}` : "/events",
        {
          method: event ? "PATCH" : "POST",
          data: payload,
          csrf: auth.session.csrf_token,
          revision: event?.revision,
        },
      );
      router.push(`/events/${saved.id}`);
    } catch (failure) {
      setError(errorMessage(failure));
      if (failure instanceof ApiError) {
        setFields(
          Object.fromEntries(
            failure.fields.map((field) => [field.path, field.message]),
          ),
        );
        setConflict(failure.status === 412);
      }
      requestAnimationFrame(() =>
        (
          form.current?.querySelector<HTMLElement>('[aria-invalid="true"]') ??
          form.current?.querySelector<HTMLElement>("[role=alert]")
        )?.focus(),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-intro">
        <span className="eyebrow">
          {event ? "Make room for the details" : "Start something memorable"}
        </span>
        <h1>{event ? "Edit your event." : "A celebration of your own."}</h1>
        <p>
          Start with a name and an occasion. You can save an incomplete draft
          and return when you know more.
        </p>
      </div>
      <form ref={form} onSubmit={submit} className="event-form">
        {error && (
          <div role="alert" tabIndex={-1}>
            <Message tone="error" title="Your event was not saved">
              <p>{error}</p>
              {fields.form && <p>{fields.form}</p>}
              {conflict && (
                <p>
                  Your entries are still here.{" "}
                  <ButtonLink href={`/events/${event?.id}`} variant="secondary">
                    View latest event
                  </ButtonLink>
                </p>
              )}
            </Message>
          </div>
        )}
        <Card>
          <fieldset disabled={busy}>
            <legend>01 / The essentials</legend>
            <div className="form-grid">
              <TextField
                label="Event name"
                required
                maxLength={160}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                error={fields.title}
              />
              <SelectField
                label="Event type"
                required
                value={eventType}
                onChange={(e) =>
                  setEventType(e.target.value as EventWrite["event_type"])
                }
                error={fields.event_type}
              >
                <option value="wedding">Wedding</option>
                <option value="birthday">Birthday</option>
                <option value="community">Community event</option>
              </SelectField>
              <TextField
                label="Location"
                maxLength={300}
                hint="A venue, neighborhood, or city. You can decide later."
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                error={fields.location}
              />
              <SelectField
                label="Event status"
                value={status}
                onChange={(e) =>
                  setStatus(e.target.value as EventWrite["status"])
                }
                hint="Confirmed/completed events need the date, location, guest count, budget and needs responses."
                error={fields.status}
              >
                <option value="draft">Draft</option>
                <option value="confirmed">Confirmed</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </SelectField>
            </div>
          </fieldset>
        </Card>
        <Card>
          <fieldset disabled={busy}>
            <legend>02 / When & where</legend>
            <div className="form-grid">
              <TextField
                label="Start date and time"
                type="datetime-local"
                step="any"
                value={start}
                onChange={(e) => {
                  setStart(e.target.value);
                  setStartFold("");
                }}
                error={fields.start_local}
              />
              <TextField
                label="End date and time"
                type="datetime-local"
                step="any"
                value={end}
                onChange={(e) => {
                  setEnd(e.target.value);
                  setEndFold("");
                }}
                error={fields.end_local}
              />
              <div className="form-span">
                <TextField
                  label="Timezone"
                  required
                  list="event-timezones"
                  maxLength={64}
                  hint="Dates and times above are local to this IANA timezone, not your device timezone."
                  value={timezone}
                  onChange={(e) => {
                    setTimezone(e.target.value);
                    setStartFold("");
                    setEndFold("");
                  }}
                  error={fields.timezone}
                />
                <datalist id="event-timezones">
                  <option value="Asia/Kolkata" />
                  <option value="UTC" />
                  <option value="Europe/London" />
                  <option value="America/New_York" />
                  <option value="Asia/Singapore" />
                </datalist>
              </div>
            </div>
            <details className="time-options">
              <summary>Daylight-saving time options</summary>
              <p className="caption">
                Only needed if the clocks move back and your chosen time occurs
                twice. Leave automatic for ordinary dates.
              </p>
              <div className="form-grid">
                <SelectField
                  label="Start time occurrence"
                  value={startFold}
                  onChange={(e) => setStartFold(e.target.value)}
                >
                  <option value="">Automatic</option>
                  <option value="0">First occurrence</option>
                  <option value="1">Second occurrence</option>
                </SelectField>
                <SelectField
                  label="End time occurrence"
                  value={endFold}
                  onChange={(e) => setEndFold(e.target.value)}
                >
                  <option value="">Automatic</option>
                  <option value="0">First occurrence</option>
                  <option value="1">Second occurrence</option>
                </SelectField>
              </div>
            </details>
          </fieldset>
        </Card>
        <Card>
          <fieldset disabled={busy}>
            <legend>03 / People & budget</legend>
            <div className="form-grid">
              <TextField
                label="Guest count"
                inputMode="numeric"
                maxLength={7}
                value={guests}
                onChange={(e) => setGuests(e.target.value)}
                hint="Leave blank if you have not decided."
                error={fields.guest_count}
              />
              <SelectField
                label="Currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value as Currency)}
                hint="Changing currency keeps the entered amount; no conversion is performed."
                error={fields.currency}
              >
                {currencies.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </SelectField>
              <div className="form-span">
                <TextField
                  label="Budget ceiling"
                  inputMode="decimal"
                  maxLength={20}
                  hint={`Your maximum budget in ${currency}. ${currency === "JPY" ? "Whole amounts only." : "Up to two decimal places, without commas."} Leave blank if undecided; zero is allowed.`}
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  error={fields.budget_ceiling_minor}
                />
              </div>
            </div>
          </fieldset>
        </Card>
        <Card>
          <fieldset disabled={busy}>
            <legend>04 / Make everyone feel welcome</legend>
            <div className="form-grid">
              <SelectField
                label="Dietary needs"
                value={dietaryChoice}
                onChange={(e) => setDietaryChoice(e.target.value)}
                error={fields.dietary_needs}
              >
                <option value="unknown">Not decided yet</option>
                <option value="none">No dietary needs</option>
                <option value="details">Record dietary needs</option>
              </SelectField>
              <SelectField
                label="Accessibility needs"
                value={accessChoice}
                onChange={(e) => setAccessChoice(e.target.value)}
                error={fields.accessibility_needs}
              >
                <option value="unknown">Not decided yet</option>
                <option value="none">No accessibility needs</option>
                <option value="details">Record accessibility needs</option>
              </SelectField>
              {dietaryChoice === "details" && (
                <TextAreaField
                  label="Dietary details"
                  required
                  maxLength={2000}
                  value={dietary}
                  onChange={(e) => setDietary(e.target.value)}
                  error={fields.dietary_needs}
                />
              )}{" "}
              {accessChoice === "details" && (
                <TextAreaField
                  label="Accessibility details"
                  required
                  maxLength={2000}
                  value={accessibility}
                  onChange={(e) => setAccessibility(e.target.value)}
                  error={fields.accessibility_needs}
                />
              )}
              <div className="form-span">
                <TextAreaField
                  label="Preferences"
                  hint="One preference per line, up to 20. Keep each under 120 characters."
                  maxLength={2420}
                  rows={4}
                  value={preferences}
                  onChange={(e) => setPreferences(e.target.value)}
                  error={fields.preferences}
                />
              </div>
            </div>
          </fieldset>
        </Card>
        <div className="form-actions">
          <Button type="submit" loading={busy} loadingLabel="Saving event...">
            {event ? "Save changes" : "Create event"}
          </Button>
          <ButtonLink
            variant="ghost"
            href={event ? `/events/${event.id}` : "/events"}
          >
            Cancel
          </ButtonLink>
          <span className="caption">
            Your details are saved to your account when you submit.
          </span>
        </div>
      </form>
    </>
  );
}
