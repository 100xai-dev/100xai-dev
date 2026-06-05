"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import { getKeywordStats, listKeywords, startKeywordResearch, getJob, startSerpAnalysis, getSerpAnalysisResults } from "@/lib/api";
import { isDemoMode } from "@/lib/config";

type Keyword = {
  id: string;
  related_keyword: string;
  primary_keyword: string;
  source_type: string;
  search_volume: number | null;
  keyword_difficulty: number | null;
  cpc: number | null;
  competition: number | null;
  search_intent: string | null;
  score: number | null;
  created_at: string;
};

type KeywordStats = {
  total_keywords: number;
  avg_search_volume: number | null;
  avg_difficulty: number | null;
  top_sources: Record<string, number>;
  completion_rate: number;
};

const mockKeywords: Keyword[] = [
  {
    id: "1",
    related_keyword: "artificial intelligence",
    primary_keyword: "ai technology",
    source_type: "related_keywords",
    search_volume: 22200,
    keyword_difficulty: 75,
    cpc: 1.50,
    competition: 0.8,
    search_intent: "commercial",
    score: 0.78,
    created_at: "2026-06-02T10:30:00Z"
  },
  {
    id: "2",
    related_keyword: "machine learning",
    primary_keyword: "ai technology",
    source_type: "suggestions",
    search_volume: 18100,
    keyword_difficulty: 65,
    cpc: 2.10,
    competition: 0.7,
    search_intent: "informational",
    score: 0.72,
    created_at: "2026-06-02T10:30:00Z"
  },
  {
    id: "3",
    related_keyword: "ai automation",
    primary_keyword: "ai technology",
    source_type: "ideas",
    search_volume: 8900,
    keyword_difficulty: 55,
    cpc: 3.20,
    competition: 0.6,
    search_intent: "commercial",
    score: 0.85,
    created_at: "2026-06-02T10:30:00Z"
  }
];

const mockStats: KeywordStats = {
  total_keywords: 87,
  avg_search_volume: 12500,
  avg_difficulty: 62,
  top_sources: {
    "related_keywords": 25,
    "suggestions": 22,
    "ideas": 18,
    "autocomplete": 15,
    "sub_topics": 7
  },
  completion_rate: 0.94
};

function StatusBadge({ status }: { status: string }) {
  const statusColors = {
    never_run: "bg-gray-100 text-gray-700",
    processing: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700"
  };

  const statusLabels = {
    never_run: "Not Started",
    processing: "Processing...",
    completed: "Completed",
    failed: "Failed"
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[status as keyof typeof statusColors] || statusColors.never_run}`}>
      {statusLabels[status as keyof typeof statusLabels] || "Unknown"}
    </span>
  );
}

function DifficultyBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-400">-</span>;
  
  let color = "bg-green-100 text-green-700";
  if (value >= 70) color = "bg-red-100 text-red-700";
  else if (value >= 50) color = "bg-yellow-100 text-yellow-700";

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${color}`}>
      {value}
    </span>
  );
}

function ScoreBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-400">-</span>;
  
  const percentage = Math.round(value * 100);
  let color = "bg-red-100 text-red-700";
  if (percentage >= 70) color = "bg-green-100 text-green-700";
  else if (percentage >= 50) color = "bg-yellow-100 text-yellow-700";

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${color}`}>
      {percentage}%
    </span>
  );
}

export default function KeywordsPage() {
  const params = useParams();
  const router = useRouter();
  const brandId = params.id as string;
  const isDemo = isDemoMode();

  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [stats, setStats] = useState<KeywordStats | null>(null);
  const [researchStatus, setResearchStatus] = useState("never_run");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [seedKeyword, setSeedKeyword] = useState("");
  const [latestJobId, setLatestJobId] = useState<string | null>(null);
  const [startingSerpAnalysis, setStartingSerpAnalysis] = useState(false);

  useEffect(() => {
    loadData();
  }, [brandId]);

  // Poll for updates when processing
  useEffect(() => {
    if (researchStatus === "processing" && latestJobId) {
      const interval = setInterval(async () => {
        try {
          const job = await getJob(latestJobId);
          if (job.status === "SUCCEEDED") {
            loadData(); // Reload everything
            clearInterval(interval);
          } else if (job.status === "FAILED") {
            setResearchStatus("failed");
            clearInterval(interval);
          }
        } catch (error) {
          console.error("Failed to poll job status:", error);
        }
      }, 3000);

      return () => clearInterval(interval);
    }
  }, [researchStatus, latestJobId]);

  const loadData = async () => {
    if (isDemo) {
      setKeywords(mockKeywords);
      setStats(mockStats);
      setResearchStatus("completed");
      setLoading(false);
      return;
    }

    try {
      const [keywordData, statsData] = await Promise.all([
        listKeywords(brandId),
        getKeywordStats(brandId)
      ]);

      setKeywords(keywordData.keywords);
      setStats(statsData);
      setResearchStatus(keywordData.research_status);
      setLatestJobId(keywordData.latest_job_id);
    } catch (error) {
      console.error("Failed to load keyword data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartResearch = async () => {
    if (!seedKeyword.trim()) return;

    setStarting(true);
    try {
      const result = await startKeywordResearch(brandId, seedKeyword.trim());
      setLatestJobId(result.job_id);
      setResearchStatus("processing");
      setSeedKeyword(""); // Clear the input
    } catch (error) {
      console.error("Failed to start keyword research:", error);
      alert("Failed to start keyword research. Please try again.");
    } finally {
      setStarting(false);
    }
  };

  const handleStartSerpAnalysis = async () => {
    setStartingSerpAnalysis(true);
    try {
      await startSerpAnalysis(brandId);
      router.push(`/brands/${brandId}/serp-analysis`);
    } catch (error) {
      console.error("Failed to start SERP analysis:", error);
      alert("Failed to start SERP analysis. Make sure you have completed keyword research first.");
    } finally {
      setStartingSerpAnalysis(false);
    }
  };

  if (loading) {
    return (
      <div className="stack stack-lg">
        <div className="card" style={{ padding: "40px", textAlign: "center" }}>
          <div className="stack stack-sm">
            <div style={{ width: 24, height: 24, border: "3px solid var(--accent)", borderTop: "3px solid transparent", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto" }}></div>
            <p className="meta">Loading keyword research data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="stack stack-lg">
      {isDemo && (
        <div className="alert alert-warning">
          <span>⚠</span>
          <span><strong>Demo mode.</strong> Displaying mock keyword data.</span>
        </div>
      )}

      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brandId}`}>Brand</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>Keywords</span>
      </nav>

      {/* Page Header */}
      <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Keyword Research</h1>
        <StatusBadge status={researchStatus} />
      </div>

      {/* Research Form — always visible so user can start additional searches */}
      <div className="card">
        <div className="stack stack-md">
          <div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600 }}>🔍 Keyword Research</h3>
            <p className="meta" style={{ marginTop: 4 }}>
              Enter a seed keyword to discover related keywords, search volumes, and competitive analysis.
              {researchStatus === "completed" && " Add more keywords to expand your research."}
            </p>
          </div>
          <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
            <input
              type="text"
              placeholder="e.g., artificial intelligence, digital marketing, cloud computing"
              value={seedKeyword}
              onChange={(e) => setSeedKeyword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleStartResearch()}
              style={{ flex: 1, minWidth: 240 }}
              disabled={starting || researchStatus === "processing"}
            />
            <button
              onClick={handleStartResearch}
              disabled={starting || !seedKeyword.trim() || researchStatus === "processing"}
              style={{ 
                padding: "8px 20px",
                backgroundColor: starting || !seedKeyword.trim() || researchStatus === "processing" ? "var(--gray-200)" : "var(--accent)",
                color: starting || !seedKeyword.trim() || researchStatus === "processing" ? "var(--gray-500)" : "white",
                border: "none",
                borderRadius: "6px",
                fontWeight: 500,
                cursor: starting || !seedKeyword.trim() || researchStatus === "processing" ? "not-allowed" : "pointer",
                whiteSpace: "nowrap"
              }}
            >
              {starting ? "Starting..." : "Start Research"}
            </button>
          </div>
          {researchStatus === "failed" && (
            <div className="alert alert-error">
              <span>❌</span>
              <span>Previous research failed. Please try again with a different keyword.</span>
            </div>
          )}
        </div>
      </div>

      {/* Processing Status */}
      {researchStatus === "processing" && (
        <div className="card" style={{ borderColor: "var(--accent-border)", background: "var(--accent-light)" }}>
          <div className="stack stack-sm">
            <div className="row" style={{ alignItems: "center", gap: 8 }}>
              <span className="pulse-dot" style={{ background: "var(--accent)" }} />
              <h3 style={{ color: "var(--accent)", fontSize: "1rem", fontWeight: 600 }}>Research in Progress</h3>
            </div>
            <p style={{ color: "var(--accent)" }}>
              Analyzing keywords and gathering SEO metrics... This usually takes 5-10 minutes.
            </p>
            {latestJobId && (
              <Link 
                href={`/brands/${brandId}/jobs/${latestJobId}`}
                className="pill-link"
                style={{ alignSelf: "flex-start", fontSize: "0.8125rem" }}
              >
                View job details →
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {researchStatus === "completed" && stats && (
        <>
          {/* Statistics Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            <div className="card" style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
                {stats.total_keywords}
              </div>
              <div className="meta">Total Keywords</div>
            </div>
            <div className="card" style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
                {stats.avg_search_volume ? `${Math.round(stats.avg_search_volume).toLocaleString()}` : "-"}
              </div>
              <div className="meta">Avg Search Volume</div>
            </div>
            <div className="card" style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
                {stats.avg_difficulty ? Math.round(stats.avg_difficulty) : "-"}
              </div>
              <div className="meta">Avg Difficulty</div>
            </div>
            <div className="card" style={{ textAlign: "center" }}>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--accent)" }}>
                {Math.round(stats.completion_rate * 100)}%
              </div>
              <div className="meta">Data Completion</div>
            </div>
          </div>

          {/* Keywords Table */}
          <div className="card">
            <div className="stack stack-md">
              <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
                <h3 style={{ fontSize: "1.125rem", fontWeight: 600 }}>🏆 Discovered Keywords</h3>
                <button
                  onClick={handleStartSerpAnalysis}
                  disabled={startingSerpAnalysis}
                  style={{ 
                    padding: "6px 16px",
                    backgroundColor: startingSerpAnalysis ? "var(--gray-200)" : "var(--accent)",
                    color: startingSerpAnalysis ? "var(--gray-500)" : "white",
                    border: "none",
                    borderRadius: "6px",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    cursor: startingSerpAnalysis ? "not-allowed" : "pointer"
                  }}
                >
                  {startingSerpAnalysis ? "Starting..." : "🔍 Start SERP Analysis"}
                </button>
              </div>

              {keywords.length > 0 ? (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                        <th style={{ textAlign: "left", padding: "12px 8px", fontWeight: 600, fontSize: "0.875rem" }}>
                          Keyword
                        </th>
                        <th style={{ textAlign: "right", padding: "12px 8px", fontWeight: 600, fontSize: "0.875rem" }}>
                          Volume
                        </th>
                        <th style={{ textAlign: "center", padding: "12px 8px", fontWeight: 600, fontSize: "0.875rem" }}>
                          Difficulty
                        </th>
                        <th style={{ textAlign: "center", padding: "12px 8px", fontWeight: 600, fontSize: "0.875rem" }}>
                          Score
                        </th>
                        <th style={{ textAlign: "left", padding: "12px 8px", fontWeight: 600, fontSize: "0.875rem" }}>
                          Source
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {keywords.slice(0, 20).map((keyword) => (
                        <tr key={keyword.id} style={{ borderBottom: "1px solid var(--border-light)" }}>
                          <td style={{ padding: "12px 8px" }}>
                            <div>
                              <div style={{ fontWeight: 500 }}>{keyword.related_keyword}</div>
                              {keyword.cpc && (
                                <div className="meta" style={{ fontSize: "0.75rem", marginTop: 2 }}>
                                  CPC: ${keyword.cpc.toFixed(2)}
                                </div>
                              )}
                            </div>
                          </td>
                          <td style={{ padding: "12px 8px", textAlign: "right" }}>
                            {keyword.search_volume ? keyword.search_volume.toLocaleString() : "-"}
                          </td>
                          <td style={{ padding: "12px 8px", textAlign: "center" }}>
                            <DifficultyBadge value={keyword.keyword_difficulty} />
                          </td>
                          <td style={{ padding: "12px 8px", textAlign: "center" }}>
                            <ScoreBadge value={keyword.score} />
                          </td>
                          <td style={{ padding: "12px 8px", fontSize: "0.875rem", textTransform: "capitalize" }}>
                            {keyword.source_type.replace("_", " ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "40px", color: "var(--gray-500)" }}>
                  <p>No keywords found. Start a research to discover keywords for your brand.</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}