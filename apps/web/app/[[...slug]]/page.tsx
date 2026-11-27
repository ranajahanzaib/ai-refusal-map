import Observatory from "@/components/observatory";

export default async function Page({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug = [] } = await params;
  return <Observatory route={slug.join("/")} />;
}
