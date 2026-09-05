import { useState, useEffect, useRef } from "react";
import { 
  X, 
  UploadCloud, 
  FileText, 
  Trash2, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Search, 
  Send, 
  Sparkles, 
  RefreshCw,
  FileCode,
  FileSpreadsheet
} from "lucide-react";
import { toast } from "sonner";
import { 
  documentService, 
  DocumentItem, 
  DocumentAskResponse 
} from "@/services/documents";
import { extractErrorMessage } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";

interface DocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAuth: () => void;
}

export function DocumentModal({ isOpen, onClose, onOpenAuth }: DocumentModalProps) {
  const { isAuthenticated } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [qaAnswer, setQaAnswer] = useState<DocumentAskResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen && isAuthenticated) {
      loadDocs();
    }
  }, [isOpen, isAuthenticated]);

  const loadDocs = async () => {
    try {
      setLoading(true);
      const res = await documentService.listDocuments();
      setDocuments(res.items);
      if (res.items.length > 0 && !activeDoc) {
        setActiveDoc(res.items[0]);
      }
    } catch (err) {
      toast.error(extractErrorMessage(err, "Failed to load document library"));
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    const allowed = [".pdf", ".txt", ".md", ".csv", ".json"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!allowed.includes(ext)) {
      toast.error(`Unsupported file type: ${ext}. Use PDF, TXT, MD, CSV, or JSON.`);
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      toast.error("File size exceeds maximum 20MB limit.");
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);
      const newDoc = await documentService.uploadDocument(file, {
        onProgress: (pct: number) => setUploadProgress(pct),
      });
      toast.success(`Uploaded ${file.name}`);
      setDocuments((prev) => [newDoc, ...prev]);
      setActiveDoc(newDoc);
      // reload after 2s to catch background chunking/embedding status
      setTimeout(() => loadDocs(), 2000);
    } catch (err) {
      toast.error(extractErrorMessage(err, "Failed to upload document"));
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this document and its embeddings?")) return;
    try {
      await documentService.deleteDocument(docId);
      toast.success("Document deleted");
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      if (activeDoc?.id === docId) {
        setActiveDoc(null);
        setQaAnswer(null);
      }
    } catch (err) {
      toast.error(extractErrorMessage(err, "Failed to delete document"));
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDoc || !question.trim()) return;
    try {
      setAsking(true);
      setQaAnswer(null);
      const res = await documentService.askDocument(activeDoc.id, question.trim());
      setQaAnswer(res);
    } catch (err) {
      toast.error(extractErrorMessage(err, "Failed to query document"));
    } finally {
      setAsking(false);
    }
  };

  if (!isOpen) return null;

  const formatBytes = (bytes?: number) => {
    if (bytes === undefined || bytes === null) return "Unknown size";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  };

  const getFileIcon = (fileType?: string) => {
    if (!fileType) return <FileText className="size-5 text-ink/70" />;
    if (fileType.includes("csv") || fileType.includes("spreadsheet")) return <FileSpreadsheet className="size-5 text-olive" />;
    if (fileType.includes("json") || fileType.includes("code")) return <FileCode className="size-5 text-saffron" />;
    return <FileText className="size-5 text-ink/70" />;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative flex h-[85vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-line bg-paper text-ink shadow-[0_25px_70px_rgba(0,0,0,0.3)]">
        {/* Header */}
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-line bg-white/70 px-6 backdrop-blur">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-full bg-saffron/10 text-saffron">
              <Sparkles size={17} />
            </span>
            <div>
              <h2 className="font-display text-xl tracking-[-0.03em]">Knowledge Vault & Travel Field Guides</h2>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink/45">
                RAG Document Ingestion & Semantic Question-Answering
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadDocs}
              disabled={loading || !isAuthenticated}
              className="rounded-full p-2 text-ink/50 hover:bg-mist hover:text-ink disabled:opacity-30"
              title="Refresh document library"
            >
              <RefreshCw size={17} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-2 text-ink/50 hover:bg-mist hover:text-ink"
              aria-label="Close"
            >
              <X size={19} />
            </button>
          </div>
        </div>

        {/* Content body */}
        {!isAuthenticated ? (
          <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
            <span className="grid size-16 place-items-center rounded-full bg-olive/10 text-olive">
              <UploadCloud size={30} />
            </span>
            <h3 className="mt-4 font-display text-2xl tracking-[-0.03em]">Sign in to Access Your Field Vault</h3>
            <p className="mt-2 max-w-md text-sm text-ink/60">
              Ingest your personal travel notes, offline PDFs, route maps, and guidebooks for AI-powered semantic search and answers.
            </p>
            <button
              type="button"
              onClick={onOpenAuth}
              className="mt-6 rounded-full bg-saffron px-6 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-[#b95a36]"
            >
              Sign In to Your Account
            </button>
          </div>
        ) : (
          <div className="flex flex-1 overflow-hidden">
            {/* Left Sidebar: Upload & Document List */}
            <div className="flex w-80 shrink-0 flex-col border-r border-line bg-white/50">
              {/* Dropzone */}
              <div className="p-4 border-b border-line bg-white">
                <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-line p-5 text-center transition hover:border-saffron hover:bg-saffron/5">
                  <UploadCloud size={24} className="text-saffron" />
                  <span className="mt-2 text-xs font-semibold text-ink">Upload Document / Guide</span>
                  <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.14em] text-ink/40">
                    PDF, TXT, MD, CSV, JSON (max 20MB)
                  </span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.txt,.md,.csv,.json,application/pdf,text/plain,text/markdown,text/csv,application/json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleFileUpload(file);
                    }}
                    disabled={uploading}
                  />
                </label>

                {uploading && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between font-mono text-[10px] text-ink/60">
                      <span>Ingesting & chunking...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-mist">
                      <div
                        className="h-full rounded-full bg-saffron transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Doc List */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                <p className="px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/45">
                  Your Library ({documents.length})
                </p>
                {loading && documents.length === 0 ? (
                  <div className="p-6 text-center text-xs text-ink/50">Loading documents...</div>
                ) : documents.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-line p-6 text-center">
                    <FileText className="mx-auto size-7 text-ink/30" />
                    <p className="mt-2 text-xs text-ink/60">No documents yet.</p>
                    <p className="mt-1 text-[11px] text-ink/40">Upload a field guide to ask questions.</p>
                  </div>
                ) : (
                  documents.map((doc) => {
                    const isSelected = activeDoc?.id === doc.id;
                    const docName = doc.original_filename || doc.title;
                    return (
                      <div
                        key={doc.id}
                        onClick={() => {
                          setActiveDoc(doc);
                          setQaAnswer(null);
                        }}
                        className={`group relative flex cursor-pointer items-start justify-between rounded-xl border p-3 transition ${
                          isSelected
                            ? "border-saffron bg-saffron/10 shadow-sm"
                            : "border-line bg-white hover:border-ink/20"
                        }`}
                      >
                        <div className="flex items-start gap-2.5 overflow-hidden">
                          <div className="mt-0.5 shrink-0">{getFileIcon(doc.mime_type || doc.document_type)}</div>
                          <div className="min-w-0">
                            <p className="truncate text-xs font-semibold text-ink">{docName}</p>
                            <div className="mt-1 flex items-center gap-2 font-mono text-[9px] text-ink/45">
                              <span>{formatBytes(doc.file_size)}</span>
                              <span>•</span>
                              <span>{doc.chunk_count} chunks</span>
                            </div>
                            <div className="mt-1 flex items-center gap-1.5">
                              {doc.status === "ready" ? (
                                <span className="inline-flex items-center gap-1 text-[9px] font-medium text-olive">
                                  <CheckCircle2 size={10} /> Indexed
                                </span>
                              ) : doc.status === "processing" || doc.status === "uploaded" ? (
                                <span className="inline-flex items-center gap-1 text-[9px] font-medium text-saffron">
                                  <Clock size={10} className="animate-spin" /> Processing
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[9px] font-medium text-red-600">
                                  <AlertCircle size={10} /> Failed
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={(e) => handleDelete(doc.id, e)}
                          className="opacity-0 group-hover:opacity-100 rounded-lg p-1.5 text-ink/40 hover:bg-red-50 hover:text-red-600 transition"
                          title="Delete document"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Pane: Selected Doc Details & Ask Q&A */}
            <div className="flex flex-1 flex-col overflow-hidden bg-paper">
              {activeDoc ? (
                <div className="flex flex-1 flex-col overflow-y-auto p-6">
                  {/* Doc Info Card */}
                  <div className="rounded-[22px] border border-line bg-white p-5 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="grid size-11 place-items-center rounded-2xl bg-mist">
                          {getFileIcon(activeDoc.mime_type || activeDoc.document_type)}
                        </div>
                        <div>
                          <h3 className="font-display text-lg tracking-[-0.02em] text-ink">
                            {activeDoc.original_filename || activeDoc.title}
                          </h3>
                          <p className="font-mono text-[10px] text-ink/45">
                            Uploaded {new Date(activeDoc.created_at).toLocaleString()} • {formatBytes(activeDoc.file_size)}
                          </p>
                        </div>
                      </div>
                      <span className="rounded-full bg-olive/10 px-3 py-1 text-[11px] font-semibold text-olive">
                        {activeDoc.chunk_count} Vector Chunks Embedded
                      </span>
                    </div>
                  </div>

                  {/* Ask Question Interface */}
                  <div className="mt-6 flex-1 flex flex-col">
                    <div className="mb-3 flex items-center justify-between">
                      <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-saffron font-semibold">
                        <Sparkles size={14} /> Semantic RAG Question-Answering
                      </div>
                      <span className="text-[11px] text-ink/45">Grounds answers directly in this document</span>
                    </div>

                    {/* Ask Form */}
                    <form onSubmit={handleAsk} className="relative">
                      <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder={`Ask anything about "${activeDoc.original_filename || activeDoc.title}"...`}
                        className="h-12 w-full rounded-2xl border border-line bg-white pl-4 pr-24 text-sm outline-none transition focus:border-saffron shadow-sm"
                        disabled={asking || activeDoc.status !== "ready"}
                      />
                      <button
                        type="submit"
                        disabled={asking || !question.trim() || activeDoc.status !== "ready"}
                        className="absolute right-1.5 top-1.5 inline-flex h-9 items-center gap-1.5 rounded-xl bg-saffron px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-[#b95a36] disabled:opacity-50"
                      >
                        {asking ? <RefreshCw size={13} className="animate-spin" /> : <Send size={13} />}
                        <span>Ask</span>
                      </button>
                    </form>

                    {/* Answer View */}
                    <div className="mt-5 flex-1">
                      {asking ? (
                        <div className="flex flex-col items-center justify-center rounded-2xl border border-line bg-white/70 p-8 text-center">
                          <RefreshCw size={24} className="animate-spin text-saffron" />
                          <p className="mt-3 text-xs font-semibold text-ink">Retrieving relevant chunks & synthesizing response...</p>
                        </div>
                      ) : qaAnswer ? (
                        <div className="space-y-4 rounded-2xl border border-line bg-white p-5 shadow-sm animate-in fade-in duration-300">
                          <div>
                            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink/45">Question</p>
                            <p className="mt-1 text-sm font-semibold text-ink">{qaAnswer.query}</p>
                          </div>
                          <div className="border-t border-line pt-3">
                            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-olive font-semibold">AI Synthesis</p>
                            <div className="mt-2 prose prose-sm max-w-none text-sm leading-relaxed text-ink/80 whitespace-pre-wrap">
                              {qaAnswer.answer}
                            </div>
                          </div>
                          {qaAnswer.sources && qaAnswer.sources.length > 0 && (
                            <div className="border-t border-line pt-3">
                              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink/40">
                                Grounded Sources ({qaAnswer.sources.length} matching excerpts)
                              </p>
                              <div className="mt-2 space-y-2">
                                {qaAnswer.sources.map((src, idx) => (
                                  <div key={idx} className="rounded-xl bg-mist p-3 text-xs text-ink/70">
                                    <div className="flex items-center justify-between font-mono text-[9px] text-ink/40 mb-1">
                                      <span>Chunk {src.chunk_id.slice(0, 8)}</span>
                                      <span>Similarity Score: {Math.round(src.similarity * 100)}%</span>
                                    </div>
                                    <p className="italic">"{src.content}"</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-white/40 p-8 text-center">
                          <Search size={24} className="text-ink/25" />
                          <p className="mt-2 text-xs font-semibold text-ink/60">Ask any question to search this document</p>
                          <p className="mt-1 text-[11px] text-ink/40">
                            KhojAI's RAG pipeline retrieves semantic vector matches to provide cited, accurate answers.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
                  <FileText size={36} className="text-ink/20" />
                  <h3 className="mt-4 font-display text-xl">Select or upload a document</h3>
                  <p className="mt-1 max-w-xs text-xs text-ink/50">
                    Choose an ingested field guide from the sidebar to inspect metadata or ask specific questions.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
