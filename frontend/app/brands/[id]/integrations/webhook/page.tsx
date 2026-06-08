"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { getValidAccessToken } from "@/lib/auth";

interface WebhookConfig {
  id?: string;
  webhook_url: string;
  auth_type: "none" | "bearer" | "basic" | "api_key" | "hmac";
  auth_token?: string;
  auth_username?: string;
  auth_password?: string;
  api_key_header?: string;
  api_key_value?: string;
  hmac_secret?: string;
  hmac_algorithm?: "sha256" | "sha512";
  custom_headers?: Record<string, string>;
  payload_format: "json" | "form_data";
  include_meta?: boolean;
  include_images?: boolean;
  webhook_timeout?: number;
  retry_attempts?: number;
}

interface ConnectionTest {
  success: boolean;
  response_status?: number;
  response_time?: number;
  error?: string;
}

const AUTH_TYPES = [
  { value: "none", label: "No Authentication", description: "No authentication required" },
  { value: "bearer", label: "Bearer Token", description: "Authorization: Bearer <token>" },
  { value: "basic", label: "Basic Auth", description: "Authorization: Basic <username:password>" },
  { value: "api_key", label: "API Key", description: "Custom header with API key" },
  { value: "hmac", label: "HMAC Signature", description: "Request signature verification" }
];

const SETUP_STEPS = [
  { id: 1, title: "Webhook URL", description: "Enter your webhook endpoint" },
  { id: 2, title: "Authentication", description: "Configure security settings" },
  { id: 3, title: "Payload Settings", description: "Customize data format" },
  { id: 4, title: "Test & Complete", description: "Test webhook and finalize setup" }
];

export default function WebhookSetupPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const brandId = params.id as string;
  const editMode = searchParams.get('edit');
  
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const [config, setConfig] = useState<WebhookConfig>({
    webhook_url: "",
    auth_type: "none",
    custom_headers: {},
    payload_format: "json",
    include_meta: true,
    include_images: true,
    webhook_timeout: 30,
    retry_attempts: 3,
    hmac_algorithm: "sha256"
  });

  // Load existing configuration if in edit mode
  useEffect(() => {
    if (editMode) {
      loadExistingConfig();
    }
  }, [editMode]);

  const loadExistingConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/brands/${brandId}/integrations/${editMode}`, {
        headers: {
          'Authorization': `Bearer ${await getValidAccessToken()}`,
        },
      });

      if (response.ok) {
        const integration = await response.json();
        setConfig({
          id: integration.id,
          webhook_url: integration.config.webhook_url || "",
          auth_type: integration.config.auth_type || "none",
          auth_token: integration.config.auth_token || "",
          auth_username: integration.config.auth_username || "",
          auth_password: "", // Don't show existing password for security
          api_key_header: integration.config.api_key_header || "",
          api_key_value: integration.config.api_key_value || "",
          hmac_secret: "", // Don't show existing secret for security
          hmac_algorithm: integration.config.hmac_algorithm || "sha256",
          custom_headers: integration.config.custom_headers || {},
          payload_format: integration.config.payload_format || "json",
          include_meta: integration.config.include_meta ?? true,
          include_images: integration.config.include_images ?? true,
          webhook_timeout: integration.config.webhook_timeout || 30,
          retry_attempts: integration.config.retry_attempts || 3
        });
        setCurrentStep(4); // Go to test step for existing integrations
      }
    } catch (err) {
      setError("Failed to load existing configuration");
    } finally {
      setLoading(false);
    }
  };

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 1:
        return !!(config.webhook_url && isValidUrl(config.webhook_url));
      case 2:
        if (config.auth_type === "bearer") return !!config.auth_token;
        if (config.auth_type === "basic") return !!(config.auth_username && config.auth_password);
        if (config.auth_type === "api_key") return !!(config.api_key_header && config.api_key_value);
        if (config.auth_type === "hmac") return !!config.hmac_secret;
        return true; // No auth required
      case 3:
        return !!config.payload_format;
      default:
        return true;
    }
  };

  const isValidUrl = (url: string): boolean => {
    try {
      const urlObj = new URL(url);
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 4));
      setError(null);
    } else {
      setError("Please fill in all required fields before continuing");
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
    setError(null);
  };

  const addCustomHeader = () => {
    const headerName = prompt("Enter header name:");
    if (headerName && headerName.trim()) {
      const headerValue = prompt("Enter header value:");
      if (headerValue !== null) {
        setConfig(prev => ({
          ...prev,
          custom_headers: {
            ...prev.custom_headers,
            [headerName.trim()]: headerValue.trim()
          }
        }));
      }
    }
  };

  const removeCustomHeader = (headerName: string) => {
    setConfig(prev => {
      const newHeaders = { ...prev.custom_headers };
      delete newHeaders[headerName];
      return { ...prev, custom_headers: newHeaders };
    });
  };

  const testWebhook = async () => {
    try {
      setLoading(true);
      setTestResult(null);

      const response = await fetch(`/api/v1/brands/${brandId}/integrations/webhook/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await getValidAccessToken()}`,
        },
        body: JSON.stringify(config),
      });

      const result = await response.json();
      setTestResult(result);
      
      if (!result.success) {
        setError(result.error || 'Webhook test failed');
      }
    } catch (err) {
      setError('Failed to test webhook');
      setTestResult({ success: false, error: 'Network error' });
    } finally {
      setLoading(false);
    }
  };

  const saveIntegration = async () => {
    try {
      setLoading(true);
      
      const integrationData = {
        channel_type: "webhook",
        name: `Webhook - ${new URL(config.webhook_url).hostname}`,
        config: {
          ...config,
          last_tested_at: new Date().toISOString()
        }
      };

      const url = editMode 
        ? `/api/v1/brands/${brandId}/integrations/${editMode}`
        : `/api/v1/brands/${brandId}/integrations`;
      
      const method = editMode ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await getValidAccessToken()}`,
        },
        body: JSON.stringify(integrationData),
      });

      if (response.ok) {
        router.push(`/brands/${brandId}/integrations`);
      } else {
        throw new Error('Failed to save integration');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save integration');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !config.webhook_url) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading configuration...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <Link 
              href={`/brands/${brandId}/integrations`}
              className="text-gray-500 hover:text-gray-700"
            >
              ← Back to Integrations
            </Link>
          </div>
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              🔗
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {editMode ? "Edit Webhook Integration" : "Setup Webhook Integration"}
              </h1>
              <p className="text-gray-600">
                Connect any website or service using webhook notifications
              </p>
            </div>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between">
            {SETUP_STEPS.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep >= step.id 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-gray-200 text-gray-600'
                }`}>
                  {currentStep > step.id ? '✓' : step.id}
                </div>
                <div className="ml-3 hidden sm:block">
                  <div className={`text-sm font-medium ${
                    currentStep >= step.id ? 'text-gray-900' : 'text-gray-500'
                  }`}>
                    {step.title}
                  </div>
                  <div className="text-xs text-gray-500">{step.description}</div>
                </div>
                {index < SETUP_STEPS.length - 1 && (
                  <div className={`hidden sm:block w-12 h-px mx-4 ${
                    currentStep > step.id ? 'bg-purple-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Step Content */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Webhook URL</h3>
                <p className="text-gray-600 mb-4">
                  Enter the URL where you want to receive webhook notifications when content is published.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Webhook Endpoint URL *
                </label>
                <input
                  type="url"
                  value={config.webhook_url}
                  onChange={(e) => setConfig(prev => ({ ...prev, webhook_url: e.target.value }))}
                  placeholder="https://yoursite.com/webhook/publish"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  This URL will receive POST requests when content is published
                </p>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 mb-2">Webhook Payload Example</h4>
                <pre className="text-xs text-blue-800 bg-blue-100 p-3 rounded font-mono overflow-x-auto">
{`{
  "event": "content_published",
  "brand_id": "brand-123",
  "content": {
    "id": "content-456",
    "title": "Your Blog Post Title",
    "html_content": "<p>...</p>",
    "published_at": "2024-01-01T12:00:00Z",
    "target_keyword": "example keyword",
    "categories": ["Blog"],
    "tags": ["AI", "Automation"]
  }
}`}
                </pre>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Authentication</h3>
                <p className="text-gray-600 mb-4">
                  Choose how you want to secure your webhook endpoint.
                </p>
              </div>

              {/* Auth Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Authentication Method
                </label>
                <div className="space-y-3">
                  {AUTH_TYPES.map(authType => (
                    <label key={authType.value} className="flex items-start space-x-3">
                      <input
                        type="radio"
                        name="auth_type"
                        value={authType.value}
                        checked={config.auth_type === authType.value}
                        onChange={(e) => setConfig(prev => ({ ...prev, auth_type: e.target.value as any }))}
                        className="mt-1"
                      />
                      <div>
                        <div className="font-medium">{authType.label}</div>
                        <div className="text-sm text-gray-500">{authType.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Auth Configuration Forms */}
              {config.auth_type === "bearer" && (
                <div className="p-4 bg-purple-50 rounded-lg">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Bearer Token *
                  </label>
                  <input
                    type="password"
                    value={config.auth_token}
                    onChange={(e) => setConfig(prev => ({ ...prev, auth_token: e.target.value }))}
                    placeholder="Your bearer token"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
                  />
                </div>
              )}

              {config.auth_type === "basic" && (
                <div className="p-4 bg-purple-50 rounded-lg space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Username *
                    </label>
                    <input
                      type="text"
                      value={config.auth_username}
                      onChange={(e) => setConfig(prev => ({ ...prev, auth_username: e.target.value }))}
                      placeholder="HTTP Basic Auth username"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Password *
                    </label>
                    <input
                      type="password"
                      value={config.auth_password}
                      onChange={(e) => setConfig(prev => ({ ...prev, auth_password: e.target.value }))}
                      placeholder="HTTP Basic Auth password"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>
              )}

              {config.auth_type === "api_key" && (
                <div className="p-4 bg-purple-50 rounded-lg space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Header Name *
                    </label>
                    <input
                      type="text"
                      value={config.api_key_header}
                      onChange={(e) => setConfig(prev => ({ ...prev, api_key_header: e.target.value }))}
                      placeholder="e.g., X-API-Key, Authorization"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      API Key Value *
                    </label>
                    <input
                      type="password"
                      value={config.api_key_value}
                      onChange={(e) => setConfig(prev => ({ ...prev, api_key_value: e.target.value }))}
                      placeholder="Your API key"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
                    />
                  </div>
                </div>
              )}

              {config.auth_type === "hmac" && (
                <div className="p-4 bg-purple-50 rounded-lg space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      HMAC Secret *
                    </label>
                    <input
                      type="password"
                      value={config.hmac_secret}
                      onChange={(e) => setConfig(prev => ({ ...prev, hmac_secret: e.target.value }))}
                      placeholder="Your HMAC secret key"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Algorithm
                    </label>
                    <select
                      value={config.hmac_algorithm}
                      onChange={(e) => setConfig(prev => ({ ...prev, hmac_algorithm: e.target.value as any }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="sha256">SHA-256</option>
                      <option value="sha512">SHA-512</option>
                    </select>
                  </div>
                  <div className="text-xs text-gray-600">
                    <p className="font-medium mb-1">HMAC signature will be sent in the header:</p>
                    <code className="bg-gray-100 px-2 py-1 rounded">X-Webhook-Signature: sha256=&lt;signature&gt;</code>
                  </div>
                </div>
              )}
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Payload Settings</h3>
                <p className="text-gray-600 mb-4">
                  Configure how the webhook payload is formatted and what data to include.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Payload Format
                  </label>
                  <select
                    value={config.payload_format}
                    onChange={(e) => setConfig(prev => ({ ...prev, payload_format: e.target.value as any }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="json">JSON</option>
                    <option value="form_data">Form Data</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Timeout (seconds)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="60"
                    value={config.webhook_timeout}
                    onChange={(e) => setConfig(prev => ({ ...prev, webhook_timeout: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.include_meta}
                    onChange={(e) => setConfig(prev => ({ ...prev, include_meta: e.target.checked }))}
                    className="mr-3"
                  />
                  <span className="text-sm">Include metadata (keywords, categories, tags)</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.include_images}
                    onChange={(e) => setConfig(prev => ({ ...prev, include_images: e.target.checked }))}
                    className="mr-3"
                  />
                  <span className="text-sm">Include image URLs and featured images</span>
                </label>
              </div>

              {/* Advanced Settings */}
              <div>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                >
                  {showAdvanced ? '▼' : '▶'} Advanced Settings
                </button>
                
                {showAdvanced && (
                  <div className="mt-4 space-y-4 p-4 bg-gray-50 rounded-lg">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Retry Attempts
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="5"
                        value={config.retry_attempts}
                        onChange={(e) => setConfig(prev => ({ ...prev, retry_attempts: parseInt(e.target.value) }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-sm font-medium text-gray-700">
                          Custom Headers
                        </label>
                        <button
                          onClick={addCustomHeader}
                          className="text-xs text-purple-600 hover:text-purple-700 font-medium"
                        >
                          + Add Header
                        </button>
                      </div>
                      {Object.entries(config.custom_headers || {}).map(([name, value]) => (
                        <div key={name} className="flex items-center space-x-2 mb-2">
                          <code className="text-xs bg-white px-2 py-1 rounded border flex-1">
                            {name}: {value}
                          </code>
                          <button
                            onClick={() => removeCustomHeader(name)}
                            className="text-red-600 hover:text-red-700 text-xs"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Test & Complete</h3>
                <p className="text-gray-600 mb-4">
                  Test your webhook to ensure it's working properly before saving.
                </p>
              </div>

              {/* Configuration Summary */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Configuration Summary</h4>
                <div className="space-y-2 text-sm">
                  <div><span className="font-medium">URL:</span> {config.webhook_url}</div>
                  <div><span className="font-medium">Auth:</span> {AUTH_TYPES.find(a => a.value === config.auth_type)?.label}</div>
                  <div><span className="font-medium">Format:</span> {config.payload_format.toUpperCase()}</div>
                  <div><span className="font-medium">Timeout:</span> {config.webhook_timeout}s</div>
                  <div><span className="font-medium">Retries:</span> {config.retry_attempts}</div>
                </div>
              </div>

              {/* Test Webhook */}
              <div>
                <button
                  onClick={testWebhook}
                  disabled={loading}
                  className="w-full px-4 py-2 bg-purple-100 text-purple-700 border border-purple-300 rounded-lg hover:bg-purple-200 disabled:opacity-50 flex items-center justify-center"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600 mr-2"></div>
                      Testing Webhook...
                    </>
                  ) : (
                    <>🧪 Test Webhook</>
                  )}
                </button>
              </div>

              {/* Test Results */}
              {testResult && (
                <div className={`p-4 rounded-lg border ${
                  testResult.success 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-red-50 border-red-200'
                }`}>
                  {testResult.success ? (
                    <div>
                      <div className="flex items-center text-green-700 font-medium mb-2">
                        <span className="mr-2">✅</span>
                        Webhook Test Successful!
                      </div>
                      <div className="text-sm text-green-600 space-y-1">
                        {testResult.response_status && <div><strong>Response Status:</strong> {testResult.response_status}</div>}
                        {testResult.response_time && <div><strong>Response Time:</strong> {testResult.response_time}ms</div>}
                        <div><strong>Status:</strong> Your webhook is ready to receive notifications</div>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center text-red-700 font-medium mb-2">
                        <span className="mr-2">❌</span>
                        Webhook Test Failed
                      </div>
                      <div className="text-sm text-red-600">
                        {testResult.error}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step Navigation */}
          <div className="flex justify-between items-center pt-6 mt-6 border-t border-gray-200">
            <button
              onClick={prevStep}
              disabled={currentStep === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>

            {currentStep < 4 ? (
              <button
                onClick={nextStep}
                disabled={!validateStep(currentStep)}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            ) : (
              <button
                onClick={saveIntegration}
                disabled={loading || (testResult ? !testResult.success : false)}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Saving...
                  </>
                ) : (
                  <>✓ Complete Setup</>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}