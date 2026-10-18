import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: "MitraField: explainer videos, directed by AI",
  description:
    "Describe what you want explained. Ask a question and get a narrated explainer video. An AI director writes the script and picks the right visual for every scene: real math, maps and charts where accuracy matters, Veo and Nano Banana where mood does, narrated in your own cloned voice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geist.variable} ${geistMono.variable}`}>
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
