/** @type {import('next').NextConfig} */
const nextConfig = {
  // Data files live one level up from the frontend directory
  // Next.js static export — no server needed, works on any static host
  output: 'export',
  trailingSlash: true,
}

module.exports = nextConfig
