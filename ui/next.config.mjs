/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The demo runs from a laptop with no internet: never reach out at build time.
  images: { unoptimized: true },
  // Static export: `next build` writes a plain folder of files to out/, which
  // deploy/serve.py can host anywhere - a laptop, a container, Nebius AI Cloud.
  // There is no Node server in the demo path.
  output: "export",
  trailingSlash: true,
};

export default nextConfig;
