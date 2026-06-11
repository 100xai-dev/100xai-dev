"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";


interface ChannelIntegration {
  id: string;
  brand_id: string;
  channel_type: "wordpress" | "webhook" | "shopify" | "ghost";
  name: string;
  status: "connected" | "disconnected" | "error" | "testing";
  config: {
    site_url?: string;
    webhook_url?: string;
    last_tested_at?: string;
    last_error?: string;
  };
  created_at: string;
  updated_at: string;
}

const CHANNEL_INFO = {
  wordpress: {
    name: "WordPress",
    description: "Publish directly to your WordPress website",
    icon: "📰",
    color: "bg-blue-50 border-blue-200 text-blue-700",
    setup_url: "/wordpress"
  },
  webhook: {
    name: "Custom Website",
    description: "Integrate with any website using webhooks",
    icon: "🔗",
    color: "bg-purple-50 border-purple-200 text-purple-700",
    setup_url: "/webhook"
  },
  shopify: {
    name: "Shopify Blog",
    description: "Publish to your Shopify store's blog",
    icon: "🛍️",
    color: "bg-green-50 border-green-200 text-green-700",
    setup_url: "/shopify"
  },
  ghost: {
    name: "Ghost",
    description: "Publish to your Ghost publication",
    icon: "👻",
    color: "bg-gray-50 border-gray-200 text-gray-700",
    setup_url: "/ghost"
  }
};

const STATUS_INFO = {
  connected: { label: "Connected", color: "bg-green-100 text-green-700", icon: "✓" },
  disconnected: { label: "Not Connected", color: "bg-gray-100 text-gray-600", icon: "○" },
  error: { label: "Connection Error", color: "bg-red-100 text-red-700", icon: "✗" },
  testing: { label: "Testing...", color: "bg-yellow-100 text-yellow-700", icon: "⏳" }
};

export default function BrandIntegrationsPage() {
  const params = useParams();
  const brandId = params.id as string;
  
  const [integrations, setIntegrations] = useState<ChannelIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testingChannel, setTestingChannel] = useState<string | null>(null);

  // Fetch existing integrations
  const fetchIntegrations = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/brands/${brandId}/integrations`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch integrations');
      }
      
      const data = await response.json();
      setIntegrations(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load integrations');
      // Ensure integrations remains an array even on error
      setIntegrations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, [brandId]);

  // Test connection for an integration
  const testConnection = async (integration: ChannelIntegration) => {
    try {
      setTestingChannel(integration.id);
      
      const response = await fetch(`/api/v1/brands/${brandId}/integrations/${integration.id}/test`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error('Connection test failed');
      }
      
      // Refresh integrations to get updated status
      await fetchIntegrations();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection test failed');
    } finally {
      setTestingChannel(null);
    }
  };

  // Delete an integration
  const deleteIntegration = async (integrationId: string) => {
    if (!confirm('Are you sure you want to remove this integration?')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/brands/${brandId}/integrations/${integrationId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete integration');
      }
      
      await fetchIntegrations();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete integration');
    }
  };

  // Get all available channel types
  const getAvailableChannels = () => {
    if (!Array.isArray(integrations)) {
      return Object.entries(CHANNEL_INFO);
    }
    const connectedTypes = new Set(integrations.map(i => i.channel_type));
    return Object.entries(CHANNEL_INFO).filter(([type]) => !connectedTypes.has(type as any));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading integrations...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Publishing Integrations</h1>
              <p className="text-gray-600">
                Connect your publishing channels to automatically publish scheduled content.
              </p>
            </div>
            <Link
              href={`/brands/${brandId}/integrations/troubleshooting`}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center"
            >
              🔧 Troubleshooting
            </Link>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Connected Integrations */}
        {Array.isArray(integrations) && integrations.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Connected Channels</h2>
            <div className="grid gap-4">
              {integrations.map((integration) => {
                const channelInfo = CHANNEL_INFO[integration.channel_type];
                const statusInfo = STATUS_INFO[integration.status];
                
                return (
                  <div key={integration.id} className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-xl ${channelInfo.color}`}>
                          {channelInfo.icon}
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">{integration.name}</h3>
                          <p className="text-sm text-gray-600 mb-2">{channelInfo.description}</p>
                          
                          {/* Connection Details */}
                          <div className="space-y-1 text-sm">
                            {integration.config.site_url && (
                              <div>
                                <span className="font-medium">Site:</span>
                                <a 
                                  href={integration.config.site_url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="ml-1 text-blue-600 hover:underline"
                                >
                                  {integration.config.site_url}
                                </a>
                              </div>
                            )}
                            {integration.config.webhook_url && (
                              <div>
                                <span className="font-medium">Webhook:</span>
                                <span className="ml-1 text-gray-600 font-mono text-xs">
                                  {integration.config.webhook_url.substring(0, 50)}...
                                </span>
                              </div>
                            )}
                            {integration.config.last_tested_at && (
                              <div>
                                <span className="font-medium">Last tested:</span>
                                <span className="ml-1 text-gray-600">
                                  {new Date(integration.config.last_tested_at).toLocaleString()}
                                </span>
                              </div>
                            )}
                          </div>
                          
                          {/* Error Message */}
                          {integration.status === "error" && integration.config.last_error && (
                            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                              {integration.config.last_error}
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-3">
                        {/* Status Badge */}
                        <div className={`px-2 py-1 rounded-full text-xs font-medium ${statusInfo.color}`}>
                          <span className="mr-1">{statusInfo.icon}</span>
                          {statusInfo.label}
                        </div>
                        
                        {/* Actions */}
                        <div className="flex space-x-2">
                          <button
                            onClick={() => testConnection(integration)}
                            disabled={testingChannel === integration.id}
                            className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                          >
                            {testingChannel === integration.id ? "Testing..." : "Test"}
                          </button>
                          <Link
                            href={`/brands/${brandId}/integrations${channelInfo.setup_url}?edit=${integration.id}`}
                            className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
                          >
                            Edit
                          </Link>
                          <button
                            onClick={() => deleteIntegration(integration.id)}
                            className="px-3 py-1 text-sm text-red-600 border border-red-300 rounded hover:bg-red-50"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Available Integrations */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            {Array.isArray(integrations) && integrations.length > 0 ? "Add More Channels" : "Connect Your First Channel"}
          </h2>
          
          <div className="grid md:grid-cols-2 gap-4">
            {getAvailableChannels().map(([type, info]) => (
              <Link
                key={type}
                href={`/brands/${brandId}/integrations${info.setup_url}`}
                className="bg-white rounded-lg border border-gray-200 p-6 hover:border-blue-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start space-x-4">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-xl ${info.color}`}>
                    {info.icon}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">{info.name}</h3>
                    <p className="text-sm text-gray-600 mb-3">{info.description}</p>
                    <div className="flex items-center text-blue-600 text-sm font-medium">
                      Connect {info.name}
                      <span className="ml-1">→</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
          
          {getAvailableChannels().length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-lg mb-2">🎉</div>
              <h3 className="text-lg font-medium text-gray-900 mb-1">All Channels Connected!</h3>
              <p className="text-gray-600">
                You've connected all available publishing channels. 
                <Link href={`/brands/${brandId}/calendar`} className="text-blue-600 hover:underline ml-1">
                  Start scheduling content →
                </Link>
              </p>
            </div>
          )}
        </div>

        {/* Getting Started Guide */}
        {(!Array.isArray(integrations) || integrations.length === 0) && (
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-2">🚀 Getting Started</h3>
            <div className="space-y-2 text-sm text-blue-800">
              <p><strong>Step 1:</strong> Choose a publishing channel above</p>
              <p><strong>Step 2:</strong> Follow the setup wizard to connect your account</p>
              <p><strong>Step 3:</strong> Test your connection to ensure it's working</p>
              <p><strong>Step 4:</strong> Create your first scheduled post in the calendar</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}