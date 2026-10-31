import { ReplanStudio } from "@/components/replan-studio";

export default async function ReplanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReplanStudio eventId={id} />;
}
