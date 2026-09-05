import { useState, useEffect } from "react";
import { Route, Switch } from "wouter";
import { Toaster, toast } from "sonner";
import { Sparkles } from "lucide-react";
import Home from "@/pages/Home";
import Discover from "@/pages/Discover";
import DestinationDetail from "@/pages/DestinationDetail";
import Planner from "@/pages/Planner";
import PlannerResults from "@/pages/PlannerResults";
import Contribute from "@/pages/Contribute";
import Community from "@/pages/Community";
import About from "@/pages/About";
import NotFound from "@/pages/NotFound";
import { AuthProvider } from "@/contexts/AuthContext";
import { AuthModal } from "@/components/AuthModal";
import { ChatModal } from "@/components/ChatModal";
import { DocumentModal } from "@/components/DocumentModal";
import { GlobalSearchDialog } from "@/components/GlobalSearchDialog";

function MainApp() {
  const [authOpen, setAuthOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [initialConvId, setInitialConvId] = useState<string | undefined>();
  const [vaultOpen, setVaultOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const handleOpenAuth = () => setAuthOpen(true);
    const handleOpenChat = () => setChatOpen(true);
    const handleOpenVault = () => setVaultOpen(true);
    const handleOpenSearch = () => setSearchOpen(true);
    const handleAuthExpired = () => {
      toast.error("Your session has expired. Please sign in again.");
      setAuthOpen(true);
    };

    window.addEventListener("khojai:open_auth", handleOpenAuth);
    window.addEventListener("khojai:open_chat", handleOpenChat);
    window.addEventListener("khojai:open_vault", handleOpenVault);
    window.addEventListener("khojai:open_search", handleOpenSearch);
    window.addEventListener("khojai:auth_expired", handleAuthExpired);

    return () => {
      window.removeEventListener("khojai:open_auth", handleOpenAuth);
      window.removeEventListener("khojai:open_chat", handleOpenChat);
      window.removeEventListener("khojai:open_vault", handleOpenVault);
      window.removeEventListener("khojai:open_search", handleOpenSearch);
      window.removeEventListener("khojai:auth_expired", handleAuthExpired);
    };
  }, []);

  return (
    <>
      <Toaster position="bottom-right" toastOptions={{ style: { background: "#1f261e", color: "#fff", border: "0" } }} />

      <Switch>
        <Route path="/" component={Home} />
        <Route path="/discover" component={Discover} />
        <Route path="/destination/:slug" component={DestinationDetail} />
        <Route path="/planner" component={Planner} />
        <Route path="/planner/results" component={PlannerResults} />
        <Route path="/contribute" component={Contribute} />
        <Route path="/community" component={Community} />
        <Route path="/about" component={About} />
        <Route component={NotFound} />
      </Switch>

      {/* Floating Travel AI Copilot Trigger */}
      <button
        type="button"
        onClick={() => setChatOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 rounded-full bg-ink px-4 py-3 text-xs font-semibold text-white shadow-[0_12px_35px_rgba(0,0,0,0.25)] transition hover:-translate-y-1 hover:bg-saffron active:scale-95 group"
        aria-label="Open KhojAI Travel Copilot"
      >
        <span className="relative flex size-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-saffron-light opacity-75" />
          <span className="relative inline-flex size-2 rounded-full bg-saffron" />
        </span>
        <Sparkles size={15} className="text-saffron-light group-hover:rotate-12 transition-transform" />
        <span>Ask KhojAI</span>
      </button>

      {/* Modals & Dialogs */}
      <AuthModal
        isOpen={authOpen}
        onClose={() => setAuthOpen(false)}
      />

      <ChatModal
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        initialConversationId={initialConvId}
        onOpenAuth={() => setAuthOpen(true)}
      />

      <DocumentModal
        isOpen={vaultOpen}
        onClose={() => setVaultOpen(false)}
        onOpenAuth={() => setAuthOpen(true)}
      />

      <GlobalSearchDialog
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        onOpenChatWithConversation={(id) => {
          setInitialConvId(id);
          setChatOpen(true);
        }}
        onOpenDocument={() => setVaultOpen(true)}
      />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
