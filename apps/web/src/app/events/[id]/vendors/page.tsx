import { VendorStudio } from "@/components/vendor-studio";

export default async function VendorsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <VendorStudio eventId={id} />;
}
