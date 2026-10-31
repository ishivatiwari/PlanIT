"use client";

import { Button, ButtonLink } from "@/components/ui/button";
import { Message } from "@/components/ui/feedback";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="page-intro">
      <h1>A little interruption.</h1>
      <Message tone="error" title="This page could not be loaded" announce>
        Please try again. If the problem continues, return to the overview.
      </Message>
      <div className="button-row section-block">
        <Button onClick={reset}>Try again</Button>
        <ButtonLink variant="secondary" href="/">
          Return to overview
        </ButtonLink>
      </div>
    </div>
  );
}
