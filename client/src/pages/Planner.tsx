import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check, CircleHelp, LoaderCircle, Sparkles } from "lucide-react";
import { Link, useLocation } from "wouter";
import { SectionKicker, Shell } from "@/components/site";
import { defaultPreferences, interestOptions, PlannerPreferences } from "@/data/destinations";

const steps = ["Budget", "Time", "Style", "Interests", "Group"];
const processingSteps = [
  "Understanding your travel style...",
  "Finding destinations beyond the usual...",
  "Checking destination intelligence...",
  "Matching experiences...",
  "Optimizing your journey...",
];

export default function Planner() {
  const [, navigate] = useLocation();
  const [step, setStep] = useState(0);
  const [prefs, setPrefs] = useState<PlannerPreferences>(defaultPreferences);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingIndex, setProcessingIndex] = useState(0);

  useEffect(() => {
    if (!isProcessing) return;
    const timer = window.setInterval(() => setProcessingIndex((current) => current + 1), 720);
    return () => window.clearInterval(timer);
  }, [isProcessing]);

  useEffect(() => {
    if (isProcessing && processingIndex >= processingSteps.length) {
      window.sessionStorage.setItem("hidden-india-planner-preferences", JSON.stringify(prefs));
      navigate("/planner/results");
    }
  }, [isProcessing, navigate, prefs, processingIndex]);

  const next = () => {
    if (step === steps.length - 1) {
      setProcessingIndex(0);
      setIsProcessing(true);
    } else {
      setStep((current) => current + 1);
    }
  };

  const update = (key: keyof PlannerPreferences, value: string) => setPrefs((current) => ({ ...current, [key]: value }));

  return <Shell><main className="min-h-screen bg-ink pt-[76px] text-white"><section className="container grid min-h-[calc(100vh-76px)] items-center gap-14 py-16 lg:grid-cols-[.85fr_1.15fr] lg:py-20"><div><Link href="/" className="inline-flex items-center gap-2 text-xs text-white/45 transition hover:text-white"><ArrowLeft size={14} /> Back home</Link><div className="mt-14"><SectionKicker light>AI trip planner · Demo flow</SectionKicker><h1 className="max-w-xl font-display text-6xl leading-[.95] tracking-[-.07em] md:text-8xl">A trip that starts with <em className="text-saffron-light">you.</em></h1><p className="mt-7 max-w-md text-base leading-7 text-white/55">Five quick signals. One considered starting point. No generic package itineraries.</p></div><div className="mt-14 hidden items-center gap-3 text-xs text-white/35 md:flex"><CircleHelp size={15} /> Everything here is mock data for the MVP demo.</div></div><div className="relative overflow-hidden rounded-[28px] border border-white/15 bg-white/[.07] p-5 shadow-[0_30px_80px_rgba(0,0,0,.22)] backdrop-blur-sm md:p-8">{isProcessing ? <ProcessingState processingIndex={Math.min(processingIndex, processingSteps.length - 1)} /> : <><div className="flex items-center justify-between border-b border-white/10 pb-6"><div><p className="font-mono text-[10px] uppercase tracking-[.2em] text-white/45">Your travel brief</p><p className="mt-2 text-sm text-white/70">Let’s make the obvious answer less obvious.</p></div><span className="font-mono text-xs text-saffron-light">0{step + 1} / 05</span></div><div className="mt-7 flex gap-1.5" role="progressbar" aria-label={`Planner progress: step ${step + 1} of ${steps.length}`} aria-valuemin={1} aria-valuemax={steps.length} aria-valuenow={step + 1}>{steps.map((item, index) => <div key={item} className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10"><div className={`h-full rounded-full bg-saffron-light transition-all duration-300 ${index <= step ? "w-full" : "w-0"}`} /></div>)}</div><div className="min-h-[340px] pt-10"><p className="font-mono text-[10px] uppercase tracking-[.2em] text-white/45">Step 0{step + 1}</p><h2 className="mt-3 font-display text-4xl tracking-[-.05em] md:text-5xl">{steps[step] === "Budget" && "What feels comfortable?"}{steps[step] === "Time" && "How much time do you have?"}{steps[step] === "Style" && "What should the days feel like?"}{steps[step] === "Interests" && "What are you curious about?"}{steps[step] === "Group" && "Who is coming along?"}</h2><div className="mt-8 grid gap-3 sm:grid-cols-2">{steps[step] === "Budget" && ["₹8,000", "₹15,000", "₹25,000", "Keep it open"].map((option) => <Option key={option} label={option} selected={prefs.budget === option} onClick={() => update("budget", option)} />)}{steps[step] === "Time" && ["3 days", "5 days", "7 days", "10+ days"].map((option) => <Option key={option} label={option} selected={prefs.days === option} onClick={() => update("days", option)} />)}{steps[step] === "Style" && ["Slow travel", "Outdoors", "Culture-led", "Road trip"].map((option) => <Option key={option} label={option} selected={prefs.style === option} onClick={() => update("style", option)} />)}{steps[step] === "Interests" && interestOptions.map((option) => <Option key={option} label={option} selected={prefs.interests.includes(option)} multi onClick={() => setPrefs((current) => ({ ...current, interests: current.interests.includes(option) ? current.interests.filter((item) => item !== option) : [...current.interests, option] }))} />)}{steps[step] === "Group" && ["Just me", "2 people", "3–5 people", "A small group"].map((option) => <Option key={option} label={option} selected={prefs.group === option} onClick={() => update("group", option)} />)}</div></div><div className="flex items-center justify-between border-t border-white/10 pt-6"><button type="button" disabled={step === 0} onClick={() => setStep((current) => current - 1)} className="inline-flex items-center gap-2 text-sm font-semibold text-white/45 transition hover:text-white disabled:cursor-not-allowed disabled:text-white/20"><ArrowLeft size={15} /> Back</button><button type="button" onClick={next} className="inline-flex items-center gap-2 rounded-full bg-saffron px-5 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-[#b95a36] active:scale-[.98]">{step === steps.length - 1 ? "Find my places" : "Continue"} <ArrowRight size={15} /></button></div></>}</div></section></main></Shell>;
}

function ProcessingState({ processingIndex }: { processingIndex: number }) {
  return <div className="flex min-h-[504px] flex-col justify-between" aria-live="polite" aria-busy="true"><div><div className="flex items-center justify-between border-b border-white/10 pb-6"><div><p className="font-mono text-[10px] uppercase tracking-[.2em] text-saffron-light">Hidden India intelligence</p><p className="mt-2 text-sm text-white/70">Reading the shape of your trip.</p></div><span className="grid size-10 place-items-center rounded-full bg-saffron/15 text-saffron-light"><Sparkles size={17} /></span></div><div className="mt-12 flex items-center gap-4"><span className="grid size-12 place-items-center rounded-full border border-saffron-light/40 bg-saffron/10 text-saffron-light"><LoaderCircle size={22} className="animate-spin" /></span><div><p className="font-display text-3xl tracking-[-.04em]">Building your shortlist</p><p className="mt-1 text-xs text-white/40">Using your preferences, not a generic itinerary.</p></div></div><div className="mt-12 space-y-4">{processingSteps.map((label, index) => <div key={label} className={`flex items-center gap-3 text-sm transition-opacity duration-300 ${index <= processingIndex ? "text-white" : "text-white/25"}`}><span className={`grid size-5 place-items-center rounded-full border ${index < processingIndex ? "border-olive bg-olive text-white" : index === processingIndex ? "border-saffron-light bg-saffron-light text-ink" : "border-white/15"}`}>{index < processingIndex ? <Check size={11} /> : index === processingIndex ? <span className="size-1.5 rounded-full bg-ink" /> : null}</span><span>{label}</span>{index === processingIndex && <span className="ml-auto font-mono text-[9px] uppercase tracking-[.16em] text-saffron-light">working</span>}</div>)}</div></div><div><div className="mb-3 flex items-center justify-between font-mono text-[10px] uppercase tracking-[.18em] text-white/35"><span>Analyzing preference signals</span><span>{Math.min(100, Math.round(((processingIndex + 1) / processingSteps.length) * 100))}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-saffron-light transition-all duration-500" style={{ width: `${Math.min(100, ((processingIndex + 1) / processingSteps.length) * 100)}%` }} /></div></div></div>;
}

function Option({ label, selected, onClick, multi = false }: { label: string; selected: boolean; onClick: () => void; multi?: boolean }) { return <button type="button" aria-pressed={selected} onClick={onClick} className={`flex items-center justify-between rounded-2xl border p-4 text-left transition active:scale-[.99] ${selected ? "border-saffron-light bg-saffron/15 text-white" : "border-white/10 bg-white/[.04] text-white/65 hover:border-white/25 hover:bg-white/[.08]"}`}><span className="flex items-center gap-3"><span className={`grid size-5 place-items-center rounded-full border ${selected ? "border-saffron-light bg-saffron-light text-ink" : "border-white/25"}`}>{selected && <Check size={12} />}</span><span className="text-sm font-medium">{label}</span></span>{multi && <span className="font-mono text-[9px] uppercase tracking-[.16em] text-white/30">multi</span>}</button>; }
