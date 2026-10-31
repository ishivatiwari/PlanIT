import { cpSync } from "node:fs";

// Next's standalone server needs these assets alongside its generated bundle.
cpSync("public", ".next/standalone/public", { recursive: true });
cpSync(".next/static", ".next/standalone/.next/static", { recursive: true });
