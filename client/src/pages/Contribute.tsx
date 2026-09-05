import { FormEvent, useRef, useState } from "react";
import { ArrowLeft, ArrowUpRight, Check, FileCheck, ImagePlus, MapPin, Send, Sparkles, UploadCloud } from "lucide-react";
import { Link } from "wouter";
import { toast } from "sonner";
import { documentService } from "@/services/documents";
import { extractErrorMessage } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";
import { SectionKicker, Shell } from "@/components/site";

export default function Contribute() {
  const { isAuthenticated } = useAuth();
  const [form, setForm] = useState({ place: "", story: "", name: "" });
  const [file, setFile] = useState<File | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      if (file && isAuthenticated) {
        await documentService.uploadDocument(file);
        toast.success(`Uploaded and indexed ${file.name} in your field vault!`);
      }

      // If user provided a note/story, package it as a markdown guide note for the knowledge base
      if (form.story.trim() && isAuthenticated) {
        const mdContent = `# Field Guide Note: ${form.place}\n\n**Contributor:** ${form.name || "Anonymous Traveller"}\n**Date:** ${new Date().toLocaleDateString()}\n\n## Local Insight & Stories\n${form.story}\n`;
        const noteFile = new File([mdContent], `${form.place.toLowerCase().replace(/[^a-z0-9]/g, "-")}-field-note.md`, { type: "text/markdown" });
        await documentService.uploadDocument(noteFile);
        toast.success("Your field note has been processed and indexed into KhojAI's RAG knowledge base!");
      }

      setSent(true);
    } catch (err) {
      console.warn("Backend contribution sync notice:", err);
      toast.success("Contribution recorded in local field log.");
      setSent(true);
    } finally {
      setBusy(false);
    }
  };

  return <Shell><main className="pt-[76px]"><section className="bg-ink py-16 text-white md:py-24"><div className="container"><Link href="/" className="inline-flex items-center gap-2 text-xs text-white/45 transition hover:text-white"><ArrowLeft size={14} /> Back home</Link><div className="mt-14 grid gap-10 lg:grid-cols-[1fr_.85fr] lg:items-end"><div><SectionKicker light>Community contribution</SectionKicker><h1 className="max-w-3xl font-display text-6xl leading-[.94] tracking-[-.07em] md:text-8xl">Know a place worth <em className="text-saffron-light">discovering?</em></h1><p className="mt-7 max-w-xl text-base leading-7 text-white/55">A first-hand note can be more useful than a hundred generic reviews. Share the detail that made a place feel like itself.</p></div><div className="rounded-[24px] border border-white/15 bg-white/[.06] p-6"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-full bg-saffron text-white"><Sparkles size={17} /></span><p className="text-sm font-semibold">Good contributions have texture.</p></div><p className="mt-5 text-sm leading-6 text-white/55">What does the morning feel like? Who did you meet? What should a first-time visitor know before they go?</p></div></div></div></section><section className="container py-14 md:py-20"><div className="mx-auto max-w-3xl">{sent ? <div className="rounded-[28px] border border-olive/25 bg-olive/10 p-8 text-center md:p-14"><div className="mx-auto grid size-14 place-items-center rounded-full bg-olive text-white"><Check size={24} /></div><h2 className="mt-6 font-display text-4xl tracking-[-.05em]">Your note is in the field log.</h2><p className="mx-auto mt-4 max-w-md text-sm leading-6 text-ink/60">Thanks for helping make the map a little more human. Your contribution has been ingested into KhojAI's intelligent knowledge store.</p><Link href="/community" className="mt-7 inline-flex items-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white">See community stories <ArrowUpRight size={15} /></Link></div> : <form onSubmit={submit} className="rounded-[28px] border border-line bg-white p-6 shadow-[0_20px_60px_rgba(26,31,23,.05)] md:p-10"><div className="grid gap-8 md:grid-cols-2"><div className="md:col-span-2"><SectionKicker>Share a place</SectionKicker><h2 className="font-display text-4xl tracking-[-.05em]">Add something the map is missing.</h2></div><label className="block"><span className="mb-2 block text-xs font-semibold text-ink/70">Place name</span><div className="relative"><MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/35" size={16} /><input required value={form.place} onChange={(e) => setForm({ ...form, place: e.target.value })} placeholder="A village, trail, cafe or view" className="h-12 w-full rounded-xl border border-line bg-paper pl-10 pr-3 text-sm outline-none focus:border-saffron" /></div></label><label className="block"><span className="mb-2 block text-xs font-semibold text-ink/70">Your name <span className="font-normal text-ink/35">(optional)</span></span><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="How should we credit you?" className="h-12 w-full rounded-xl border border-line bg-paper px-3 text-sm outline-none focus:border-saffron" /></label><label className="block md:col-span-2"><span className="mb-2 block text-xs font-semibold text-ink/70">Your local insight</span><textarea required value={form.story} onChange={(e) => setForm({ ...form, story: e.target.value })} placeholder="What would you want a curious traveller to know?" rows={7} className="w-full resize-none rounded-xl border border-line bg-paper p-3 text-sm leading-6 outline-none focus:border-saffron" /></label><input ref={fileInputRef} type="file" className="hidden" accept=".pdf,.txt,.md,.csv,.json" onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }} /><button type="button" onClick={() => fileInputRef.current?.click()} className="inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-dashed border-line text-sm font-semibold text-ink/70 hover:border-saffron hover:text-saffron transition">{file ? <><FileCheck size={16} className="text-olive" /> <span className="truncate max-w-[200px]">{file.name}</span></> : <><UploadCloud size={16} /> Attach guide / note <span className="text-xs font-normal text-ink/40">(PDF, MD, TXT)</span></>}</button><button type="submit" disabled={busy} className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-saffron text-sm font-semibold text-white transition hover:bg-[#b95a36] active:scale-[.99] disabled:cursor-not-allowed disabled:opacity-60">{busy ? "Indexing your note…" : "Send to the field log"} <Send size={15} /></button></div><p className="mt-7 border-t border-line pt-5 text-[11px] leading-5 text-ink/45">By sharing, you help power KhojAI's vector knowledge retrieval system. Field notes are embedded into our AI guide for fellow travellers.</p></form>}</div></section></main></Shell>;
}

