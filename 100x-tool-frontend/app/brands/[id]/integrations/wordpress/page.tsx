import Link from "next/link";
import { notFound } from "next/navigation";

import { WordPressSetupForm } from "@/components/brand/wordpress-setup-form";
import { getBrand, listIntegrations } from "@/lib/api";
import { isDemoMode } from "@/lib/config";
import { demoBrand } from "@/lib/demo-data";

type PageProps = { params: { id: string } };

export default async function BrandWordpressIntegrationPage({ params }: PageProps) {
  const demo = isDemoMode();

  let brand;
  let siteUrl = "";
  let username = "";
  let status: string | null = null;

<<<<<<< Updated upstream
export default function WordPressSetupPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const brandId = params.id as string;
  const editMode = searchParams.get('edit');
  
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTest | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [config, setConfig] = useState<WordPressConfig>({
    site_url: "",
    username: "",
    password: "",
    auth_type: "application_password",
    custom_post_type: "post",
    default_category: "",
    default_tags: [],
    auto_publish: true,
    featured_image_support: true
  });

  const [oauthNotice, setOauthNotice] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  // Load existing configuration if in edit mode
  useEffect(() => {
    if (editMode) {
      loadExistingConfig();
    }
  }, [editMode]);

  // Surface the result of a WordPress.com OAuth round-trip (set on redirect back).
  useEffect(() => {
    if (searchParams.get("wpcom_connected")) {
      setOauthNotice({ type: "ok", text: "WordPress.com connected successfully. You can now publish to this site." });
    } else if (searchParams.get("wpcom_error")) {
      setOauthNotice({ type: "error", text: `WordPress.com connection failed: ${searchParams.get("wpcom_error")}` });
    }
  }, [searchParams]);

  const loadExistingConfig = async () => {
=======
  if (demo) {
    brand = demoBrand(params.id);
  } else {
>>>>>>> Stashed changes
    try {
      brand = await getBrand(params.id);
    } catch {
      notFound();
    }
    try {
      const data = await listIntegrations(params.id);
      const wp = data.items.find((a) => a.provider === "wordpress");
      if (wp) {
        siteUrl = (wp.config?.site_url as string) ?? "";
        username = (wp.config?.username as string) ?? "";
        status = wp.status;
      }
    } catch {
      /* no existing integration — fresh form */
    }
<<<<<<< Updated upstream
  };

  const saveIntegration = async () => {
    try {
      setLoading(true);
      
      const integrationData = {
        channel_type: "wordpress",
        name: `WordPress - ${new URL(normalizeUrl(config.site_url)).hostname}`,
        config: {
          ...config,
          site_url: normalizeUrl(config.site_url),
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

  const startOAuthFlow = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`/api/v1/integrations/wordpress/oauth/start?brand_id=${brandId}`, {
        headers: { Authorization: `Bearer ${await getValidAccessToken()}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "WordPress.com OAuth is not configured");
      }
      const { authorize_url } = await response.json();
      window.location.href = authorize_url; // hand off to WordPress.com
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start WordPress.com connection");
      setLoading(false);
    }
  };

  if (loading && !config.site_url) {
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
=======
>>>>>>> Stashed changes
  }

  return (
    <div className="stack stack-lg">
      <nav className="breadcrumb">
        <Link href="/brands">Brands</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}`}>{brand.name}</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/brands/${brand.id}/integrations`}>Integrations</Link>
        <span className="breadcrumb-sep">/</span>
        <span style={{ color: "var(--text)", fontWeight: 500 }}>WordPress</span>
      </nav>

<<<<<<< Updated upstream
        {/* Progress Steps */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between">
            {AUTH_STEPS.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep >= step.id 
                    ? 'bg-blue-600 text-white' 
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
                {index < AUTH_STEPS.length - 1 && (
                  <div className={`hidden sm:block w-12 h-px mx-4 ${
                    currentStep > step.id ? 'bg-blue-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {oauthNotice && (
          <div className={`rounded-lg p-4 mb-6 border ${oauthNotice.type === "ok" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
            <p className={oauthNotice.type === "ok" ? "text-green-700" : "text-red-700"}>{oauthNotice.text}</p>
          </div>
        )}

        {/* WordPress.com one-click connect — fastest path for WP.com-hosted sites */}
        {!editMode && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 mb-6 flex items-center justify-between gap-4">
            <div>
              <div className="font-medium text-gray-900">Hosted on WordPress.com?</div>
              <div className="text-sm text-gray-500">Connect instantly with OAuth — no application password needed.</div>
            </div>
            <button
              onClick={startOAuthFlow}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
            >
              Connect with WordPress.com
            </button>
          </div>
        )}

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
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Site Information</h3>
                <p className="text-gray-600 mb-4">
                  Enter your WordPress website URL to begin the connection process.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  WordPress Site URL *
                </label>
              <input
                  type="text"
                  value={config.site_url}
                  onChange={(e) => setConfig(prev => ({ ...prev, site_url: e.target.value }))}
                  onBlur={(e) => {
                    // Auto-prefix https:// when the user leaves the field
                    const val = e.target.value.trim();
                    if (val && !val.startsWith('http://') && !val.startsWith('https://')) {
                      setConfig(prev => ({ ...prev, site_url: 'https://' + val }));
                    }
                  }}
                  placeholder="yoursite.com  or  https://yoursite.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Enter your domain — <code>https://</code> will be added automatically if omitted.
                </p>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Authentication</h3>
                <p className="text-gray-600 mb-4">
                  Choose how you want to authenticate with your WordPress site.
                </p>
              </div>

              {/* Auth Type Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Authentication Method
                </label>
                <div className="space-y-3">
                  <label className="flex items-start space-x-3">
                    <input
                      type="radio"
                      name="auth_type"
                      value="application_password"
                      checked={config.auth_type === "application_password"}
                      onChange={(e) => setConfig(prev => ({ ...prev, auth_type: e.target.value as any }))}
                      className="mt-1"
                    />
                    <div>
                      <div className="font-medium">Application Password (Recommended)</div>
                      <div className="text-sm text-gray-500">
                        Secure authentication using WordPress application passwords
                      </div>
                    </div>
                  </label>
                  <label className="flex items-start space-x-3 opacity-50">
                    <input
                      type="radio"
                      name="auth_type"
                      value="oauth"
                      checked={config.auth_type === "oauth"}
                      onChange={(e) => setConfig(prev => ({ ...prev, auth_type: e.target.value as any }))}
                      disabled
                      className="mt-1"
                    />
                    <div>
                      <div className="font-medium">OAuth (WordPress.com)</div>
                      <div className="text-sm text-gray-500">
                        For WordPress.com-hosted sites — use the “Connect with WordPress.com” button above.
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Application Password Form */}
              {config.auth_type === "application_password" && (
                <div className="space-y-4 p-4 bg-blue-50 rounded-lg">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Username *
                    </label>
                    <input
                      type="text"
                      value={config.username}
                      onChange={(e) => setConfig(prev => ({ ...prev, username: e.target.value }))}
                      placeholder="Your WordPress username"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Application Password *
                    </label>
                    <input
                      type="password"
                      value={config.password}
                      onChange={(e) => setConfig(prev => ({ ...prev, password: e.target.value }))}
                      placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                    />
                    <div className="text-xs text-gray-600 mt-2">
                      <p className="font-medium mb-1">How to create an Application Password:</p>
                      <ol className="list-decimal list-inside space-y-1">
                        <li>Go to your WordPress Dashboard → Users → Profile</li>
                        <li>Scroll down to "Application Passwords"</li>
                        <li>Enter "100xAI Publisher" as the name</li>
                        <li>Click "Add New Application Password"</li>
                        <li>Copy the generated password and paste it above</li>
                      </ol>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Publishing Configuration</h3>
                <p className="text-gray-600 mb-4">
                  Configure how content will be published to your WordPress site.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Post Type
                  </label>
                  <select
                    value={config.custom_post_type}
                    onChange={(e) => setConfig(prev => ({ ...prev, custom_post_type: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="post">Blog Post</option>
                    <option value="page">Page</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Default Category
                  </label>
                  <input
                    type="text"
                    value={config.default_category}
                    onChange={(e) => setConfig(prev => ({ ...prev, default_category: e.target.value }))}
                    placeholder="e.g., Blog, News, Articles"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.auto_publish}
                    onChange={(e) => setConfig(prev => ({ ...prev, auto_publish: e.target.checked }))}
                    className="mr-3"
                  />
                  <span className="text-sm">Auto-publish scheduled content</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.featured_image_support}
                    onChange={(e) => setConfig(prev => ({ ...prev, featured_image_support: e.target.checked }))}
                    className="mr-3"
                  />
                  <span className="text-sm">Include featured images</span>
                </label>
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Test & Complete</h3>
                <p className="text-gray-600 mb-4">
                  Test your connection to ensure everything is working properly.
                </p>
              </div>

              {/* Configuration Summary */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-3">Configuration Summary</h4>
                <div className="space-y-2 text-sm">
                  <div><span className="font-medium">Site:</span> {config.site_url}</div>
                  <div><span className="font-medium">Username:</span> {config.username}</div>
                  <div><span className="font-medium">Auth Method:</span> {config.auth_type === "application_password" ? "Application Password" : "OAuth"}</div>
                  <div><span className="font-medium">Post Type:</span> {config.custom_post_type}</div>
                  <div><span className="font-medium">Auto-publish:</span> {config.auto_publish ? "Yes" : "No"}</div>
                </div>
              </div>

              {/* Test Connection */}
              <div>
                <button
                  onClick={testConnection}
                  disabled={loading}
                  className="w-full px-4 py-2 bg-blue-100 text-blue-700 border border-blue-300 rounded-lg hover:bg-blue-200 disabled:opacity-50 flex items-center justify-center"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                      Testing Connection...
                    </>
                  ) : (
                    <>🔍 Test Connection</>
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
                        Connection Successful!
                      </div>
                      {testResult.site_info && (
                        <div className="text-sm text-green-600 space-y-1">
                          <div><strong>Site:</strong> {testResult.site_info.name}</div>
                          <div><strong>WordPress Version:</strong> {testResult.site_info.wp_version}</div>
                          <div><strong>Publishing Permission:</strong> {testResult.site_info.can_publish ? "✓ Granted" : "❌ Denied"}</div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center text-red-700 font-medium mb-2">
                        <span className="mr-2">❌</span>
                        Connection Failed
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
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
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
=======
      <div>
        <h1 className="page-title">WordPress Integration</h1>
        <p className="page-subtitle">
          Connect a WordPress site so approved drafts publish straight to it via the REST API.
        </p>
>>>>>>> Stashed changes
      </div>

      <WordPressSetupForm
        brandId={brand.id}
        initialSiteUrl={siteUrl}
        initialUsername={username}
        currentStatus={status}
      />
    </div>
  );
}
