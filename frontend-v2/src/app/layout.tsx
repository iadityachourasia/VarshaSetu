import type { Metadata } from "next";
import localFont from "next/font/local";
import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "@/components/layout/providers";
import "./globals.css";

const inter = localFont({ src: "../assets/fonts/inter-latin.woff2", weight: "100 900", display: "swap", variable: "--font-geist-sans" });
const jetBrainsMono = localFont({ src: "../assets/fonts/jetbrains-latin.woff2", weight: "100 800", display: "swap", variable: "--font-geist-mono" });

const themeScript = `try{document.documentElement.classList.toggle('dark',localStorage.getItem('varshasetu-theme')!=='light')}catch{document.documentElement.classList.add('dark')}`;

export const metadata: Metadata = {
  title: "VarshaSetu — Monsoon Rainfall Intelligence",
  description: "Historical scientific prototype for GEFS rainfall post-processing and verification.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`dark h-full antialiased ${inter.variable} ${jetBrainsMono.variable}`}
      suppressHydrationWarning
    >
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body className="min-h-full">
        <Providers><AppShell>{children}</AppShell></Providers>
      </body>
    </html>
  );
}
