import { EventScreen } from "@/components/event-workspace";
export default async function EditEvent({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return <EventScreen id={(await params).id} edit />;
}
