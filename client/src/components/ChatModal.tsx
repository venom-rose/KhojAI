import React, { useEffect, useRef, useState } from "react";
import {
  chatService,
  ChatMessage,
  Conversation,
} from "@/services/chat";
import {
  Bot,
  ChevronLeft,
  Loader2,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
  User as UserIcon,
  X,
} from "lucide-react";
import { toast } from "sonner";

interface ChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialConversationId?: string;
  onOpenAuth?: () => void;
}

export function ChatModal({ isOpen, onClose, initialConversationId, onOpenAuth }: ChatModalProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [selectedModel, setSelectedModel] = useState("khojai-local-v1");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [showThreadList, setShowThreadList] = useState(false);
  const [loading, setLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      if (initialConversationId) {
        setActiveConvId(initialConversationId);
        loadConversation(initialConversationId);
      }
      loadConversations();
    }
  }, [isOpen, initialConversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamedText]);

  const loadConversations = async () => {
    try {
      const res = await chatService.listConversations({ limit: 20 });
      setConversations(res.items);
      if (initialConversationId) {
        // already handled
      } else if (res.items.length > 0 && !activeConvId) {
        loadConversation(res.items[0].id);
      } else if (res.items.length === 0) {
        startNewConversation();
      }
    } catch (err) {
      console.warn("Failed to load conversations:", err);
    }
  };

  const loadConversation = async (id: string) => {
    setLoading(true);
    try {
      const detail = await chatService.getConversation(id);
      setActiveConvId(detail.id);
      setMessages(detail.messages || []);
      if (detail.model) setSelectedModel(detail.model);
      setShowThreadList(false);
    } catch {
      toast.error("Failed to load conversation history.");
    } finally {
      setLoading(false);
    }
  };

  const startNewConversation = async () => {
    setLoading(true);
    try {
      const conv = await chatService.createConversation({
        title: "New Travel Inquiry",
        model: selectedModel,
      });
      setConversations((prev) => [conv, ...prev]);
      setActiveConvId(conv.id);
      setMessages([]);
      setShowThreadList(false);
    } catch {
      toast.error("Could not initialize new conversation.");
    } finally {
      setLoading(false);
    }
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await chatService.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      toast.success("Conversation deleted.");
      if (activeConvId === id) {
        if (remaining.length > 0) {
          loadConversation(remaining[0].id);
        } else {
          startNewConversation();
        }
      }
    } catch {
      toast.error("Failed to delete conversation.");
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPrompt.trim() || isStreaming) return;

    const userText = inputPrompt.trim();
    setInputPrompt("");

    let currentConvId = activeConvId;
    if (!currentConvId) {
      const newConv = await chatService.createConversation({
        title: userText.slice(0, 40),
        model: selectedModel,
      });
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      currentConvId = newConv.id;
    }

    // Optimistically append user message
    const tempUserMsg: ChatMessage = {
      id: "temp-" + Date.now(),
      conversation_id: currentConvId,
      sender_type: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsStreaming(true);
    setStreamedText("");

    // Call SSE streaming
    chatService.streamMessage(
      currentConvId,
      userText,
      {
        onToken: (token) => {
          setStreamedText((prev) => prev + token);
        },
        onDone: (doneData) => {
          const assistantMsg: ChatMessage = {
            id: doneData.message_id,
            conversation_id: currentConvId!,
            sender_type: "assistant",
            content: doneData.content,
            model_name: selectedModel,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreamedText("");
          setIsStreaming(false);
        },
        onError: (err) => {
          toast.error("Streaming interrupted: " + err);
          setIsStreaming(false);
        },
      },
      selectedModel
    );
  };

  const handleRegenerate = async () => {
    if (!activeConvId || isStreaming || messages.length === 0) return;
    setLoading(true);
    try {
      const updatedMsg = await chatService.regenerateMessage(activeConvId, undefined, selectedModel);
      setMessages((prev) => {
        const copy = [...prev];
        for (let i = copy.length - 1; i >= 0; i--) {
          if (copy[i].sender_type === "assistant") {
            copy[i] = updatedMsg;
            break;
          }
        }
        return copy;
      });
      toast.success("Response regenerated.");
    } catch {
      toast.error("Failed to regenerate response.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <div className="relative flex h-full w-full max-w-lg flex-col border-l border-line bg-paper shadow-2xl transition-transform duration-300">
        {/* Drawer Header */}
        <div className="flex h-16 items-center justify-between border-b border-line px-5">
          <div className="flex items-center gap-3">
            {showThreadList ? (
              <button
                type="button"
                onClick={() => setShowThreadList(false)}
                className="rounded-full p-1.5 text-ink/60 hover:bg-mist hover:text-ink"
              >
                <ChevronLeft size={18} />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setShowThreadList(true)}
                className="flex items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1 text-[11px] font-semibold text-ink/70 hover:border-ink hover:text-ink"
              >
                <span>Threads</span>
                <span className="rounded-full bg-saffron/10 px-1.5 py-0.2 font-mono text-[9px] text-saffron">
                  {conversations.length}
                </span>
              </button>
            )}

            <div>
              <p className="flex items-center gap-1.5 font-display text-base font-semibold tracking-tight text-ink">
                <Sparkles size={14} className="text-saffron" />
                KhojAI Field Guide
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Model Selector */}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="rounded-full border border-line bg-white px-2.5 py-1 text-[11px] font-medium text-ink/70 outline-none hover:border-ink"
            >
              <option value="khojai-local-v1">KhojAI Local</option>
              <option value="gemini-1.5-flash">Gemini Flash</option>
              <option value="gpt-4o-mini">GPT-4o mini</option>
            </select>

            <button
              type="button"
              onClick={startNewConversation}
              className="rounded-full p-2 text-ink/50 transition hover:bg-mist hover:text-ink"
              title="New thread"
            >
              <Plus size={18} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-2 text-ink/50 transition hover:bg-mist hover:text-ink"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content Area: Thread List vs Active Chat */}
        {showThreadList ? (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink/40">
                Conversation History
              </span>
              <button
                type="button"
                onClick={startNewConversation}
                className="inline-flex items-center gap-1 rounded-full bg-saffron px-3 py-1 text-xs font-semibold text-white hover:bg-[#b95a36]"
              >
                <Plus size={12} /> New Thread
              </button>
            </div>

            {conversations.length === 0 ? (
              <p className="py-8 text-center text-xs text-ink/40">No saved conversations yet.</p>
            ) : (
              <div className="space-y-2">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className={`group flex cursor-pointer items-center justify-between rounded-2xl border p-3 transition ${
                      activeConvId === conv.id
                        ? "border-saffron bg-white shadow-sm"
                        : "border-line bg-white/60 hover:bg-white"
                    }`}
                  >
                    <div className="min-w-0 flex-1 pr-3">
                      <p className="truncate text-sm font-semibold text-ink">{conv.title}</p>
                      <p className="mt-0.5 text-[10px] text-ink/40">
                        {new Date(conv.updated_at).toLocaleDateString()} · {conv.message_count || 0} messages
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => deleteConversation(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 rounded-full p-1.5 text-ink/30 hover:bg-red-50 hover:text-red-600 transition"
                      title="Delete thread"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && !isStreaming ? (
                <div className="flex h-full flex-col items-center justify-center text-center p-6">
                  <div className="grid size-12 place-items-center rounded-full bg-saffron/10 text-saffron">
                    <Bot size={24} />
                  </div>
                  <h3 className="mt-4 font-display text-2xl tracking-tight text-ink">
                    Where would you like to wander?
                  </h3>
                  <p className="mt-2 max-w-xs text-xs leading-5 text-ink/55">
                    Ask about quiet high-altitude homestays, living root bridges, local seasonal
                    timings, or sustainable routes across India.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {[
                      "Best time for Ziro Valley?",
                      "Slow route through Spiti",
                      "Quiet homestays in Kerala",
                    ].map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        onClick={() => {
                          setInputPrompt(prompt);
                        }}
                        className="rounded-full border border-line bg-white px-3 py-1.5 text-xs text-ink/70 transition hover:border-saffron hover:text-saffron"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex gap-3 ${
                        msg.sender_type === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {msg.sender_type === "assistant" && (
                        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-olive text-white shadow-sm">
                          <Bot size={15} />
                        </span>
                      )}
                      <div
                        className={`max-w-[85%] rounded-[20px] p-4 text-sm leading-6 shadow-sm ${
                          msg.sender_type === "user"
                            ? "bg-ink text-white"
                            : "border border-line bg-white text-ink"
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        {msg.metadata_json?.citations && (
                          <div className="mt-3 border-t border-line/50 pt-2 text-[10px] text-ink/50">
                            <span className="font-semibold uppercase tracking-wider text-olive">
                              Verified Signals:
                            </span>{" "}
                            {msg.metadata_json.citations.join(" · ")}
                          </div>
                        )}
                      </div>
                      {msg.sender_type === "user" && (
                        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-mist text-ink/60">
                          <UserIcon size={14} />
                        </span>
                      )}
                    </div>
                  ))}

                  {/* Streaming In-Progress Bubble */}
                  {isStreaming && (
                    <div className="flex gap-3 justify-start">
                      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-olive text-white animate-pulse">
                        <Bot size={15} />
                      </span>
                      <div className="max-w-[85%] rounded-[20px] border border-line bg-white p-4 text-sm leading-6 text-ink shadow-sm">
                        <p className="whitespace-pre-wrap">{streamedText}</p>
                        <span className="inline-block size-2 animate-bounce rounded-full bg-saffron ml-1" />
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Bottom Input & Actions */}
            <div className="border-t border-line bg-white p-3">
              {messages.length > 0 && !isStreaming && (
                <div className="mb-2 flex justify-end">
                  <button
                    type="button"
                    onClick={handleRegenerate}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-ink/50 hover:text-saffron transition"
                  >
                    <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
                    Regenerate answer
                  </button>
                </div>
              )}

              <form onSubmit={handleSend} className="relative flex items-center">
                <input
                  type="text"
                  value={inputPrompt}
                  onChange={(e) => setInputPrompt(e.target.value)}
                  placeholder="Ask about offbeat trails, places or routes..."
                  disabled={isStreaming}
                  className="h-12 w-full rounded-full border border-line bg-paper pl-4 pr-12 text-sm outline-none transition focus:border-saffron"
                />
                <button
                  type="submit"
                  disabled={!inputPrompt.trim() || isStreaming}
                  className="absolute right-1.5 grid size-9 place-items-center rounded-full bg-saffron text-white transition hover:bg-[#b95a36] disabled:opacity-40"
                  aria-label="Send message"
                >
                  {isStreaming ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Send size={15} />
                  )}
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
