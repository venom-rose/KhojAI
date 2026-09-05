import { useState, useEffect, useRef } from "react";
import { 
  Search, 
  X, 
  MapPin, 
  FileText, 
  MessageSquare, 
  ArrowRight, 
  Command, 
  Sparkles,
  ShieldCheck,
  RefreshCw
} from "lucide-react";
import { useLocation } from "wouter";
import { searchService, GlobalSearchResponse } from "@/services/search";
import { extractErrorMessage } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";

interface GlobalSearchDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenChatWithConversation?: (id: string) => void;
  onOpenDocument?: () => void;
}

export function GlobalSearchDialog({
  isOpen,
  onClose,
  onOpenChatWithConversation,
  onOpenDocument,
}: GlobalSearchDialogProps) {
  const [, setLocation] = useLocation();
  const { isAuthenticated } = useAuth();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<GlobalSearchResponse | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setResults(null);
    }
  }, [isOpen]);

  // Handle Cmd+K / Ctrl+K keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Open handled by parent or custom event
          window.dispatchEvent(new CustomEvent("khojai:open_search"));
        }
      } else if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Debounced search
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults(null);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const res = await searchService.globalSearch(query.trim(), 5);
        setResults(res);
      } catch (err) {
        console.error("Global search error:", err);
      } finally {
        setLoading(false);
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [query]);

  if (!isOpen) return null;

  const totalHits = (results?.destinations.length ?? 0) + 
                    (results?.documents.length ?? 0) + 
                    (results?.conversations.length ?? 0);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 p-4 pt-20 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-[26px] border border-line bg-paper text-ink shadow-[0_25px_70px_rgba(0,0,0,0.35)]">
        {/* Search Input Bar */}
        <div className="relative flex h-16 shrink-0 items-center border-b border-line bg-white px-4">
          <Search className="size-5 text-ink/40" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search destinations, travel guides, or past conversations..."
            className="h-full flex-1 bg-transparent px-3 text-sm font-medium outline-none placeholder:text-ink/35"
          />
          {loading && <RefreshCw className="size-4 animate-spin text-saffron mr-2" />}
          {query && !loading && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setResults(null);
                inputRef.current?.focus();
              }}
              className="mr-2 rounded-full p-1 text-ink/35 hover:bg-mist hover:text-ink"
            >
              <X size={14} />
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="flex items-center gap-1 rounded-lg border border-line bg-paper px-2 py-1 font-mono text-[10px] text-ink/50 hover:text-ink"
          >
            ESC
          </button>
        </div>

        {/* Results Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {!query.trim() ? (
            <div className="py-12 text-center">
              <span className="inline-grid size-12 place-items-center rounded-full bg-saffron/10 text-saffron">
                <Sparkles size={20} />
              </span>
              <p className="mt-3 font-display text-lg">Omnisearch across KhojAI</p>
              <p className="mt-1 text-xs text-ink/50">
                Type 2 or more letters to search curated destinations, ingested vault files, and AI discussions.
              </p>
              <div className="mt-6 flex justify-center gap-2 font-mono text-[10px] text-ink/40">
                <span className="rounded-md border border-line px-2 py-1">Tip: Try "Ziro", "Mon", "temple", or "route"</span>
              </div>
            </div>
          ) : loading && !results ? (
            <div className="py-12 text-center text-xs text-ink/50">
              Searching across intelligent index...
            </div>
          ) : totalHits === 0 ? (
            <div className="py-12 text-center">
              <p className="font-display text-lg">No matching results found</p>
              <p className="mt-1 text-xs text-ink/50">
                Try searching with alternative keywords or checking your vault documents.
              </p>
            </div>
          ) : (
            <>
              {/* Destinations Section */}
              {results?.destinations && results.destinations.length > 0 && (
                <div>
                  <div className="mb-2 flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/45">
                    <span>Destinations ({results.destinations.length})</span>
                    <span className="text-saffron">Curated Intelligence</span>
                  </div>
                  <div className="space-y-1.5">
                    {results.destinations.map((dest) => (
                      <div
                        key={dest.slug}
                        onClick={() => {
                          onClose();
                          setLocation(`/destination/${dest.slug}`);
                        }}
                        className="group flex cursor-pointer items-center justify-between rounded-xl border border-line/70 bg-white p-3 transition hover:border-saffron hover:bg-saffron/5"
                      >
                        <div className="flex items-center gap-3">
                          <span className="grid size-8 place-items-center rounded-lg bg-mist text-ink/60 group-hover:bg-saffron/10 group-hover:text-saffron">
                            <MapPin size={15} />
                          </span>
                          <div>
                            <p className="text-xs font-semibold text-ink group-hover:text-saffron">
                              {dest.name}
                              <span className="ml-2 font-normal text-ink/45">• {dest.state}, {dest.region}</span>
                            </p>
                            <p className="line-clamp-1 text-[11px] text-ink/55 mt-0.5">
                              {dest.description}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="inline-flex items-center gap-1 rounded-full bg-olive/10 px-2 py-0.5 text-[10px] font-semibold text-olive">
                            <ShieldCheck size={11} /> {dest.trust_score}
                          </span>
                          <ArrowRight size={13} className="text-ink/30 group-hover:text-saffron group-hover:translate-x-0.5 transition" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Ingested Documents Section */}
              {results?.documents && results.documents.length > 0 && (
                <div>
                  <div className="mb-2 flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/45">
                    <span>Field Guides & Vault ({results.documents.length})</span>
                    <span className="text-olive">Vector Chunks</span>
                  </div>
                  <div className="space-y-1.5">
                    {results.documents.map((doc) => (
                      <div
                        key={doc.chunk_id}
                        onClick={() => {
                          onClose();
                          onOpenDocument?.();
                        }}
                        className="group flex cursor-pointer items-center justify-between rounded-xl border border-line/70 bg-white p-3 transition hover:border-olive hover:bg-olive/5"
                      >
                        <div className="flex items-center gap-3">
                          <span className="grid size-8 place-items-center rounded-lg bg-mist text-ink/60 group-hover:bg-olive/10 group-hover:text-olive">
                            <FileText size={15} />
                          </span>
                          <div>
                            <p className="text-xs font-semibold text-ink group-hover:text-olive">
                              {doc.document_title}
                            </p>
                            <p className="line-clamp-1 text-[11px] text-ink/50 mt-0.5">
                              {doc.content || "Vector-indexed document"}
                            </p>
                          </div>
                        </div>
                        <span className="rounded-md bg-paper px-2 py-1 font-mono text-[9px] uppercase tracking-[0.1em] text-ink/45">
                          View Vault
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Past Conversations Section */}
              {results?.conversations && results.conversations.length > 0 && (
                <div>
                  <div className="mb-2 flex items-center justify-between px-2 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/45">
                    <span>Chat Conversations ({results.conversations.length})</span>
                    <span className="text-ink/40">History</span>
                  </div>
                  <div className="space-y-1.5">
                    {results.conversations.map((conv) => (
                      <div
                        key={conv.conversation_id}
                        onClick={() => {
                          onClose();
                          onOpenChatWithConversation?.(conv.conversation_id);
                        }}
                        className="group flex cursor-pointer items-center justify-between rounded-xl border border-line/70 bg-white p-3 transition hover:border-ink/40"
                      >
                        <div className="flex items-center gap-3">
                          <span className="grid size-8 place-items-center rounded-lg bg-mist text-ink/60">
                            <MessageSquare size={15} />
                          </span>
                          <div>
                            <p className="text-xs font-semibold text-ink">
                              {conv.title}
                            </p>
                            <p className="font-mono text-[10px] text-ink/40 mt-0.5">
                              Model: {conv.model} • Updated {new Date(conv.updated_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <ArrowRight size={13} className="text-ink/30 group-hover:translate-x-0.5 transition" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex h-11 shrink-0 items-center justify-between border-t border-line bg-paper px-5 font-mono text-[10px] text-ink/45">
          <div className="flex items-center gap-3">
            <span>Navigation: <kbd className="rounded bg-white px-1.5 py-0.5 border border-line text-ink font-sans">↑</kbd> <kbd className="rounded bg-white px-1.5 py-0.5 border border-line text-ink font-sans">↓</kbd></span>
            <span>Select: <kbd className="rounded bg-white px-1.5 py-0.5 border border-line text-ink font-sans">Enter</kbd></span>
          </div>
          <span>KhojAI Hybrid Search Engine</span>
        </div>
      </div>
    </div>
  );
}
