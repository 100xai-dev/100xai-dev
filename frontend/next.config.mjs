/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  
  // Enable output file tracing for smaller Docker images (moved from experimental in Next.js 15)
  outputFileTracingRoot: process.cwd(),

  // NOTE: do NOT add a rewrite for /api/v1/* here. /api/* is handled by the
  // BFF route handler at app/api/[...path]/route.ts, which injects the auth
  // token from the cookie. A rewrite would shadow that handler and proxy to the
  // backend with no Authorization header (401 on every authenticated call).
};

export default nextConfig;
