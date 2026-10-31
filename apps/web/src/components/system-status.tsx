"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "./icon";
import { Button } from "./ui/button";
import { Badge, Card } from "./ui/card";
import { useAuth } from "./auth-provider";
import { api } from "@/lib/api";
import type { AIStatus } from "@/lib/api-types";

type State = { api: boolean; database: boolean; checked: string | null };

async function probe(
  name: "live" | "ready",
  signal: AbortSignal,
): Promise<boolean> {
  const response = await fetch(`/api/v1/health/${name}`, {
    cache: "no-store",
    signal,
  });
  if (!response.ok) return false;
  const body: unknown = await response.json();
  return (
    typeof body === "object" &&
    body !== null &&
    "status" in body &&
    body.status === (name === "live" ? "ok" : "ready")
  );
}

export function SystemStatus() {
  const [state, setState] = useState<State>({
    api: false,
    database: false,
    checked: null,
  });
  const [checking, setChecking] = useState(true);
  const active = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    const timeout = setTimeout(() => controller.abort(), 6500);
    const results = await Promise.allSettled([
      probe("live", controller.signal),
      probe("ready", controller.signal),
    ]);
    clearTimeout(timeout);
    if (active.current !== controller) return;
    setState({
      api: results[0].status === "fulfilled" && results[0].value,
      database: results[1].status === "fulfilled" && results[1].value,
      checked: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    });
    setChecking(false);
  }, []);

  useEffect(() => {
    void refresh();
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [refresh]);

  const summary = checking
    ? "Checking your connection…"
    : state.api && state.database
      ? "Your foundation is connected."
      : "A connection needs attention.";

  return (
    <section
      id="system-status"
      className="system-section"
      aria-labelledby="system-title"
    >
      <div className="section-heading">
        <div>
          <span className="eyebrow">A strong start</span>
          <h2 id="system-title">A little check behind the scenes.</h2>
        </div>
        <Button
          variant="secondary"
          onClick={() => {
            setChecking(true);
            void refresh();
          }}
          loading={checking}
          loadingLabel="Checking..."
        >
          <Icon name="refresh" />
          Check again
        </Button>
      </div>
      <p className="status-summary" role="status" aria-live="polite">
        {summary}
      </p>
      <div className="status-grid">
        <StatusCard
          title="Application API"
          description="The connection that brings your workspace to life."
          label={
            checking ? "Checking" : state.api ? "Connected" : "Unavailable"
          }
          tone={checking ? "neutral" : state.api ? "good" : "warning"}
          icon="layers"
        />
        <StatusCard
          title="Database readiness"
          description="Checks the database connection and migration baseline."
          label={
            checking
              ? "Checking"
              : state.database
                ? "Ready"
                : state.api
                  ? "Not ready"
                  : "Unverified"
          }
          tone={checking ? "neutral" : state.database ? "good" : "warning"}
          icon="grid"
        />
        <AIStatusCard />
      </div>
      <p className="check-note">
        {state.checked ? `Last checked at ${state.checked}. ` : ""}
        {!checking && (!state.api || !state.database)
          ? "Start the API and database, run migrations, then check again. Your connection status is never simulated."
          : "Live connection checks. No event or personal data is sent."}
      </p>
    </section>
  );
}

function AIStatusCard() {
  const auth = useAuth();
  const [state, setState] = useState<AIStatus | null>(null);
  const userId = auth.session?.user.id;
  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    void api<AIStatus>("/ai/status", { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setState(data);
      })
      .catch(() => {
        if (!controller.signal.aborted) setState(null);
      });
    return () => controller.abort();
  }, [userId]);
  return (
    <StatusCard
      title="AI planning"
      label={
        !userId
          ? "Sign in to check"
          : state
            ? state.enabled
              ? "Configured"
              : "Not enabled"
            : "Unverified"
      }
      description={
        !userId
          ? "Sign in to check AI configuration and open an event's planning space."
          : state?.enabled
            ? "Generate an editable draft from reviewed details. Provider availability is checked when you make a request."
            : "Saved plans remain available. New generation needs a configured model and backend API key."
      }
      tone="neutral"
      icon="spark"
    />
  );
}

function StatusCard({
  title,
  description,
  label,
  tone,
  icon,
}: {
  title: string;
  description: string;
  label: string;
  tone: "good" | "warning" | "neutral";
  icon: "layers" | "grid" | "spark";
}) {
  return (
    <Card className="status-card">
      <div className="status-card-top">
        <span className="status-icon">
          <Icon name={icon} />
        </span>
        <Badge tone={tone}>
          <span className="status-dot" />
          {label}
        </Badge>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
    </Card>
  );
}
