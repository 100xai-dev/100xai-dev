import { notFound } from "next/navigation";

import { getBrandProfile } from "@/lib/api";

type PageProps = {
  params: { id: string };
};

export default async function BrandOperationalPage({ params }: PageProps) {
  let profile;
  try {
    profile = await getBrandProfile(params.id);
  } catch {
    notFound();
  }

  return (
    <section className="card stack">
      <h2 style={{ margin: 0 }}>Operational Fields</h2>
      <p style={{ margin: 0 }}>Placid template: {profile.placid_template_id ?? "not set"}</p>
      <p style={{ margin: 0 }}>Image output bucket: {profile.image_output_bucket ?? "not set"}</p>
      <p style={{ margin: 0 }}>Default location: {profile.default_location}</p>
      <p style={{ margin: 0 }}>Default language: {profile.default_language}</p>
      <p style={{ margin: 0 }}>Publish adapter: {profile.publish_adapter}</p>
      <p style={{ margin: 0 }}>
        This page is read-only for now. Field-level editing is available through the DNA editor PATCH flow.
      </p>
    </section>
  );
}
