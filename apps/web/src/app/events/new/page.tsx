import { RequireAccount } from "@/components/auth-provider";
import { EventForm } from "@/components/event-form";
export default async function NewEvent({
  searchParams,
}: {
  searchParams: Promise<{ type?: string }>;
}) {
  const { type } = await searchParams;
  return (
    <RequireAccount>
      <EventForm
        type={type === "birthday" || type === "community" ? type : "wedding"}
      />
    </RequireAccount>
  );
}
