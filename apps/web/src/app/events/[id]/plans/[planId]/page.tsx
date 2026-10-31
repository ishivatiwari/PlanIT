import { PlanScreen } from "@/components/planning-workspace";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string; planId: string }>;
}) {
  const { id, planId } = await params;
  return <PlanScreen id={id} planId={planId} />;
}
