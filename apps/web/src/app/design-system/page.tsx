import { ComponentPreview } from "@/components/component-preview";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Design system | PlanIT" };

export default function DesignSystemPage() {
  return (
    <>
      <div className="page-intro">
        <span className="eyebrow">The details make the difference</span>
        <h1>A shared design language.</h1>
        <p>
          Calm colors, clear choices, and space to breathe. Explore the building
          blocks of PlanIT.
        </p>
      </div>
      <ComponentPreview />
    </>
  );
}
