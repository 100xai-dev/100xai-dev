"use client";

import { useState } from "react";

import { JobContentPanel } from "@/components/brand/job-content-panel";
import { JobKeywordsPanel } from "@/components/brand/job-keywords-panel";
import { JobSerpPanel } from "@/components/brand/job-serp-panel";
import type { BlogDraftOut, KeywordOut, SerpAnalysisItem } from "@/lib/types";

type TabKey = "keywords" | "serp" | "draft";

export function JobOutputTabs({
  jobId,
  brandId,
  initialKeywords,
  initialSerp,
  initialDraft,
  showKeywords,
  showSerp,
  showDraft,
}: {
  jobId: string;
  brandId: string;
  initialKeywords: KeywordOut[];
  initialSerp: SerpAnalysisItem[];
  initialDraft: BlogDraftOut | null;
  showKeywords: boolean;
  showSerp: boolean;
  showDraft: boolean;
}) {
  const tabs: { key: TabKey; label: string; enabled: boolean }[] = [
    { key: "keywords", label: "Keywords", enabled: showKeywords },
    { key: "serp", label: "SERP Analysis", enabled: showSerp },
    { key: "draft", label: "Draft", enabled: showDraft && initialDraft !== null },
  ];

  const firstEnabled = tabs.find((t) => t.enabled)?.key;
  const [active, setActive] = useState<TabKey | undefined>(firstEnabled);

  // No tab has data yet — nothing to render.
  if (!firstEnabled) return null;

  return (
    <div className="card stack">
      <div style={{ display: "flex", gap: 8 }}>
        {tabs.map((tab) => {
          const isActive = tab.key === active;
          return (
            <button
              key={tab.key}
              type="button"
              className="btn-ghost"
              disabled={!tab.enabled}
              onClick={() => tab.enabled && setActive(tab.key)}
              style={{
                background: isActive ? "var(--accent)" : "var(--bg-subtle)",
                color: isActive ? "#fff" : "var(--text-secondary)",
                opacity: tab.enabled ? 1 : 0.4,
                cursor: tab.enabled ? "pointer" : "not-allowed",
                borderRadius: "var(--radius-full)",
                padding: "6px 16px",
                fontSize: "0.8125rem",
                fontWeight: 600,
                border: "none",
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <hr className="divider" />

      {active === "keywords" && <JobKeywordsPanel initialKeywords={initialKeywords} />}
      {active === "serp" && <JobSerpPanel initialRecords={initialSerp} />}
      {active === "draft" && initialDraft && (
        <JobContentPanel draft={initialDraft} jobId={jobId} brandId={brandId} />
      )}
    </div>
  );
}
