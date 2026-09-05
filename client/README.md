# KHOJAI Frontend Client Manual

The KHOJAI user interface is built using **React 19**, **Vite**, and **Tailwind CSS**, designed with an earthy editorial design system tailored for exploring India's hidden destinations.

---

## 🎨 Design Philosophy & Features

* **Visual Aesthetics:** Earthy editorial aesthetic inspired by unmapped Himalayan terrain, rustic terracotta homestays, and sacred architecture.
* **Component Architecture:** Reusable Radix UI primitives styled with Tailwind CSS, custom motion animations powered by `framer-motion`.
* **Centralized API Architecture:** All backend communications flow through `client/src/services/apiClient.ts` using Axios with automated token injection and response error interception.
* **Real-time Modals:**
  * `AuthModal`: Smooth tabbed sign-in/registration with client-side validation.
  * `ChatModal`: Real-time streaming conversation drawer with model switching and markdown formatting.
  * `DocumentModal`: Drag-and-drop document upload vault for RAG queries.
  * `GlobalSearchDialog`: Omnisearch dialog (`⌘K` / `Ctrl+K`) searching across destinations, knowledge documents, and chats.

---

## 📁 Key Directories

```text
client/src/
├── components/          # Reusable UI components
│   ├── ui/              # Radix + Tailwind primitive widgets (buttons, dialogs, cards)
│   ├── AuthModal.tsx    # Authentication dialog
│   ├── ChatModal.tsx    # AI Copilot chat drawer
│   ├── DocumentModal.tsx# Knowledge vault & RAG upload manager
│   ├── GlobalSearchDialog.tsx # Omnisearch modal
│   └── site.tsx         # Navbar and footer chrome
├── contexts/            # Global React contexts (AuthContext, etc.)
├── pages/               # Main application route views
│   ├── Home.tsx         # Landing page & curated collections
│   ├── Discover.tsx     # Destination explorer with multi-faceted filters
│   ├── Contribute.tsx   # Crowdsourced travel notes submission
│   └── NotFound.tsx     # 404 error page
├── services/            # Centralized API service modules
│   ├── apiClient.ts     # Axios instance with credentials and interceptors
│   ├── auth.ts          # Auth endpoints (login, register, logout, me)
│   ├── chat.ts          # Chat sessions, message history, SSE streaming
│   ├── documents.ts     # File upload, list, chunk detail, RAG queries
│   ├── search.ts        # Global omnisearch and hybrid queries
│   └── users.ts         # User profile and AI preferences
└── App.tsx              # Root component & Wouter client router
```

---

## 🚀 Development Quickstart

```powershell
# 1. Install dependencies
corepack pnpm install

# 2. Start Vite development server
corepack pnpm run dev
```

* Application is served at `http://localhost:3000/`.
* Any API request to `/api/*` is automatically proxied to the backend at `http://127.0.0.1:8000`.

---

## 🔍 Validation & Production Build

### Typechecking (TypeScript)
```powershell
corepack pnpm check
```

### Production Build
```powershell
corepack pnpm run build
```
Build output is generated in `dist/public`, ready for Nginx or static file serving.
