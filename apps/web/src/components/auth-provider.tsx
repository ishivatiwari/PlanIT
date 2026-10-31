"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { AccountSession } from "@/lib/api-types";
import { api, ApiError, errorMessage } from "@/lib/api";
import { Button, ButtonLink } from "./ui/button";
import { LoadingState, Message } from "./ui/feedback";

type AuthState = {
  status: "loading" | "signed-in" | "signed-out" | "error";
  session: AccountSession | null;
  error: string;
};
type AuthContext = AuthState & {
  refresh: () => Promise<void>;
  accept: (session: AccountSession) => void;
  signOut: () => Promise<void>;
};
const Context = createContext<AuthContext | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    status: "loading",
    session: null,
    error: "",
  });
  const version = useRef(0);
  const [broadcastId] = useState(() => crypto.randomUUID());
  const accept = useCallback(
    (session: AccountSession) => {
      version.current++;
      setState({ status: "signed-in", session, error: "" });
      const channel = new BroadcastChannel("eventora-session");
      channel.postMessage({ source: broadcastId });
      channel.close();
    },
    [broadcastId],
  );
  const refresh = useCallback(() => {
    const started = version.current;
    return api<AccountSession>("/me")
      .then((session) => {
        if (started !== version.current) return;
        version.current++;
        setState({ status: "signed-in", session, error: "" });
      })
      .catch((error: unknown) => {
        if (started !== version.current) return;
        version.current++;
        setState({
          status:
            error instanceof ApiError && error.status === 401
              ? "signed-out"
              : "error",
          session: null,
          error: errorMessage(error),
        });
      });
  }, []);
  useEffect(() => {
    void refresh();
    const invalidate = () => {
      version.current++;
      setState({ status: "signed-out", session: null, error: "" });
    };
    const channel = new BroadcastChannel("eventora-session");
    channel.onmessage = (event: MessageEvent<{ source?: string }>) => {
      if (event.data?.source !== broadcastId) invalidate();
    };
    window.addEventListener("eventora:unauthorized", invalidate);
    return () => {
      // Invalidate async requests using the latest counter; this is not a DOM ref.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      version.current++;
      channel.close();
      window.removeEventListener("eventora:unauthorized", invalidate);
    };
  }, [refresh, broadcastId]);
  async function signOut() {
    if (!state.session) return;
    try {
      await api<void>("/auth/logout", {
        method: "POST",
        data: {},
        csrf: state.session.csrf_token,
      });
    } catch (failure) {
      if (!(failure instanceof ApiError && failure.status === 401))
        throw failure;
    }
    version.current++;
    setState({ status: "signed-out", session: null, error: "" });
    const channel = new BroadcastChannel("eventora-session");
    channel.postMessage({ source: broadcastId });
    channel.close();
  }
  return (
    <Context.Provider value={{ ...state, refresh, accept, signOut }}>
      {children}
    </Context.Provider>
  );
}

export function useAuth() {
  const context = useContext(Context);
  if (!context) throw new Error("AuthProvider is required");
  return context;
}

export function RequireAccount({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  if (auth.status === "loading")
    return <LoadingState label="Checking your session..." />;
  if (auth.status === "error")
    return (
      <Message tone="error" title="We could not check your account">
        <p>{auth.error}</p>
        <Button variant="secondary" onClick={() => void auth.refresh()}>
          Try again
        </Button>
      </Message>
    );
  if (!auth.session)
    return (
      <div className="page-intro">
        <span className="eyebrow">Your own planning space</span>
        <h1>Your celebrations, together.</h1>
        <p>
          Sign in to create events and keep your details safely in your
          workspace.
        </p>
        <div className="button-row">
          <ButtonLink href="/sign-in">Sign in</ButtonLink>
          <ButtonLink href="/register" variant="secondary">
            Create an account
          </ButtonLink>
        </div>
      </div>
    );
  // A different account must never reuse the previous account's component state.
  return <div key={auth.session.user.id}>{children}</div>;
}

export function AccountControls() {
  const auth = useAuth();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  if (!auth.session)
    return (
      <ButtonLink href="/sign-in" variant="ghost">
        Sign in
      </ButtonLink>
    );
  return (
    <div className="account-controls">
      <span className="account-name">{auth.session.user.display_name}</span>
      <Button
        variant="ghost"
        loading={busy}
        loadingLabel="Signing out..."
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            await auth.signOut();
          } catch (failure) {
            setError(errorMessage(failure));
          } finally {
            setBusy(false);
          }
        }}
      >
        Sign out
      </Button>
      {error && (
        <span role="alert" className="account-error">
          {error}
        </span>
      )}
    </div>
  );
}
