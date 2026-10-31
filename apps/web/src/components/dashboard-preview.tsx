"use client";

import { useRef, useState } from "react";
import { CelebrationArt } from "./celebration-art";
import { Icon, type IconName } from "./icon";
import { Button, ButtonLink } from "./ui/button";
import { Badge, Card } from "./ui/card";
import { DashboardEvents } from "./event-workspace";

const occasions: {
  name: string;
  description: string;
  icon: IconName;
  detail: string;
}[] = [
  {
    name: "Wedding",
    description: "A day that's unmistakably yours.",
    icon: "heart",
    detail: "From a quiet ceremony to a room full of loved ones.",
  },
  {
    name: "Birthday",
    description: "Make another year memorable.",
    icon: "calendar",
    detail: "Small surprises, big milestones, and everything in between.",
  },
  {
    name: "Community",
    description: "Bring your people together.",
    icon: "people",
    detail: "Shared tables, familiar faces, and new connections.",
  },
];

export function DashboardPreview() {
  const [selected, setSelected] = useState<string | null>(null);
  const firstOption = useRef<HTMLInputElement>(null);
  const occasion = occasions.find((item) => item.name === selected);

  return (
    <>
      <div className="page-kicker">
        <span>
          <Icon name="grid" /> Your celebration workspace
        </span>
        <span className="edition">Room for something wonderful</span>
      </div>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <span className="hero-label">
            <Icon name="spark" /> Every good gathering starts somewhere.
          </span>
          <h1 id="hero-title">
            Good things
            <br />
            start with <em>a plan.</em>
          </h1>
          <p>
            Big milestones. Small gatherings. A thoughtful home for the moments
            that matter to you.
          </p>
          <ButtonLink href="#occasions">
            Choose a celebration <Icon name="arrow" />
          </ButtonLink>
          <p className="hero-footnote">
            A first look at your future planning space.
          </p>
        </div>
        <CelebrationArt />
      </section>
      <section
        id="occasions"
        className="section-block"
        aria-labelledby="occasion-title"
      >
        <div className="section-heading">
          <div>
            <span className="eyebrow">Start with the occasion</span>
            <h2 id="occasion-title">What brings you together?</h2>
          </div>
          <Badge>Explore the preview</Badge>
        </div>
        <fieldset
          className="occasion-fieldset"
          aria-describedby="occasion-hint"
        >
          <legend className="sr-only">Choose an event type</legend>
          <p className="section-description" id="occasion-hint">
            Choose a type to explore this workspace. No event is created or
            saved.
          </p>
          <div className="occasion-grid">
            {occasions.map((item) => (
              <label
                key={item.name}
                className={`occasion-card ${selected === item.name ? "occasion-card--selected" : ""}`}
              >
                <input
                  ref={
                    item.name === occasions[0].name ? firstOption : undefined
                  }
                  className="sr-only"
                  type="radio"
                  name="occasion"
                  value={item.name}
                  checked={selected === item.name}
                  onChange={() => setSelected(item.name)}
                />
                <span className="occasion-top">
                  <span className="occasion-icon">
                    <Icon name={item.icon} />
                  </span>
                  <span className="radio-mark" aria-hidden="true">
                    {selected === item.name && <Icon name="check" />}
                  </span>
                </span>
                <strong>{item.name}</strong>
                <span className="occasion-description">{item.description}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="selection-feedback">
          <p role="status" aria-live="polite">
            {selected
              ? `${selected} selected for preview. Nothing has been saved.`
              : "Your selection stays here until you leave or reload this page."}
          </p>
          {selected && (
            <Button
              variant="ghost"
              onClick={() => {
                setSelected(null);
                firstOption.current?.focus();
              }}
            >
              Clear selection
            </Button>
          )}
        </div>
      </section>
      <div className="dashboard-grid">
        <section aria-labelledby="events-title">
          <div className="section-heading">
            <h2 id="events-title">Your next occasion</h2>
            <Badge>Occasion preview</Badge>
          </div>
          <Card className="empty-events">
            <span className="empty-icon">
              <Icon name={occasion?.icon ?? "calendar"} />
            </span>
            <h3>
              {occasion
                ? `${occasion.name} preview`
                : "A little space for your next big moment."}
            </h3>
            <p>
              {occasion?.detail ??
                "Your celebrations will have a home here. For now, take a look around and choose an occasion above."}
            </p>
            <span className="empty-caption">
              {occasion
                ? "Preview only. No event has been created."
                : "Choose an occasion above, or start from My events."}
            </span>
            {occasion && (
              <ButtonLink
                href={`/events/new?type=${occasion.name.toLowerCase()}`}
              >
                Continue with {occasion.name}
              </ButtonLink>
            )}
          </Card>
        </section>
        <aside className="intention-card" aria-labelledby="intention-title">
          <span className="eyebrow">The PlanIT idea</span>
          <h2 id="intention-title">
            More moments.
            <br />
            <em>Fewer moving parts.</em>
          </h2>
          <p>
            A calm place to bring your celebration together, one thoughtful
            detail at a time.
          </p>
          <div className="intention-line">
            <Icon name="heart" />
            <span>Made around what matters to you</span>
          </div>
          <div className="intention-line">
            <Icon name="shield" />
            <span>Clear choices, at your own pace</span>
          </div>
        </aside>
      </div>
      <DashboardEvents />
    </>
  );
}
