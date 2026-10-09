import fs from "node:fs";
import path from "node:path";

import type { Bundle } from "./types";

const BUNDLE = path.join(process.cwd(), "public", "data", "bundle.json");

/**
 * Read the bundle from disk at build time. Static export means this runs once, during
 * `next build`, and the numbers are frozen into the HTML — the same guarantee the ledger makes.
 *
 * The bundle is a build product and is not committed, so a fresh clone hits this first. Fail with
 * the command that fixes it rather than an ENOENT from deep inside the bundler.
 */
export function getBundle(): Bundle {
  try {
    return JSON.parse(fs.readFileSync(BUNDLE, "utf8")) as Bundle;
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    throw new Error(
      [
        `No data bundle at ${BUNDLE}.`,
        "",
        "The UI renders artefacts the Python pipeline produces; it computes nothing itself.",
        "From the repository root:",
        "",
        "    python scripts/showcase.py --fast   # produce runs/ and outputs/",
        "    python scripts/export_web.py        # write web/public/data/",
        "",
        "then run `npm run build` again.",
      ].join("\n"),
    );
  }
}
