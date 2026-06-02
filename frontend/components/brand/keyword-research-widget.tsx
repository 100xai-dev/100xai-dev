"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getKeywordStats } from "@/lib/api";

type KeywordStats = {
  total_keywords: number;
  avg_search_volume: number | null;
  avg_difficulty: number | null;
  top_sources: Record<string, number>;
  completion_rate: number;
};

interface KeywordResearchWidgetProps {
  brandId: string;
}

export function KeywordResearchWidget({ brandId }: KeywordResearchWidgetProps) {
  const [stats, setStats] = useState<KeywordStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, [brandId]);

  const loadStats = async () => {
    try {
      const data = await getKeywordStats(brandId);
      setStats(data);
    } catch (error) {
      console.error("Failed to load keyword stats:", error);
      // Don't show error state for this widget, just show empty state
      setStats({
        total_keywords: 0,
        avg_search_volume: null,
        avg_difficulty: null,
        top_sources: {},
        completion_rate: 0
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div style={{ padding: "20px", textAlign: "center" }}>
          <div style={{ width: 20, height: 20, border: "2px solid var(--gray-300)", borderTop: "2px solid var(--accent)", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto" }}></div>
          <p className="meta" style={{ marginTop: 8 }}>Loading keywords...</p>
        </div>
      </div>
    );
  }

  if (!stats || stats.total_keywords === 0) {
    return (
      <div className="card">
        <div className="stack stack-sm">
          <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>🔍 Keyword Research</h3>
            <Link 
              href={`/brands/${brandId}/keywords`}
              className="pill-link"
              style={{ fontSize: "0.8125rem", height: 28 }}
            >
              Start Research →
            </Link>
          </div>
          <p className="meta">
            No keywords discovered yet. Start keyword research to find SEO opportunities.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="stack stack-sm">
        <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>🔍 Keyword Research</h3>
          <Link 
            href={`/brands/${brandId}/keywords`}
            className="pill-link"
            style={{ fontSize: "0.8125rem", height: 28 }}
          >
            View All →
          </Link>
        </div>
        
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, paddingTop: 8 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)" }}>
              {stats.total_keywords}
            </div>
            <div className="meta" style={{ fontSize: "0.75rem" }}>Keywords</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)" }}>
              {stats.avg_search_volume ? `${Math.round(stats.avg_search_volume / 1000)}k` : "-"}
            </div>
            <div className="meta" style={{ fontSize: "0.75rem" }}>Avg Volume</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)" }}>
              {stats.avg_difficulty ? Math.round(stats.avg_difficulty) : "-"}
            </div>
            <div className="meta" style={{ fontSize: "0.75rem" }}>Avg Difficulty</div>
          </div>
        </div>

        {/* Top sources */}
        {Object.keys(stats.top_sources).length > 0 && (
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border-light)" }}>
            <div className="meta" style={{ fontSize: "0.75rem", marginBottom: 6 }}>Top Sources:</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {Object.entries(stats.top_sources)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 3)
                .map(([source, count]) => (
                  <span 
                    key={source}
                    style={{
                      fontSize: "0.75rem",
                      padding: "2px 6px",
                      backgroundColor: "var(--gray-100)",
                      borderRadius: "4px",
                      textTransform: "capitalize"
                    }}
                  >
                    {source.replace("_", " ")} ({count})
                  </span>
                ))
              }
            </div>
          </div>
        )}
      </div>
    </div>
  );
}