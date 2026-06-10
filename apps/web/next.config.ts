import type { NextConfig } from "next";
import path from "path";
import { loadEnvConfig } from "@next/env";

// Load repo-root .env so API routes (e.g. /api/transcribe) get OPENAI_API_KEY
loadEnvConfig(path.resolve(__dirname, "../.."));

const nextConfig: NextConfig = {};

export default nextConfig;
