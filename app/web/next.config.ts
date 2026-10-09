import type { NextConfig } from "next";

/**
 * Static export. The UI renders artefacts the Python pipeline already wrote; there is no server
 * and no runtime computation, so `next build` produces a folder any judge can open or any host
 * can serve. Determinism end to end: same seed -> same ledger -> same page.
 */
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  turbopack: {
    // Pin the workspace root; otherwise Turbopack walks up past the repo looking for a lockfile.
    root: __dirname,
    rules: { "*.css": { loaders: ["@tailwindcss/turbopack"], as: "*.css" } },
  },
};

export default nextConfig;
