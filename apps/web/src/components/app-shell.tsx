"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import Image from "next/image";
import { Icon } from "./icon";
import { Navigation } from "./navigation";
import { Button } from "./ui/button";
import { Badge } from "./ui/card";
import { Dialog } from "./ui/dialog";
import { AccountControls } from "./auth-provider";

function Brand() {
  return (
    <Link href="/" className="brand" aria-label="PlanIT home">
      <Image
        className="brand-logo"
        src="/planit-logo.png"
        alt="PlanIT"
        width={232}
        height={232}
        priority
      />
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const title =
    pathname === "/"
      ? "Overview"
      : pathname === "/design-system"
        ? "Design system"
        : pathname === "/system-status"
          ? "System status"
          : pathname.startsWith("/events")
            ? "My events"
            : "Account";

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <Brand />
        <Navigation pathname={pathname} />
        <div className="sidebar-note">
          <Icon name="spark" />
          <p>
            More presence.
            <br />
            <em>Less planning in circles.</em>
          </p>
        </div>
        <div className="workspace-label">
          <span className="workspace-avatar" aria-hidden="true">
            E
          </span>
          <div>
            <strong>Your workspace</strong>
            <span>A thoughtful beginning</span>
          </div>
        </div>
      </aside>
      <div className="app-frame">
        <header className="app-header">
          <div className="header-location">
            <Button
              variant="ghost"
              className="menu-button icon-button"
              aria-label="Open navigation"
              aria-expanded={menuOpen}
              aria-haspopup="dialog"
              onClick={() => setMenuOpen(true)}
            >
              <Icon name="menu" />
            </Button>
            <span className="breadcrumb-parent">Workspace</span>
            <Icon name="chevron" />
            <span>{title}</span>
          </div>
          <div className="header-actions">
            <Badge>Local workspace</Badge>
            <AccountControls />
            <Button
              variant="ghost"
              className="about-button"
              onClick={() => setAboutOpen(true)}
              aria-label="About this workspace"
            >
              <Icon name="info" />
              <span>About</span>
            </Button>
          </div>
        </header>
        <main id="main" tabIndex={-1} className="workspace-content">
          {children}
        </main>
        <footer className="app-footer">
          <span>Made for the moments that matter.</span>
          <span>
            PlanIT <span aria-hidden="true">·</span> Your celebration workspace
          </span>
        </footer>
      </div>
      <Dialog
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        title="Navigation"
        className="navigation-dialog"
      >
        <Navigation pathname={pathname} onNavigate={() => setMenuOpen(false)} />
      </Dialog>
      <Dialog
        open={aboutOpen}
        onClose={() => setAboutOpen(false)}
        title="A thoughtful beginning"
        description="Welcome to your PlanIT workspace."
      >
        <p>
          Create an account to save, edit, and archive your events. Your event
          details are stored in your own workspace. Occasion previews and the
          design-system examples remain temporary until you leave or reload.
        </p>
        <p>
          AI intake and draft planning are available within an event when
          configured. Vendor evidence, deterministic budgets/timelines, and
          adaptive replanning are available; live vendor integrations and
          bookings are not enabled. Nothing here books a service or sends a
          message. Creating an event saves the details you submit; it does not
          generate a plan.
        </p>
        <div className="dialog-actions">
          <Button onClick={() => setAboutOpen(false)}>Got it</Button>
        </div>
      </Dialog>
    </>
  );
}
