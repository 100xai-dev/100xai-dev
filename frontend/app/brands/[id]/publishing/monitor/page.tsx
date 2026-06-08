"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { getValidAccessToken } from "@/lib/auth";

interface PublishingStats {
  brand_id: string;
  period_days: number;
  total_schedules: number;
  published_count: number;
  failed_count: number;
  pending_count: number;
  success_rate: number;
  channel_stats: ChannelStats[];
  recent_activity: RecentActivity[];
}

interface ChannelStats {
  channel: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
}

interface RecentActivity {
  id: string;
  title: string;
  status: string;
  published_at?: string;
  channels: string[];
  published_urls: Record<string, string>;
}

interface QueueEntry {
  id: string;
  schedule_id: string;
  channel: string;
  status: string;
  scheduled_for: string;
  processing_started_at?: string;
  processing_completed_at?: string;
  attempt_count: number;
  last_error?: string;
  published_url?: string;
  external_id?: string;
  schedule: {
    title: string;
    status: string;
  };
}

interface FailedJob {
  id: string;
  schedule_id: string;
  channel: string;
  failed_at?: string;
  attempt_count: number;
  last_error?: string;
  can_retry: boolean;
  schedule: {
    title: string;
    slug?: string;
  };
}

const STATUS_COLORS = {
  PUBLISHED: "bg-green-100 text-green-700 border-green-200",
  FAILED: "bg-red-100 text-red-700 border-red-200",
  PUBLISHING: "bg-yellow-100 text-yellow-700 border-yellow-200",
  SCHEDULED: "bg-blue-100 text-blue-700 border-blue-200",
  PENDING: "bg-gray-100 text-gray-700 border-gray-200",
  COMPLETED: "bg-green-100 text-green-700 border-green-200"
};

const CHANNEL_COLORS = {
  wordpress: "bg-blue-50 text-blue-700",
  webhook: "bg-purple-50 text-purple-700",
  shopify: "bg-green-50 text-green-700",
  ghost: "bg-gray-50 text-gray-700"
};

const CHANNEL_ICONS = {
  wordpress: "📰",
  webhook: "🔗", 
  shopify: "🛍️",
  ghost: "👻"
};

export default function PublishingMonitorPage() {
  const params = useParams();
  const brandId = params.id as string;
  
  const [stats, setStats] = useState<PublishingStats | null>(null);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [failures, setFailures] = useState<FailedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryingJob, setRetryingJob] = useState<string | null>(null);

  // Fetch publishing statistics
  const fetchStats = async () => {
    try {
      const response = await fetch(`/api/v1/publishing/stats?brand_id=${brandId}&days=30`, {
        headers: {
          'Authorization': `Bearer ${await getValidAccessToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch publishing stats');
      }
      
      const data = await response.json();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    }
  };

  // Fetch publishing queue
  const fetchQueue = async () => {
    try {
      const response = await fetch(`/api/v1/publishing/queue?brand_id=${brandId}&limit=20`, {
        headers: {
          'Authorization': `Bearer ${await getValidAccessToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch publishing queue');
      }
      
      const data = await response.json();
      setQueue(data);
    } catch (err) {
      console.error('Failed to fetch queue:', err);
    }
  };

  // Fetch failed jobs
  const fetchFailures = async () => {
    try {
      const response = await fetch(`/api/v1/publishing/failures?brand_id=${brandId}&days=7&limit=10`, {
        headers: {
          'Authorization': `Bearer ${await getValidAccessToken()}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch failed jobs');
      }
      
      const data = await response.json();
      setFailures(data);
    } catch (err) {
      console.error('Failed to fetch failures:', err);
    }
  };

  // Retry a failed job
  const retryJob = async (queueId: string) => {
    try {
      setRetryingJob(queueId);
      
      const response = await fetch(`/api/v1/publishing/retry/${queueId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await getValidAccessToken()}`,
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to retry job');
      }
      
      // Refresh data
      await Promise.all([fetchStats(), fetchQueue(), fetchFailures()]);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry job');
    } finally {
      setRetryingJob(null);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchStats(), fetchQueue(), fetchFailures()]);
      setLoading(false);
    };

    loadData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [brandId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading publishing monitor...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Publishing Monitor</h1>
              <p className="text-gray-600">
                Monitor publishing performance and manage publishing queue
              </p>
            </div>
            <div className="flex space-x-3">
              <Link
                href={`/brands/${brandId}/calendar`}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                📅 Calendar
              </Link>
              <Link
                href={`/brands/${brandId}/integrations`}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                🔧 Integrations
              </Link>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-600 hover:text-red-800"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Statistics Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                  📊
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Schedules</p>
                  <p className="text-2xl font-bold text-gray-900">{stats.total_schedules}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mr-3">
                  ✅
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">Published</p>
                  <p className="text-2xl font-bold text-green-600">{stats.published_count}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center mr-3">
                  ❌
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">Failed</p>
                  <p className="text-2xl font-bold text-red-600">{stats.failed_count}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                  📈
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-600">Success Rate</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.success_rate.toFixed(1)}%</p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Channel Performance */}
          {stats && stats.channel_stats.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Channel Performance</h2>
              <div className="space-y-4">
                {stats.channel_stats.map((channel) => (
                  <div key={channel.channel} className="flex items-center justify-between p-3 border border-gray-100 rounded-lg">
                    <div className="flex items-center">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mr-3 ${CHANNEL_COLORS[channel.channel as keyof typeof CHANNEL_COLORS] || 'bg-gray-50 text-gray-700'}`}>
                        {CHANNEL_ICONS[channel.channel as keyof typeof CHANNEL_ICONS] || '🔗'}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 capitalize">{channel.channel}</p>
                        <p className="text-sm text-gray-600">{channel.completed_jobs}/{channel.total_jobs} published</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-gray-900">{channel.success_rate.toFixed(1)}%</p>
                      {channel.failed_jobs > 0 && (
                        <p className="text-sm text-red-600">{channel.failed_jobs} failed</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Activity */}
          {stats && stats.recent_activity.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
              <div className="space-y-3">
                {stats.recent_activity.slice(0, 5).map((activity) => (
                  <div key={activity.id} className="flex items-start justify-between p-3 border border-gray-100 rounded-lg">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 text-sm">{activity.title}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className={`px-2 py-1 text-xs rounded-full border ${STATUS_COLORS[activity.status as keyof typeof STATUS_COLORS] || 'bg-gray-100 text-gray-700'}`}>
                          {activity.status}
                        </span>
                        <div className="flex space-x-1">
                          {activity.channels.map(channel => (
                            <span key={channel} className="text-xs">
                              {CHANNEL_ICONS[channel as keyof typeof CHANNEL_ICONS] || '🔗'}
                            </span>
                          ))}
                        </div>
                      </div>
                      {activity.published_at && (
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(activity.published_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    {Object.keys(activity.published_urls).length > 0 && (
                      <div className="ml-3">
                        <button className="text-xs text-blue-600 hover:text-blue-800">
                          View Links
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Publishing Queue */}
        {queue.length > 0 && (
          <div className="mt-8 bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Publishing Queue</h2>
            </div>
            <div className="divide-y divide-gray-200">
              {queue.slice(0, 10).map((entry) => (
                <div key={entry.id} className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="font-medium text-gray-900">{entry.schedule.title}</h3>
                        <span className={`px-2 py-1 text-xs rounded-full border ${STATUS_COLORS[entry.status as keyof typeof STATUS_COLORS]}`}>
                          {entry.status}
                        </span>
                        <div className={`px-2 py-1 text-xs rounded-lg ${CHANNEL_COLORS[entry.channel as keyof typeof CHANNEL_COLORS] || 'bg-gray-50 text-gray-700'}`}>
                          {CHANNEL_ICONS[entry.channel as keyof typeof CHANNEL_ICONS]} {entry.channel}
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">Scheduled:</span>
                          <br />
                          {new Date(entry.scheduled_for).toLocaleString()}
                        </div>
                        {entry.processing_started_at && (
                          <div>
                            <span className="font-medium">Started:</span>
                            <br />
                            {new Date(entry.processing_started_at).toLocaleString()}
                          </div>
                        )}
                        {entry.processing_completed_at && (
                          <div>
                            <span className="font-medium">Completed:</span>
                            <br />
                            {new Date(entry.processing_completed_at).toLocaleString()}
                          </div>
                        )}
                        <div>
                          <span className="font-medium">Attempts:</span>
                          <br />
                          {entry.attempt_count}
                        </div>
                      </div>
                      
                      {entry.last_error && (
                        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                          {entry.last_error}
                        </div>
                      )}
                      
                      {entry.published_url && (
                        <div className="mt-2">
                          <a 
                            href={entry.published_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 text-sm"
                          >
                            View Published Content →
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Failed Jobs */}
        {failures.length > 0 && (
          <div className="mt-8 bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Recent Failures</h2>
            </div>
            <div className="divide-y divide-gray-200">
              {failures.map((failure) => (
                <div key={failure.id} className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="font-medium text-gray-900">{failure.schedule.title}</h3>
                        <div className={`px-2 py-1 text-xs rounded-lg ${CHANNEL_COLORS[failure.channel as keyof typeof CHANNEL_COLORS] || 'bg-gray-50 text-gray-700'}`}>
                          {CHANNEL_ICONS[failure.channel as keyof typeof CHANNEL_ICONS]} {failure.channel}
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-2">
                        <div>
                          <span className="font-medium">Failed:</span> {failure.failed_at ? new Date(failure.failed_at).toLocaleString() : 'Unknown'}
                        </div>
                        <div>
                          <span className="font-medium">Attempts:</span> {failure.attempt_count}/3
                        </div>
                      </div>
                      
                      {failure.last_error && (
                        <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                          {failure.last_error}
                        </div>
                      )}
                    </div>
                    
                    <div className="ml-4">
                      {failure.can_retry && (
                        <button
                          onClick={() => retryJob(failure.id)}
                          disabled={retryingJob === failure.id}
                          className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {retryingJob === failure.id ? "Retrying..." : "Retry"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty States */}
        {!loading && stats && stats.total_schedules === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">📅</div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No Scheduled Content</h3>
            <p className="text-gray-600 mb-4">
              Start by creating your first scheduled post to see publishing activity here.
            </p>
            <Link
              href={`/brands/${brandId}/calendar`}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              Create Schedule
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}