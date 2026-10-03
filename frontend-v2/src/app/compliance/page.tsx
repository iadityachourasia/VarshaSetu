import { notFound } from "next/navigation";
import { PsCoverage } from "@/components/compliance/ps-coverage";
import { SHOW_COMPLIANCE_PAGE } from "@/lib/features";

export default function CompliancePage() {
  if (!SHOW_COMPLIANCE_PAGE) notFound();
  return <PsCoverage />;
}
