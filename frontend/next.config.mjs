/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Produce a self-contained production server (.next/standalone) for small,
  // reliable container images.
  output: "standalone"
};

export default nextConfig;
