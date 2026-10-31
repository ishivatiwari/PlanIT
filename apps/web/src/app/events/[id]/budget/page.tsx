import { BudgetTimeline } from "@/components/budget-timeline";

export default async function BudgetPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <BudgetTimeline eventId={id} />;
}
