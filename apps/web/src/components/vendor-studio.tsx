"use client";

import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { formatMoney, type Currency } from "@/lib/money";
import { RequireAccount } from "./auth-provider";
import { ButtonLink } from "./ui/button";
import { Card } from "./ui/card";
import { LoadingState, Message } from "./ui/feedback";

type Quote = {
  amount_minor: number;
  currency: Currency;
  status: string;
  provenance: string;
  inclusions: string[];
  availability_evidence: string | null;
  deposit_minor: number | null;
};
type Vendor = {
  id: string;
  name: string;
  category: string;
  location: string;
  provenance: string;
  source_label: string;
  service_inclusions: string[];
  availability_evidence: string | null;
  cancellation_terms: string | null;
  deposit_minor: number | null;
  quotes: Quote[];
};

export function VendorStudio({ eventId }: { eventId: string }) {
  return (
    <RequireAccount>
      <VendorContent key={eventId} eventId={eventId} />
    </RequireAccount>
  );
}

function VendorContent({ eventId }: { eventId: string }) {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("name");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError("");
      void api<Vendor[]>(
        `/events/${eventId}/vendors?sort=${sort}${category ? `&category=${encodeURIComponent(category)}` : ""}`,
        { signal: controller.signal },
      )
        .then(setVendors)
        .catch((e) => {
          if (!controller.signal.aborted) setError(errorMessage(e));
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [eventId, sort, category]);
  return (
    <>
      {loading ? (
        <LoadingState label="Opening vendor comparison..." />
      ) : (
        <div className="workspace-main">
          <ButtonLink href={`/events/${eventId}`} variant="ghost">
            Back to event
          </ButtonLink>
          <p className="eyebrow">Personalization studio</p>
          <h1>Vendors and requirements</h1>
          <p className="section-description">
            Compare records you supplied or intentionally seeded for
            demonstration. Unknown availability stays unknown.
          </p>
          {error && (
            <Message tone="error" title="Could not load vendors" announce>
              {error}
            </Message>
          )}
          <div className="filter-row">
            <label>
              Category
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All categories</option>
                {[
                  "venue",
                  "catering",
                  "decor",
                  "photography",
                  "entertainment",
                  "other",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Sort
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="name">Name</option>
                <option value="category">Category</option>
                <option value="price">Lowest supplied quote</option>
              </select>
            </label>
          </div>
          <div className="planning-columns">
            {vendors.map((v) => (
              <Card key={v.id}>
                <div className="card-heading">
                  <h2>{v.name}</h2>
                  <span className="badge">
                    {v.provenance === "demo_seeded"
                      ? "Demonstration data"
                      : v.provenance.replace("_", " ")}
                  </span>
                </div>
                <p>
                  {v.category} · {v.location || "Location unknown"}
                </p>
                <p className="muted">Source: {v.source_label}</p>
                <h3>Service inclusions</h3>
                <ul>
                  {(v.service_inclusions.length
                    ? v.service_inclusions
                    : ["Unknown"]
                  ).map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
                <h3>Quotes</h3>
                {v.quotes.length ? (
                  v.quotes.map((q, i) => (
                    <div key={i} className="notice">
                      {formatMoney(q.amount_minor, q.currency)} · {q.status} ·{" "}
                      {q.provenance}
                      {q.availability_evidence
                        ? ` · Evidence: ${q.availability_evidence}`
                        : " · Availability unknown"}
                    </div>
                  ))
                ) : (
                  <p>Quote unknown.</p>
                )}
              </Card>
            ))}
            {vendors.length === 0 && (
              <Card>
                <p>
                  No vendor records yet. Add user-provided or clearly labeled
                  demonstration records through the API.
                </p>
              </Card>
            )}
          </div>
        </div>
      )}
    </>
  );
}
