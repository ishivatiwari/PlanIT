import { ButtonLink } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="page-intro">
      <span className="eyebrow">Page not found</span>
      <h1>Let&apos;s find your way back.</h1>
      <p>This address does not lead to a page in the preview.</p>
      <ButtonLink href="/">Return to overview</ButtonLink>
    </div>
  );
}
