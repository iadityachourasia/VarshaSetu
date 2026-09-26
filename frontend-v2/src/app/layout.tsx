import type { Metadata } from "next";
import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "@/components/layout/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "VarshaSetu — Monsoon Rainfall Intelligence",
  description: "Historical scientific prototype for GEFS rainfall post-processing and verification.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className="dark h-full antialiased"
    >
      <body className="min-h-full">
        <Providers><AppShell>{children}</AppShell></Providers>
      </body>
    </html>
  );
}
