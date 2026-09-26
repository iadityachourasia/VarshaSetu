"use client";

import Link from "next/link";
import { StoryMode } from "@/components/story/story-mode";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, useSyncExternalStore } from "react";
import { Activity, BookOpenText, CloudRain, Compass, Gauge, MapPinned, Moon, Sun, CalendarDays, Layers3, Orbit, Microscope, Network, ShieldCheck } from "lucide-react";

const navigation = [
  { group: "ANALYSIS", items: [
    { href: "/", label: "Overview", icon: Gauge },
    { href: "/forecast", label: "Forecast & Atmosphere", icon: Compass },
    { href: "/casebook", label: "Event Casebook", icon: CalendarDays },
    { href: "/extremes", label: "Extreme Rain", icon: CloudRain },
  ] },
  { group: "INTELLIGENCE", items: [
    { href: "/ensemble", label: "Ensemble & Uncertainty", icon: Layers3 },
    { href: "/regimes", label: "Regime Intelligence", icon: Orbit },
    { href: "/districts", label: "District Intelligence", icon: MapPinned },
  ] },
  { group: "SCIENCE", items: [
    { href: "/verification", label: "Verification Lab", icon: Activity },
    { href: "/observations", label: "Six-Season Observations", icon: CalendarDays },
    { href: "/quality", label: "Data Quality & Provenance", icon: Network },
    { href: "/methodology", label: "Data & Methodology", icon: BookOpenText },
    { href: "/audit", label: "Scientific Audit", icon: Microscope },
  ] },
];

function Navigation() {
  const pathname = usePathname();
  const search = useSearchParams();
  const caseId = search.get("case");
  const experiment = search.get("experiment") === "operational" ? "operational" : "reforecast";
  const year = search.get("year") ?? (experiment === "operational" ? "2025" : "2019");
  return <nav aria-label="Primary" className="nav-list">
    {navigation.map(({ group, items }) => <div key={group} className="nav-group"><span className="nav-group-label">{group}</span>{items.map(({ href, label, icon: Icon }) => {
      const selected = pathname === href;
      const context = ["/forecast", "/casebook", "/extremes", "/ensemble", "/regimes", "/districts", "/verification", "/observations"].includes(href);
      const params = new URLSearchParams();
      if (context) { params.set("experiment", experiment); params.set("year", year); }
      if (context && caseId) params.set("case", caseId);
      const url = params.size ? `${href}?${params.toString()}` : href;
      return <Link key={href} href={url} className={`nav-link ${selected ? "nav-link-active" : ""}`} aria-current={selected ? "page" : undefined} title={label}>
        <Icon size={19} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span>
      </Link>;
    })}</div>)}
  </nav>;
}

function ExperimentContextControl() {
  const pathname = usePathname();
  const search = useSearchParams();
  const experiment = search.get("experiment") === "operational" ? "operational" : "reforecast";
  const year = search.get("year") ?? (experiment === "operational" ? "2025" : "2019");
  const select = (value: string) => {
    const [nextExperiment, nextYear] = value.split(":");
    const route = nextExperiment === "reforecast" && nextYear !== "2019" ? "/observations" : pathname === "/" ? "/forecast" : pathname;
    window.location.assign(`${route}?experiment=${nextExperiment}&year=${nextYear}`);
  };
  return <label className="global-experiment-control"><span>EXPERIMENT / YEAR</span><select aria-label="Experiment and year" value={`${experiment}:${year}`} onChange={(event) => select(event.target.value)}>
    <optgroup label="GEFSv12 Reforecast"><option value="reforecast:2017">2017 · Train</option><option value="reforecast:2018">2018 · Validate</option><option value="reforecast:2019">2019 · Test</option></optgroup>
    <optgroup label="Historical Operational GEFS"><option value="operational:2023">2023 · Cross-fit</option><option value="operational:2024">2024 · Validate</option><option value="operational:2025">2025 · Final test</option></optgroup>
  </select></label>;
}

function ThemeToggle() {
  const light = useSyncExternalStore(
    (callback) => {
      window.addEventListener("storage", callback);
      window.addEventListener("varshasetu-theme", callback);
      return () => { window.removeEventListener("storage", callback); window.removeEventListener("varshasetu-theme", callback); };
    },
    () => window.localStorage.getItem("varshasetu-theme") === "light",
    () => false,
  );
  useEffect(() => {
    document.documentElement.classList.toggle("dark", !light);
  }, [light]);
  function toggle() {
    const next = !light;
    document.documentElement.classList.toggle("dark", !next);
    window.localStorage.setItem("varshasetu-theme", next ? "light" : "dark");
    window.dispatchEvent(new Event("varshasetu-theme"));
  }
  return <button className="icon-button theme-button" type="button" onClick={toggle} aria-label={light ? "Use dark theme" : "Use light theme"} title={light ? "Use dark theme" : "Use light theme"}>
    {light ? <Moon size={18} aria-hidden="true" /> : <Sun size={18} aria-hidden="true" />}
  </button>;
}

function PresentButton() {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" className="present-button" onClick={() => setOpen(true)}>Present VarshaSetu</button>
    {open ? <StoryMode onClose={() => setOpen(false)} /> : null}
  </>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="sidebar">
      <Link href="/" className="brand" aria-label="VarshaSetu overview"><span className="brand-mark" aria-hidden="true">V</span><span className="brand-word">VarshaSetu<small>MONSOON INTELLIGENCE</small></span></Link>
      <Suspense fallback={<nav className="nav-list" aria-label="Primary" />}><Navigation /></Suspense>
      <div className="sidebar-foot"><span className="status-dot" aria-hidden="true" /> Historical prototype</div>
    </aside>
    <div className="app-main">
      <header className="global-header"><div><span className="global-kicker">VARSHASetu / SCIENTIFIC WORKSPACE</span><span className="global-context">Two separate historical GEFS lineages · no pooled result</span></div><div className="header-actions"><PresentButton /><Suspense fallback={null}><ExperimentContextControl /></Suspense><span className="header-status"><ShieldCheck size={14} aria-hidden="true" /> Historical prototype</span><ThemeToggle /></div></header>
      <main id="main-content">{children}</main>
    </div>
  </div>;
}
