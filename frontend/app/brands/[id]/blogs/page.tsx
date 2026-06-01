import Link from "next/link";
import { notFound } from "next/navigation";

import { getBrand, listBlogJobs } from "@/lib/api";
import type { BlogJobOut } from "@/lib/types";

type Props = { params: { id: string } };

function statusColor(s: string) {
  if (s === "PUBLISHED") return "var(--accent)";
  if (s === "FAILED" || s === "REJECTED") return "var(--danger)";
  if (s === "PENDING_BRIEF_REVIEW" || s === "PENDING_REVIEW") return "var(--warning)";
  return "var(--accent-alt)";
}

export default async function BlogsPage({ params }: Props) {
  let brand, result;
  try {
    [brand, result] = await Promise.all([getBrand(params.id), listBlogJobs(params.id)]);
  } catch {
    notFound();
  }

  const jobs: BlogJobOut[] = result.items;

  return (
    <section className="stack">
      <div className="meta" style={{ letterSpacing: "0.15em", color: "var(--accent)" }}>
        SYS.NETWORK // BRANDS // {brand.name.toUpperCase()} // BLOG_ENGINE
      </div>

      <div className="page-head">
        <div>
          <h2 style={{ margin: 0 }}>Blog Engine</h2>
          <p className="meta" style={{ marginTop: 4 }}>SEO + AEO articles powered by Brand DNA</p>
        </div>
        <Link href={`/brands/${params.id}/blogs/new`} className="button">
          + New Article
        </Link>
      </div>

      {jobs.length === 0 ? (
        <div className="card stack" style={{ textAlign: "center", padding: "40px" }}>
          <p className="meta">No articles yet.</p>
          <Link href={`/brands/${params.id}/blogs/new`} className="button" style={{ alignSelf: "center" }}>
            Generate first article
          </Link>
        </div>
      ) : (
        <div className="stack">
          {jobs.map((job) => (
            <Link
              key={job.id}
              href={`/brands/${params.id}/blogs/${job.id}`}
              style={{ textDecoration: "none" }}
            >
              <div className="card row" style={{ cursor: "pointer" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>
                    {job.brief?.selected_title ?? job.keyword}
                  </div>
                  <div className="meta">Keyword: {job.keyword}</div>
                  {job.draft && (
                    <div className="meta" style={{ marginTop: 4 }}>
                      {job.draft.word_count} words · SEO {job.draft.seo_score}/100 · AEO {job.draft.aeo_score}/100 · Virality {job.draft.virality_score}/100
                    </div>
                  )}
                </div>
                <span className="status-badge" style={{ color: statusColor(job.status), borderColor: statusColor(job.status) }}>
                  {job.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
