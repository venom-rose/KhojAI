import { ArrowLeft, Compass } from "lucide-react";
import { Link } from "wouter";

export default function NotFound() { return <main className="grid min-h-screen place-items-center bg-ink px-6 text-white"><div className="max-w-lg text-center"><Compass className="mx-auto text-saffron-light" size={32} /><p className="mt-6 font-mono text-[10px] uppercase tracking-[.25em] text-white/40">404 · Wrong turn</p><h1 className="mt-4 font-display text-6xl tracking-[-.06em]">This path goes nowhere.</h1><p className="mt-4 text-sm leading-6 text-white/55">Let’s take you back to somewhere worth discovering.</p><Link href="/" className="mt-8 inline-flex items-center gap-2 rounded-full bg-saffron px-5 py-3 text-sm font-semibold text-white"><ArrowLeft size={15} /> Return home</Link></div></main>; }
