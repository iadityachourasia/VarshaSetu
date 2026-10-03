"use client";

import { useToast } from "@/components/ui/toast";

/** A normal download link that also confirms that the download started. It stays a real `<a download>`, so it works without scripts. */
export function DownloadLink({ href, children }: { href: string; children: React.ReactNode }) {
  const toast = useToast();
  return <a href={href} download onClick={() => toast("Download started")}>{children}</a>;
}
