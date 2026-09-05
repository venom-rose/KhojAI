import { Link, useLocation } from "wouter";
import { useEffect, useState } from "react";
import { ArrowUpRight, Check, ChevronDown, Compass, Heart, Instagram, Linkedin, Menu, MoveUpRight, Search, ShieldCheck, Sparkles, X } from "lucide-react";
import { Destination, destinations } from "@/data/destinations";

export function Logo({ inverse = false }: { inverse?: boolean }) {
  return (
    <Link href="/" className={`group inline-flex items-center gap-3 ${inverse ? "text-white" : "text-ink"}`} aria-label="Hidden India AI home">
      <span className="relative grid size-9 place-items-center rounded-full border border-current/25 font-mono text-[11px] font-bold tracking-[-0.08em] transition-transform duration-200 group-hover:rotate-[-8deg]">HI<span className="absolute -right-0.5 -top-0.5 size-1.5 rounded-full bg-saffron" /></span>
      <span className="leading-none"><span className="block font-display text-[20px] font-semibold tracking-[-0.04em]">hidden india</span><span className="mt-1 block font-mono text-[9px] uppercase tracking-[0.26em] text-current/55">artificial intelligence</span></span>
    </Link>
  );
}

import { useAuth } from "@/contexts/AuthContext";
import { FolderLock, LogOut, MessageSquareText, User } from "lucide-react";

export function SiteHeader({ dark = false }: { dark?: boolean }) {
  const [location] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();

  useEffect(() => { const onScroll = () => setScrolled(window.scrollY > 28); window.addEventListener("scroll", onScroll); return () => window.removeEventListener("scroll", onScroll); }, []);
  const nav = [{ href: "/discover", label: "Discover" }, { href: "/planner", label: "AI Trip Planner" }, { href: "/community", label: "Community" }, { href: "/about", label: "About" }];
  const inverse = dark && !scrolled;

  const openSearch = () => window.dispatchEvent(new CustomEvent("khojai:open_search"));
  const openChat = () => window.dispatchEvent(new CustomEvent("khojai:open_chat"));
  const openVault = () => window.dispatchEvent(new CustomEvent("khojai:open_vault"));
  const openAuth = () => window.dispatchEvent(new CustomEvent("khojai:open_auth"));

  return (
    <header className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${scrolled ? "border-b border-line/70 bg-paper/92 text-ink shadow-[0_8px_30px_rgba(30,35,25,0.06)] backdrop-blur-xl" : inverse ? "bg-transparent text-white" : "border-b border-line/70 bg-paper/92 text-ink backdrop-blur-xl"}`}>
      <div className="container flex h-[76px] items-center justify-between gap-4">
        <Logo inverse={inverse} />
        
        {/* Navigation links */}
        <nav className="hidden items-center gap-6 lg:flex" aria-label="Primary navigation">
          {nav.map((item) => <Link key={item.href} href={item.href} className={`relative py-2 text-[13px] font-medium transition-colors ${location === item.href ? "text-saffron" : inverse ? "text-white/75 hover:text-white" : "text-ink/65 hover:text-ink"}`}>{item.label}{location === item.href && <span className="absolute -bottom-1 left-0 h-px w-full bg-saffron" />}</Link>)}
        </nav>

        {/* Global Action Bar */}
        <div className="hidden items-center gap-2.5 md:flex">
          {/* Omnisearch trigger */}
          <button
            type="button"
            onClick={openSearch}
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              inverse
                ? "border-white/20 bg-white/10 text-white/80 hover:bg-white/20 hover:text-white"
                : "border-line bg-white text-ink/70 hover:border-ink/25 hover:text-ink shadow-sm"
            }`}
            title="Global Search (⌘K)"
          >
            <Search size={13} />
            <span>Search</span>
            <kbd className="rounded bg-black/10 px-1 py-0.5 font-mono text-[9px] opacity-60">⌘K</kbd>
          </button>

          {/* RAG Vault trigger */}
          <button
            type="button"
            onClick={openVault}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition ${
              inverse ? "text-white/75 hover:text-white" : "text-ink/65 hover:text-ink"
            }`}
            title="Field Vault & Documents"
          >
            <FolderLock size={13} />
            <span>Vault</span>
          </button>

          {/* Travel AI Chat trigger */}
          <button
            type="button"
            onClick={openChat}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              inverse
                ? "border-saffron-light/30 bg-saffron/20 text-saffron-light hover:bg-saffron/30"
                : "border-saffron/30 bg-saffron/10 text-saffron hover:bg-saffron/20"
            }`}
          >
            <Sparkles size={13} />
            <span>AI Copilot</span>
          </button>

          {/* Plan trip button */}
          <Link href="/planner" className="inline-flex items-center gap-1.5 rounded-full bg-saffron px-3.5 py-2 text-[12px] font-semibold text-white shadow-[0_8px_20px_rgba(197,101,58,0.18)] transition hover:-translate-y-0.5 hover:bg-[#b95a36]">
            Plan trip <ArrowUpRight size={13} />
          </Link>

          {/* Auth Button */}
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2 pl-1">
              <div 
                className="flex items-center gap-1.5 rounded-full border border-line bg-white/80 px-2.5 py-1 text-xs text-ink"
                title={`Signed in as ${user.email}`}
              >
                <span className="grid size-5 place-items-center rounded-full bg-olive text-[10px] font-bold text-white">
                  {(user.fullName || user.email)[0].toUpperCase()}
                </span>
                <span className="max-w-[80px] truncate text-[11px] font-medium">
                  {user.fullName?.split(" ")[0] || "User"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => logout()}
                className="rounded-full p-1.5 text-ink/40 hover:bg-red-50 hover:text-red-600 transition"
                title="Sign Out"
              >
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={openAuth}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition ${
                inverse
                  ? "border-white/30 text-white hover:bg-white/10"
                  : "border-line bg-white text-ink hover:border-ink/40"
              }`}
            >
              Sign In
            </button>
          )}
        </div>

        {/* Mobile menu trigger */}
        <div className="flex items-center gap-2 lg:hidden">
          <button
            type="button"
            onClick={openSearch}
            className="rounded-full border border-current/20 p-2"
            aria-label="Search"
          >
            <Search size={16} />
          </button>
          <button
            type="button"
            className="rounded-full border border-current/20 p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div id="mobile-navigation" className="border-t border-line bg-paper px-5 pb-5 pt-3 text-ink lg:hidden">
          <nav className="flex flex-col" aria-label="Mobile navigation">
            {nav.map((item) => (
              <Link key={item.href} href={item.href} onClick={() => setMobileOpen(false)} className="border-b border-line py-3 text-sm font-medium">
                {item.label}
              </Link>
            ))}
            <Link href="/contribute" onClick={() => setMobileOpen(false)} className="border-b border-line py-3 text-sm font-medium">
              Contribute
            </Link>
            <div className="flex gap-2 py-3">
              <button
                type="button"
                onClick={() => { setMobileOpen(false); openChat(); }}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-full border border-saffron/30 bg-saffron/10 py-2.5 text-xs font-semibold text-saffron"
              >
                <Sparkles size={14} /> AI Copilot
              </button>
              <button
                type="button"
                onClick={() => { setMobileOpen(false); openVault(); }}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-full border border-line bg-white py-2.5 text-xs font-semibold text-ink"
              >
                <FolderLock size={14} /> Field Vault
              </button>
            </div>
            {isAuthenticated ? (
              <div className="flex items-center justify-between border-t border-line pt-3">
                <span className="text-xs text-ink/70">Signed in as <strong>{user?.email}</strong></span>
                <button
                  type="button"
                  onClick={() => { logout(); setMobileOpen(false); }}
                  className="text-xs font-semibold text-red-600"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => { setMobileOpen(false); openAuth(); }}
                className="mt-2 w-full rounded-full border border-line bg-white py-2.5 text-xs font-semibold text-ink"
              >
                Sign In
              </button>
            )}
            <Link href="/planner" onClick={() => setMobileOpen(false)} className="mt-2 inline-flex items-center justify-center gap-2 rounded-full bg-saffron px-4 py-3 text-sm font-semibold text-white">
              Plan my trip <ArrowUpRight size={15} />
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}

export function SectionKicker({ children, light = false }: { children: React.ReactNode; light?: boolean }) { return <div className={`mb-5 flex items-center gap-2 font-mono text-[10px] font-semibold uppercase tracking-[0.24em] ${light ? "text-saffron-light" : "text-saffron"}`}><span className="size-1.5 rounded-full bg-current" />{children}</div>; }

export function ArrowLink({ href, children, light = false }: { href: string; children: React.ReactNode; light?: boolean }) { return <Link href={href} className={`group inline-flex items-center gap-2 text-sm font-semibold ${light ? "text-white" : "text-ink"}`}>{children}<span className={`grid size-7 place-items-center rounded-full border transition group-hover:translate-x-1 ${light ? "border-white/25" : "border-ink/20"}`}><MoveUpRight size={13} /></span></Link>; }

export function TrustScore({ score, compact = false }: { score: number; compact?: boolean }) {
  return <div className={`flex items-center gap-2 ${compact ? "" : "rounded-full border border-line bg-paper/80 px-3 py-1.5"}`}><span className="grid size-7 place-items-center rounded-full bg-olive text-[10px] font-bold text-white">{score}</span><span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink/55">Trust score</span></div>;
}

export function DestinationCard({ destination, featured = false }: { destination: Destination; featured?: boolean }) {
  return <Link href={`/destination/${destination.slug}`} className={`group block ${featured ? "md:col-span-2" : ""}`}><article className="overflow-hidden rounded-[24px] border border-line bg-white shadow-[0_18px_50px_rgba(26,31,23,0.05)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_24px_60px_rgba(26,31,23,0.11)]"><div className={`${featured ? "aspect-[1.65]" : "aspect-[1.12]"} relative overflow-hidden bg-mist`}><img src={destination.image} alt={`${destination.name}, ${destination.state}`} className="h-full w-full object-cover transition duration-700 group-hover:scale-105" /><div className="absolute inset-0 bg-gradient-to-t from-black/55 via-transparent to-black/5" /><div className="absolute left-4 top-4 rounded-full border border-white/30 bg-black/15 px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-white backdrop-blur-md">{destination.region}</div><div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-3 text-white"><div><p className="mb-1 text-[11px] font-medium text-white/70">{destination.state}</p><h3 className={`font-display font-medium leading-none tracking-[-0.03em] ${featured ? "text-3xl md:text-4xl" : "text-2xl"}`}>{destination.name}</h3></div><span className="grid size-9 place-items-center rounded-full bg-white/15 backdrop-blur-md transition group-hover:bg-saffron"><ArrowUpRight size={15} /></span></div></div><div className="space-y-3 p-4"><div className="flex flex-wrap gap-1.5">{destination.tags.slice(0, 2).map((tag) => <span key={tag} className="rounded-full bg-mist px-2.5 py-1 text-[10px] font-medium text-ink/60">{tag}</span>)}</div><p className="line-clamp-2 text-sm leading-6 text-ink/65">{destination.description}</p><div className="flex items-center justify-between border-t border-line pt-3 text-[11px] text-ink/50"><span>Best {destination.bestSeason}</span><span className="flex items-center gap-2"><span>{destination.budget}</span><TrustScore score={destination.trustScore} compact /></span></div></div></article></Link>;
}

export function TrustBreakdown({ score, metrics }: { score: number; metrics: Destination["trustMetrics"] }) {
  const rows = [["Source quality", metrics.sourceQuality], ["Recency", metrics.recency], ["Community agreement", metrics.communityAgreement], ["Completeness", metrics.completeness]] as const;
  return <div className="rounded-[24px] border border-line bg-white p-6 shadow-[0_16px_45px_rgba(26,31,23,0.04)]"><div className="flex items-end justify-between gap-4 border-b border-line pb-5"><div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink/45">Destination trust score</p><div className="mt-2 flex items-baseline gap-2"><span className="font-display text-6xl tracking-[-0.07em] text-ink">{score}</span><span className="text-sm text-ink/45">/ 100</span></div></div><div className="rounded-full bg-olive/10 px-3 py-1.5 text-[11px] font-semibold text-olive"><ShieldCheck size={13} className="mr-1 inline" /> Excellent confidence</div></div><div className="space-y-4 pt-5">{rows.map(([label, value]) => <div key={label}><div className="mb-1.5 flex justify-between text-[11px] font-medium"><span className="text-ink/65">{label}</span><span className="text-ink">{value}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-mist"><div className="h-full rounded-full bg-olive" style={{ width: `${value}%` }} /></div></div>)}</div><p className="mt-5 text-[11px] leading-5 text-ink/45">Demo signal model combining source quality, recency, community agreement and information completeness.</p></div>;
}

export function MapMock() {
  return <div className="relative min-h-[420px] overflow-hidden rounded-[24px] border border-line bg-[#edf0e8] p-5"><div className="absolute inset-0 opacity-60" style={{ backgroundImage: "linear-gradient(rgba(80,100,70,.12) 1px, transparent 1px), linear-gradient(90deg, rgba(80,100,70,.12) 1px, transparent 1px)", backgroundSize: "42px 42px" }} /><svg viewBox="0 0 300 430" className="absolute left-1/2 top-1/2 h-[90%] -translate-x-1/2 -translate-y-1/2 opacity-25" aria-hidden="true"><path d="M148 12 186 46 193 76 228 105 210 132 234 162 222 197 244 226 214 254 202 290 181 312 184 350 158 380 137 358 121 322 94 296 85 258 63 235 74 207 51 179 67 151 53 128 77 103 86 68 111 49Z" fill="#71815e" /></svg><div className="relative z-10 flex items-center justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink/45">Signal map</p><h3 className="mt-1 font-display text-2xl tracking-[-0.04em]">Where the quiet is</h3></div><span className="rounded-full border border-line bg-white/75 px-3 py-1.5 text-[10px] font-semibold text-ink/55">Demo map view</span></div>{destinations.map((destination) => <div key={destination.slug} className="absolute z-20" style={{ left: destination.coordinates.x, top: destination.coordinates.y }}><div className="group relative"><span className="block size-3 rounded-full border-2 border-white bg-saffron shadow-[0_0_0_5px_rgba(197,101,58,0.2)]" /><span className="pointer-events-none absolute bottom-5 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded-full bg-ink px-2.5 py-1.5 text-[10px] font-semibold text-white shadow-lg group-hover:block">{destination.name}</span></div></div>)}<div className="absolute bottom-5 left-5 right-5 z-10 flex items-center justify-between rounded-full border border-white/80 bg-white/70 px-4 py-2.5 text-[10px] text-ink/55 backdrop-blur"><span className="flex items-center gap-2"><span className="size-2 rounded-full bg-saffron" /> Community signal</span><span>8 places shown</span></div></div>;
}

export function Footer() { return <footer className="bg-ink text-white"><div className="container grid gap-12 py-16 md:grid-cols-[1.4fr_1fr_1fr_1fr] md:py-20"><div><Logo inverse /><p className="mt-6 max-w-xs text-sm leading-7 text-white/55">A community-powered field guide to the India beyond the obvious.</p><div className="mt-7 flex gap-2"><span className="grid size-9 place-items-center rounded-full border border-white/10 text-white/35" aria-label="Instagram not connected" title="Instagram link not connected in this MVP"><Instagram size={15} /></span><span className="grid size-9 place-items-center rounded-full border border-white/10 text-white/35" aria-label="LinkedIn not connected" title="LinkedIn link not connected in this MVP"><Linkedin size={15} /></span></div></div><div><p className="mb-4 font-mono text-[10px] uppercase tracking-[0.2em] text-saffron-light">Explore</p><div className="flex flex-col gap-3 text-sm text-white/60"><Link href="/discover" className="transition hover:text-white">Discover</Link><Link href="/planner" className="transition hover:text-white">AI Trip Planner</Link><Link href="/community" className="transition hover:text-white">Community</Link></div></div><div><p className="mb-4 font-mono text-[10px] uppercase tracking-[0.2em] text-saffron-light">Participate</p><div className="flex flex-col gap-3 text-sm text-white/60"><Link href="/contribute" className="transition hover:text-white">Share a place</Link><Link href="/about" className="transition hover:text-white">How it works</Link><a href="mailto:hello@hiddenindia.ai" className="transition hover:text-white">Say hello</a></div></div><div><p className="mb-4 font-mono text-[10px] uppercase tracking-[0.2em] text-saffron-light">The fine print</p><p className="text-sm leading-6 text-white/45">All destinations and scores are demo content for this MVP. Verify routes, access and local guidance before you travel.</p></div></div><div className="border-t border-white/10"><div className="container flex flex-col gap-3 py-5 text-[11px] text-white/35 sm:flex-row sm:items-center sm:justify-between"><span>© 2026 Hidden India AI · SIH prototype</span><span>Built for slower discovery.</span></div></div></footer>; }

export function Shell({ children, darkHeader = false }: { children: React.ReactNode; darkHeader?: boolean }) { return <div className="min-h-screen bg-paper text-ink"><SiteHeader dark={darkHeader} />{children}<Footer /></div>; }
