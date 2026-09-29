import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export function RegimeWorkInProgress() {
  return <div className="page-content regime-development-page">
    <section className="regime-development-stage" aria-labelledby="regime-development-title">
      <h1 id="regime-development-title">Feature in Development</h1>
      <p>This capability is currently under development and will be introduced to <strong>VarshaSetu</strong> in a forthcoming release. Further details will be announced as the feature becomes available.</p>
      <div className="regime-development-footer">
        <span>Regime Intelligence</span>
        <Link href="/">Return to overview <ArrowUpRight size={17} aria-hidden="true" /></Link>
      </div>
    </section>
  </div>;
}
