/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  
  // Enable output file tracing for smaller Docker images (moved from experimental in Next.js 15)
  outputFileTracingRoot: process.cwd(),
  
  // API proxy configuration for backend communication
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
