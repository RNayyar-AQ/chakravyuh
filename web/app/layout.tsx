import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { Nav } from "@/components/Nav";
import { getBundle } from "@/lib/data";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CHAKRAVYUH — policy fuzzing for emergency telecom governance",
  description:
    "A deterministic multi-agent simulator that runs one real disaster under three legal regimes and reports, with citations, which clauses fail.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  const { generated_utc, scenario } = getBundle();
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <footer className="mt-20 border-t border-line">
          <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-7 text-[11.5px] text-faint sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p>
              CHAKRAVYUH · Team Quantum QAI · ITU AI for Good Sandbox Build-a-thon 5.0, New Delhi
            </p>
            <p className="font-mono">
              scenario {scenario.scenario_id} · artefacts built {generated_utc}
            </p>
          </div>
          <div className="mx-auto max-w-7xl px-4 pb-8 text-[11px] leading-relaxed text-faint/80 sm:px-6">
            Simulation output, not legal advice. Every figure on this site was produced by the
            pipeline in this repository and can be regenerated from the seed shown beside it.
          </div>
        </footer>
      </body>
    </html>
  );
}
