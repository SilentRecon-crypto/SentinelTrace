import { Link } from "react-router-dom";
import {
  ShieldCheck,
  UserRound,
  FileWarning,
  Network,
  UserRoundSearch,
  Target,
  MapPinned,
  Compass,
  FolderSearch,
  ArrowRight,
  ChevronDown,
} from "lucide-react";
import { NetworkBackground } from "@/components/landing/NetworkBackground";
import { SentinelMark } from "@/components/layout/SentinelMark";
import { ROUTES } from "@/routes";

const PIPELINE = [
  { icon: FileWarning, label: "Cybercrime Complaint" },
  { icon: Network, label: "Transaction / Network Analysis" },
  { icon: UserRoundSearch, label: "Suspicious Account Identification" },
  { icon: Target, label: "Predictive Analytics" },
  { icon: MapPinned, label: "Likely Cash-Out Location Intelligence" },
  { icon: Compass, label: "Actionable Intervention" },
];

const CAPABILITIES = [
  { icon: FileWarning, title: "Cybercrime Complaint Intelligence", description: "Structures raw complaint data into a consistent, investigable record from the moment it's filed." },
  { icon: Network, title: "Transaction Network Analysis", description: "Maps the flow of funds across accounts as an interactive graph, not a flat transaction list." },
  { icon: UserRoundSearch, title: "Suspicious Account Detection", description: "Ranks accounts by hop distance, pass-through behavior, fan-in/out, and network centrality." },
  { icon: Target, title: "Predictive Analytics", description: "Surfaces the accounts and locations most likely to matter before an investigator has to ask." },
  { icon: MapPinned, title: "Cash-Out Location Prediction", description: "Estimates where funds are likely to be physically withdrawn, ranked by confidence." },
  { icon: Compass, title: "Geospatial Intelligence", description: "Places predicted locations on real geography, with the context investigators need at a glance." },
  { icon: FolderSearch, title: "Actionable Investigation Support", description: "Brings complaints, accounts, networks, and locations into one working case file." },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[color:var(--color-void)] text-[color:var(--color-text-primary)]">
      {/* Top bar */}
      <header className="fixed inset-x-0 top-0 z-30 border-b border-[color:var(--color-border)]/70 bg-[color:var(--color-void)]/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <SentinelMark className="h-6 w-6" />
            <span className="text-[14px] font-semibold tracking-tight">SentinelTrace</span>
          </div>
          <nav className="hidden items-center gap-7 text-[13px] font-medium text-[color:var(--color-text-secondary)] sm:flex">
            <a href="#how-it-works" className="hover:text-[color:var(--color-text-primary)]">How it works</a>
            <a href="#capabilities" className="hover:text-[color:var(--color-text-primary)]">Capabilities</a>
            <a href="#why" className="hover:text-[color:var(--color-text-primary)]">Why it matters</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to={ROUTES.userLogin} className="rounded-sm border border-[color:var(--color-border-strong)] px-3 py-1.5 text-[12.5px] font-medium text-[color:var(--color-text-secondary)] transition-colors hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]">
              User Portal
            </Link>
            <Link to={ROUTES.analystLogin} className="rounded-sm bg-[color:var(--color-signal)] px-3 py-1.5 text-[12.5px] font-semibold text-[#04191c] transition-opacity hover:opacity-90">
              Analyst Login
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative flex min-h-screen items-center overflow-hidden pt-16">
        <NetworkBackground className="absolute inset-0 h-full w-full opacity-70" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[color:var(--color-void)]/20 via-[color:var(--color-void)]/70 to-[color:var(--color-void)]" />

        <div className="relative mx-auto max-w-5xl px-6 py-24 text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/70 px-3.5 py-1.5 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)] backdrop-blur">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[color:var(--color-signal)]" />
            Smart India Hackathon 2026 · Cybercrime Intelligence
          </div>

          <h1 className="text-[44px] font-semibold leading-[1.05] tracking-tight sm:text-[64px]">SentinelTrace</h1>
          <p className="mt-3 text-[18px] font-medium text-[color:var(--color-signal)] sm:text-[22px]">Predict. Trace. Intervene.</p>
          <p className="mx-auto mt-5 max-w-2xl text-[14.5px] leading-relaxed text-[color:var(--color-text-secondary)] sm:text-[15.5px]">
            An intelligent predictive analytics platform designed to transform cybercrime complaint data into actionable intelligence for proactive intervention.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to={ROUTES.userLogin}
              className="group flex w-full items-center justify-center gap-2 rounded-sm border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-raised)]/80 px-6 py-3 text-[13.5px] font-semibold text-[color:var(--color-text-primary)] backdrop-blur transition-colors hover:border-[color:var(--color-signal)] sm:w-auto"
            >
              <UserRound className="h-4 w-4 text-[color:var(--color-signal)]" strokeWidth={1.75} />
              Enter User Portal
              <ArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
            </Link>
            <Link
              to={ROUTES.analystLogin}
              className="group flex w-full items-center justify-center gap-2 rounded-sm bg-[color:var(--color-signal)] px-6 py-3 text-[13.5px] font-semibold text-[#04191c] transition-opacity hover:opacity-90 sm:w-auto"
            >
              <ShieldCheck className="h-4 w-4" strokeWidth={1.75} />
              Analyst Login
              <ArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
            </Link>
          </div>

          <p className="mt-6 text-[11px] text-[color:var(--color-text-tertiary)]">Synthetic / demo environment — no real complaint or account data.</p>
        </div>

        <a href="#what-is" className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[color:var(--color-text-tertiary)] transition-colors hover:text-[color:var(--color-signal)]" aria-label="Scroll to learn more">
          <ChevronDown className="h-5 w-5 animate-bounce" strokeWidth={1.5} />
        </a>
      </section>

      {/* What is SentinelTrace */}
      <section id="what-is" className="border-t border-[color:var(--color-border)] px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">What is SentinelTrace?</div>
          <h2 className="text-[26px] font-semibold tracking-tight sm:text-[30px]">From scattered complaints to a working case file</h2>
          <p className="mt-4 text-[14.5px] leading-relaxed text-[color:var(--color-text-secondary)]">
            SentinelTrace is a predictive cybercrime intelligence platform built for investigators and financial-crime analysts. It takes cybercrime
            complaint and transaction data, reconstructs how money moved across accounts, and highlights which accounts and locations deserve
            attention first — so investigation time goes toward the leads most likely to matter.
          </p>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="border-t border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <div className="mb-10 text-center">
            <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">How SentinelTrace Works</div>
            <h2 className="text-[26px] font-semibold tracking-tight sm:text-[30px]">One pipeline, from report to intervention</h2>
          </div>
          <div className="flex flex-col items-center gap-0">
            {PIPELINE.map((step, i) => (
              <div key={step.label} className="flex w-full max-w-md flex-col items-center">
                <div className="flex w-full items-center gap-3 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] px-4 py-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[color:var(--color-signal-dim)] text-[color:var(--color-signal)]">
                    <step.icon className="h-4 w-4" strokeWidth={1.75} />
                  </span>
                  <span className="text-[13px] font-medium text-[color:var(--color-text-primary)]">{step.label}</span>
                </div>
                {i < PIPELINE.length - 1 && <div className="h-6 w-px bg-[color:var(--color-border-strong)]" />}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Key Capabilities */}
      <section id="capabilities" className="border-t border-[color:var(--color-border)] px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 text-center">
            <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">Key Capabilities</div>
            <h2 className="text-[26px] font-semibold tracking-tight sm:text-[30px]">What the platform does</h2>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {CAPABILITIES.map((c) => (
              <div key={c.title} className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] p-5 transition-colors hover:border-[color:var(--color-border-strong)]">
                <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-sm bg-[color:var(--color-signal-dim)] text-[color:var(--color-signal)]">
                  <c.icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
                </span>
                <h3 className="text-[13.5px] font-semibold text-[color:var(--color-text-primary)]">{c.title}</h3>
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-[color:var(--color-text-secondary)]">{c.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why it matters */}
      <section id="why" className="border-t border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-[color:var(--color-signal)]">Why It Matters</div>
          <h2 className="text-[26px] font-semibold tracking-tight sm:text-[30px]">Reactive investigation is expensive. Proactive intelligence isn't.</h2>
          <p className="mt-4 text-[14.5px] leading-relaxed text-[color:var(--color-text-secondary)]">
            Cybercrime money often clears intermediary accounts within hours. The objective of SentinelTrace is to help investigators move from
            reacting after funds are gone toward acting on ranked, evidence-linked leads while intervention is still possible.
          </p>
          <p className="mt-3 text-[11.5px] text-[color:var(--color-text-tertiary)]">
            This is a research and demonstration platform. It does not make claims about real-world accuracy, deployment status, or law-enforcement outcomes.
          </p>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="border-t border-[color:var(--color-border)] px-6 py-16">
        <div className="mx-auto flex max-w-4xl flex-col items-center gap-6 text-center">
          <h2 className="text-[20px] font-semibold tracking-tight">Choose how you'd like to continue</h2>
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
            <Link to={ROUTES.userLogin} className="flex items-center justify-center gap-2 rounded-sm border border-[color:var(--color-border-strong)] px-6 py-3 text-[13px] font-semibold text-[color:var(--color-text-primary)] hover:border-[color:var(--color-signal)] hover:text-[color:var(--color-signal)]">
              <UserRound className="h-4 w-4" strokeWidth={1.75} /> Enter User Portal
            </Link>
            <Link to={ROUTES.analystLogin} className="flex items-center justify-center gap-2 rounded-sm bg-[color:var(--color-signal)] px-6 py-3 text-[13px] font-semibold text-[#04191c] hover:opacity-90">
              <ShieldCheck className="h-4 w-4" strokeWidth={1.75} /> Analyst Login
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-[color:var(--color-border)] px-6 py-8 text-center">
        <p className="text-[11px] text-[color:var(--color-text-tertiary)]">SentinelTrace · Smart India Hackathon 2026 · Synthetic demo environment</p>
      </footer>
    </div>
  );
}
