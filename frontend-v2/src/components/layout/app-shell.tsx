"use client";

import Link from "next/link";
import { StoryMode } from "@/components/story/story-mode";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { Activity, BookOpenText, ChevronRight, Clock3, CloudRain, Compass, Gauge, MapPinned, Menu, Moon, PanelLeftClose, PanelLeftOpen, Play, RotateCcw, Sun, X, CalendarDays, Layers3, Orbit, Microscope, Network } from "lucide-react";

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

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
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
      return <Link key={href} href={url} className={`nav-link ${selected ? "nav-link-active" : ""}`} aria-label={label} aria-current={selected ? "page" : undefined} title={label} onClick={onNavigate}>
        <Icon size={19} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span>
      </Link>;
    })}</div>)}
  </nav>;
}

function ArchiveCard({ onNavigate }: { onNavigate?: () => void }) {
  return <Link href="/casebook" className="sidebar-foot" aria-label="Browse historical prototype cases" onClick={onNavigate}>
    <Clock3 className="sidebar-foot-icon" size={25} strokeWidth={1.7} aria-hidden="true" />
    <span className="sidebar-foot-copy"><strong>Historical prototype</strong><small>2019 &amp; 2025 cases</small></span>
    <ChevronRight className="sidebar-foot-arrow" size={17} strokeWidth={1.8} aria-hidden="true" />
  </Link>;
}

function ExperimentContextControl() {
  const router = useRouter();
  const pathname = usePathname();
  const search = useSearchParams();
  const experiment = search.get("experiment") === "operational" ? "operational" : "reforecast";
  const year = search.get("year") ?? (experiment === "operational" ? "2025" : "2019");
  const select = (value: string) => {
    const [nextExperiment, nextYear] = value.split(":");
    const route = nextExperiment === "reforecast" && nextYear !== "2019" ? "/observations" : pathname === "/" ? "/forecast" : pathname;
    router.push(`${route}?experiment=${nextExperiment}&year=${nextYear}`);
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
  const trigger = useRef<HTMLButtonElement>(null);
  const close = () => {
    setOpen(false);
    requestAnimationFrame(() => trigger.current?.focus());
  };
  return <>
    <button ref={trigger} type="button" className="present-button" aria-label="Present VarshaSetu" aria-haspopup="dialog" aria-expanded={open} title="Present VarshaSetu" onClick={() => setOpen(true)}><Play className="present-icon" size={16} fill="currentColor" aria-hidden="true" /><span>Present VarshaSetu</span></button>
    {open ? createPortal(<StoryMode onClose={close} />, document.body) : null}
  </>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileMounted, setMobileMounted] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const mobileDrawer = useRef<HTMLElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const openFrame = useRef<number | null>(null);
  const openMobile = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    if (openFrame.current) cancelAnimationFrame(openFrame.current);
    setMobileMounted(true);
    openFrame.current = requestAnimationFrame(() => setMobileOpen(true));
  };
  const closeMobile = (restoreFocus = true) => {
    if (openFrame.current) cancelAnimationFrame(openFrame.current);
    setMobileOpen(false);
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setMobileMounted(false), 260);
    if (restoreFocus) menuButton.current?.focus();
  };
  useEffect(() => () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    if (openFrame.current) cancelAnimationFrame(openFrame.current);
  }, []);
  useEffect(() => {
    if (!mobileOpen) return;
    const priorOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMobile();
      if (event.key === "Tab" && mobileDrawer.current) {
        const focusables = [...mobileDrawer.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')];
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    const onResize = () => { if (window.innerWidth > 760) closeMobile(false); };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = priorOverflow;
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("resize", onResize);
    };
  }, [mobileOpen]);
  return <div className={`app-shell ${sidebarExpanded ? "sidebar-expanded" : ""}`}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="sidebar" id="primary-sidebar">
      <div className="sidebar-brand-control">
        <button type="button" className="sidebar-brand-toggle" aria-label={sidebarExpanded ? "Collapse navigation" : "Expand navigation"} aria-expanded={sidebarExpanded} aria-controls="primary-sidebar" onClick={() => setSidebarExpanded((expanded) => !expanded)} title={sidebarExpanded ? "Collapse navigation" : "Expand navigation"}>
          <span className="brand-symbol sidebar-toggle-logo" aria-hidden="true" />
          {sidebarExpanded ? <PanelLeftClose className="sidebar-toggle-icon" size={22} strokeWidth={1.8} aria-hidden="true" /> : <PanelLeftOpen className="sidebar-toggle-icon" size={22} strokeWidth={1.8} aria-hidden="true" />}
        </button>
        <Link href="/" className="sidebar-brand-name" aria-label="VarshaSetu overview">VarshaSetu<small>MONSOON INTELLIGENCE</small></Link>
      </div>
      <Suspense fallback={<nav className="nav-list" aria-label="Primary" />}><Navigation /></Suspense>
      <ArchiveCard />
    </aside>
    <div className="mobile-app-bar">
      <button ref={menuButton} type="button" className="mobile-menu-button" aria-label="Open navigation" aria-expanded={mobileOpen} aria-controls="mobile-sidebar" onClick={openMobile}><Menu size={20} aria-hidden="true" /></button>
      <Link href="/" className="brand" aria-label="VarshaSetu overview"><span className="brand-mark brand-symbol" aria-hidden="true" /><span className="brand-word">VarshaSetu<small>MONSOON INTELLIGENCE</small></span><span className="mobile-brand-context" aria-hidden="true"><span className="mobile-brand-mark brand-symbol" /><strong>VarshaSetu</strong><span className="mobile-brand-slash">/</span><span className="mobile-brand-descriptor">Scientific workspace</span></span></Link>
    </div>
    {mobileMounted ? <><button type="button" tabIndex={-1} className="mobile-nav-backdrop" data-open={mobileOpen} aria-label="Close navigation" aria-hidden={!mobileOpen} inert={!mobileOpen} onClick={() => closeMobile()} /><aside ref={mobileDrawer} className="mobile-sidebar" data-open={mobileOpen} id="mobile-sidebar" role="dialog" aria-modal="true" aria-label="Mobile navigation" aria-hidden={!mobileOpen} inert={!mobileOpen}><div className="mobile-sidebar-top"><div className="mobile-sidebar-brand"><span className="drawer-brand-mark brand-symbol" aria-hidden="true" /><span className="brand-word">VarshaSetu<small>MONSOON INTELLIGENCE</small></span></div><button ref={closeButton} type="button" className="mobile-menu-button" aria-label="Close navigation" onClick={() => closeMobile()}><X size={20} aria-hidden="true" /></button></div><Suspense fallback={<nav className="nav-list" aria-label="Primary" />}><Navigation onNavigate={() => closeMobile(false)} /></Suspense><ArchiveCard onNavigate={() => closeMobile(false)} /></aside></> : null}
    <div className="app-main">
      <header className="global-header"><div className="header-context"><div className="header-brandline"><span className="header-brand-logo brand-symbol" aria-hidden="true" /><span className="header-brand-copy"><Link href="/" aria-label="Return to VarshaSetu overview"><span>Varsha</span><span>Setu</span></Link><span className="header-brand-slash" aria-hidden="true">/</span><span>Scientific workspace</span></span></div></div><div className="header-actions"><Suspense fallback={null}><ExperimentContextControl /></Suspense><Link href="/forecast?demo=official" className="reset-demo-link" aria-label="Reset Demo" title="Restore the official experiment, year, case, and lead"><RotateCcw className="reset-demo-icon" size={17} aria-hidden="true" /><span>Reset Demo</span></Link><PresentButton /><ThemeToggle /></div></header>
      <main id="main-content">{children}</main>
    </div>
  </div>;
}
