"use client";

import Link from "next/link";
import { StoryMode } from "@/components/story/story-mode";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, useSyncExternalStore } from "react";
import { Activity, BookOpenText, CloudRain, Compass, Gauge, MapPinned, Moon, Presentation, Sun, CalendarDays, Layers3, Orbit, Microscope, Network, ShieldCheck } from "lucide-react";

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

/** Phase 5B, section 10-11: collapses the sidebar to its already-existing
 * compact icon rail (reusing the proven <1550px responsive state rather
 * than inventing a new hidden-nav layout, so navigation stays interactive)
 * and declutters the header of non-context controls. Experiment/year
 * context, legends, and limitation labels all live inside page content and
 * are untouched -- this only changes chrome. "P" toggles it globally
 * (guarded against firing while typing in a form control), with a visible
 * Exit affordance always present while active. */
function PresentationViewToggle() {
  const [active, setActive] = useState(false);
  useEffect(() => {
    document.querySelector(".app-shell")?.classList.toggle("presentation-mode", active);
    return () => document.querySelector(".app-shell")?.classList.remove("presentation-mode");
  }, [active]);
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() !== "p" || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) return;
      if (target?.isContentEditable) return;
      setActive((current) => !current);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
  return <button type="button" className={`icon-button presentation-toggle ${active ? "active" : ""}`} onClick={() => setActive((current) => !current)} aria-pressed={active} title="Presentation View (P)">
    <Presentation size={18} aria-hidden="true" /><span>{active ? "Exit Presentation View" : "Presentation View"}</span>
  </button>;
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
      <header className="global-header"><div><span className="global-kicker">VARSHASetu / SCIENTIFIC WORKSPACE</span><span className="global-context">Two separate historical GEFS lineages · no pooled result</span></div><div className="header-actions"><Link href="/forecast?demo=official" className="reset-demo-link" title="Restore the official experiment, year, case, and lead">Reset Demo</Link><PresentationViewToggle /><span className="header-hide-in-presentation"><PresentButton /></span><Suspense fallback={null}><ExperimentContextControl /></Suspense><span className="header-status"><ShieldCheck size={14} aria-hidden="true" /> Historical prototype</span><span className="header-hide-in-presentation"><ThemeToggle /></span></div></header>
      <main id="main-content">{children}</main>
    </div>
  </div>;
}
