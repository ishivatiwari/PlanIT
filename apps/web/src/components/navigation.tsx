import Link from "next/link";
import { Icon, type IconName } from "./icon";

const destinations: { href: string; label: string; icon: IconName }[] = [
  { href: "/", label: "Overview", icon: "grid" },
  { href: "/events", label: "My events", icon: "calendar" },
  { href: "/design-system", label: "Design system", icon: "palette" },
  { href: "/system-status", label: "System status", icon: "layers" },
];

export function Navigation({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="navigation" aria-label="Workspace navigation">
      <p className="navigation-label">Workspace</p>
      {destinations.map(({ href, label, icon }) => (
        <Link
          key={href}
          href={href}
          onClick={onNavigate}
          aria-current={
            pathname === href ||
            (href === "/events" && pathname.startsWith("/events/"))
              ? "page"
              : undefined
          }
        >
          <Icon name={icon} />
          <span>{label}</span>
          {(pathname === href ||
            (href === "/events" && pathname.startsWith("/events/"))) && (
            <span className="nav-current-dot" />
          )}
        </Link>
      ))}
      <p className="navigation-label navigation-label--next">Event tools</p>
      <div className="nav-upcoming">
        <Icon name="wallet" />
        <span>Budget</span>
        <small>In an event</small>
      </div>
      <div className="nav-upcoming">
        <Icon name="clock" />
        <span>Timeline</span>
        <small>In an event</small>
      </div>
    </nav>
  );
}
