"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

export default function IntegrationTroubleshootingPage() {
  const params = useParams();
  const brandId = params.id as string;

  const troubleshootingSteps = {
    wordpress: [
      {
        issue: "Connection test failed",
        solutions: [
          "Verify your WordPress site URL is correct and accessible",
          "Ensure the Application Password was generated correctly",
          "Check that your WordPress username is correct (case-sensitive)",
          "Make sure REST API is enabled on your WordPress site",
          "Verify your WordPress site supports Application Passwords (WordPress 5.6+)"
        ]
      },
      {
        issue: "Publishing permission denied",
        solutions: [
          "Ensure your user account has 'publish_posts' capability",
          "Check that the Application Password has sufficient permissions", 
          "Verify your user role allows publishing (Editor or Administrator)",
          "Test publishing manually from WordPress admin to confirm permissions"
        ]
      },
      {
        issue: "Images not uploading",
        solutions: [
          "Check WordPress upload permissions and file size limits",
          "Verify media library is accessible and has sufficient space",
          "Ensure your user can upload media files",
          "Check WordPress security plugins aren't blocking uploads"
        ]
      }
    ],
    webhook: [
      {
        issue: "Webhook test timeout",
        solutions: [
          "Verify your webhook URL is reachable and responding",
          "Check firewall settings allow incoming webhook requests",
          "Ensure your server responds within the timeout period (30 seconds default)",
          "Test your webhook URL manually with a tool like curl"
        ]
      },
      {
        issue: "Authentication failed",
        solutions: [
          "Double-check your authentication credentials",
          "Verify the authentication method matches your server configuration",
          "For Bearer tokens, ensure the token is active and not expired",
          "For Basic Auth, confirm username and password are correct",
          "For API keys, verify the header name and value are correct"
        ]
      },
      {
        issue: "Webhook returns error status",
        solutions: [
          "Check your server logs for specific error details",
          "Verify your webhook endpoint accepts POST requests",
          "Ensure your payload format (JSON/form data) matches expectations",
          "Check that required headers are being sent correctly",
          "Validate your webhook URL path and parameters"
        ]
      }
    ]
  };

  const generalTips = [
    {
      title: "Network Issues",
      tips: [
        "Check your internet connection stability",
        "Verify DNS resolution for your target domains",
        "Ensure no proxy or VPN is interfering with connections",
        "Test connectivity from your server to the target endpoint"
      ]
    },
    {
      title: "SSL/TLS Issues", 
      tips: [
        "Ensure your target site has a valid SSL certificate",
        "Check that certificate is not expired or self-signed",
        "Verify SSL/TLS version compatibility",
        "Test HTTPS endpoints with SSL verification tools"
      ]
    },
    {
      title: "Rate Limiting",
      tips: [
        "Check if you're hitting API rate limits",
        "Implement exponential backoff for retries",
        "Verify your API plan supports the request volume",
        "Monitor request frequency and adjust accordingly"
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
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
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              🔧
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Integration Troubleshooting
              </h1>
              <p className="text-gray-600">
                Common issues and solutions for channel integrations
              </p>
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Navigation</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <a 
              href="#wordpress" 
              className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                📰
              </div>
              <div>
                <div className="font-medium">WordPress Issues</div>
                <div className="text-sm text-gray-500">Connection, permissions, publishing</div>
              </div>
            </a>
            <a 
              href="#webhook" 
              className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mr-3">
                🔗
              </div>
              <div>
                <div className="font-medium">Webhook Issues</div>
                <div className="text-sm text-gray-500">Connectivity, authentication, timeouts</div>
              </div>
            </a>
          </div>
        </div>

        {/* WordPress Troubleshooting */}
        <div id="wordpress" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center mb-6">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
              📰
            </div>
            <h2 className="text-xl font-semibold text-gray-900">WordPress Integration Issues</h2>
          </div>
          
          <div className="space-y-6">
            {troubleshootingSteps.wordpress.map((step, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <span className="w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-sm mr-2">
                    !
                  </span>
                  {step.issue}
                </h3>
                <div className="ml-8">
                  <h4 className="font-medium text-gray-700 mb-2">Solutions:</h4>
                  <ul className="space-y-2">
                    {step.solutions.map((solution, sIndex) => (
                      <li key={sIndex} className="flex items-start">
                        <span className="w-2 h-2 bg-blue-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                        <span className="text-gray-600">{solution}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Webhook Troubleshooting */}
        <div id="webhook" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center mb-6">
            <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mr-3">
              🔗
            </div>
            <h2 className="text-xl font-semibold text-gray-900">Webhook Integration Issues</h2>
          </div>
          
          <div className="space-y-6">
            {troubleshootingSteps.webhook.map((step, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <span className="w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-sm mr-2">
                    !
                  </span>
                  {step.issue}
                </h3>
                <div className="ml-8">
                  <h4 className="font-medium text-gray-700 mb-2">Solutions:</h4>
                  <ul className="space-y-2">
                    {step.solutions.map((solution, sIndex) => (
                      <li key={sIndex} className="flex items-start">
                        <span className="w-2 h-2 bg-purple-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                        <span className="text-gray-600">{solution}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* General Tips */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center mb-6">
            <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mr-3">
              💡
            </div>
            <h2 className="text-xl font-semibold text-gray-900">General Troubleshooting Tips</h2>
          </div>
          
          <div className="grid md:grid-cols-1 gap-6">
            {generalTips.map((category, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3">{category.title}</h3>
                <ul className="space-y-2">
                  {category.tips.map((tip, tIndex) => (
                    <li key={tIndex} className="flex items-start">
                      <span className="w-2 h-2 bg-green-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                      <span className="text-gray-600">{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Support Contact */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
              📞
            </div>
            <h2 className="text-lg font-semibold text-blue-900">Still Need Help?</h2>
          </div>
          <p className="text-blue-800 mb-4">
            If you're still experiencing issues after trying these solutions, our support team is here to help.
          </p>
          <div className="space-y-2 text-sm text-blue-700">
            <div><strong>Email:</strong> support@100xai.com</div>
            <div><strong>Documentation:</strong> docs.100xai.com/integrations</div>
            <div><strong>Community:</strong> community.100xai.com</div>
          </div>
          <div className="mt-4">
            <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
              Contact Support
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}