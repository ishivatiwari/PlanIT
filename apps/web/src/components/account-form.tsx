"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, errorMessage } from "@/lib/api";
import type { AccountSession } from "@/lib/api-types";
import { useAuth } from "./auth-provider";
import { Button, ButtonLink } from "./ui/button";
import { Card } from "./ui/card";
import { TextField } from "./ui/field";
import { Message } from "./ui/feedback";

export function AccountForm({ register = false }: { register?: boolean }) {
  const auth = useAuth(),
    router = useRouter();
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const form = useRef<HTMLFormElement>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setFields({});
    try {
      const session = await api<AccountSession>(
        register ? "/auth/register" : "/auth/login",
        {
          method: "POST",
          data: {
            username,
            password,
            ...(register ? { display_name: name } : {}),
          },
        },
      );
      setPassword("");
      auth.accept(session);
      router.replace("/events");
    } catch (failure) {
      setError(errorMessage(failure));
      if (failure instanceof ApiError)
        setFields(
          Object.fromEntries(
            failure.fields.map((field) => [field.path, field.message]),
          ),
        );
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
  if (auth.session)
    return (
      <div className="page-intro">
        <h1>You&apos;re signed in.</h1>
        <p>Welcome, {auth.session.user.display_name}.</p>
        <ButtonLink href="/events">Go to my events</ButtonLink>
      </div>
    );
  return (
    <div className="account-page">
      <div className="page-intro">
        <span className="eyebrow">A place for your celebrations</span>
        <h1>{register ? "Make yourself at home." : "Welcome back."}</h1>
        <p>
          {register
            ? "Create your account to keep your event details together."
            : "Sign in to pick up where you left off."}
        </p>
      </div>
      <Card>
        <form className="sample-form" ref={form} onSubmit={submit}>
          {register && (
            <TextField
              label="Your name"
              required
              autoComplete="name"
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
              error={fields.display_name}
            />
          )}
          <TextField
            label="Username"
            required
            autoComplete="username"
            minLength={3}
            maxLength={32}
            pattern="[A-Za-z0-9_]+"
            hint="3-32 letters, numbers, or underscores. Usernames are not case-sensitive."
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            error={fields.username}
          />
          <TextField
            label="Password"
            type="password"
            required
            autoComplete={register ? "new-password" : "current-password"}
            minLength={15}
            maxLength={128}
            hint="Use a passphrase of 15-128 characters. Spaces are preserved."
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={fields.password}
          />
          {error && (
            <div tabIndex={-1} role="alert">
              <Message
                tone="error"
                title={register ? "Account not created" : "Could not sign in"}
              >
                {error}
              </Message>
            </div>
          )}
          <Button
            type="submit"
            loading={busy}
            loadingLabel={register ? "Creating account..." : "Signing in..."}
          >
            {register ? "Create account" : "Sign in"}
          </Button>
          <p className="caption">
            {register ? "Already have an account?" : "New to PlanIT?"}{" "}
            <ButtonLink
              variant="ghost"
              href={register ? "/sign-in" : "/register"}
            >
              {register ? "Sign in" : "Create an account"}
            </ButtonLink>
          </p>
          {register && (
            <p className="caption">
              Keep your password safe. Password recovery is not available in
              this local version.
            </p>
          )}
        </form>
      </Card>
    </div>
  );
}
