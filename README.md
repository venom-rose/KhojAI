# KHOJAI (Hidden India AI) 🇮🇳
### Destination Intelligence & AI Copilot for Unexplored India

[![Tests](https://img.shields.io/badge/pytest-81%20passed-brightgreen.svg)](docs/TESTING.md)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](package.json)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue.svg)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-cyan.svg)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](package.json)

**KHOJAI** is an AI-powered travel intelligence platform built for the **Smart India Hackathon (SIH)**. It unlocks authentic, lesser-known, and rural destinations across India, diverting pressure away from congested tourist hotspots toward remote cultural villages, sacred Himalayan trails, and indigenous community homestays.

---

## 🏛️ System Architecture

```text
                                 [ Traveler / Web Client ]
                                             │
                                             ▼
                 ┌───────────────────────────────────────────────────────┐
                 │       Frontend: React 19 + Tailwind CSS + Vite        │
                 │   • Discover Explorer   • Interactive Chat Copilot    │
                 │   • Knowledge Vault RAG • Global Omnisearch (⌘K)      │
                 └───────────────────────────┬───────────────────────────┘
                                             │  /api/v1 (Reverse Proxy / JWT)
                                             ▼
                 ┌───────────────────────────────────────────────────────┐
                 │        Backend: FastAPI High-Performance API          │
                 │   • Auth & Security     • Rate Limiting & HSTS        │
                 │   • Chat Service (SSE)  • Document Pipeline (RAG)     │
                 │   • Hybrid Search Core  • Multi-Tenant Isolation      │
                 └───────────────────────────┬───────────────────────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     ▼                       ▼                       ▼
           ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
           │ Relational Store │    │ Vector Retrieval │    │  AI Abstraction  │
           │  PostgreSQL 16   │    │  In-Memory / PG  │    │  Gemini / OpenAI │
           │ (SQLAlchemy ORM) │    │  Vector (Cosine) │    │ / Local Fallback │
           └──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

## ⚡ Quickstart for Judges & Developers

### Option 1: Standalone Zero-Dependency Local Setup (Recommended)
This runs KHOJAI completely locally using SQLite async and the built-in Local AI provider without requiring external accounts or paid API keys.

#### 1. Setup Backend:
```powershell
# In project root:
.\backend\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# Initialize local SQLite database
python backend/init_db.py

# Start FastAPI backend (port 8000)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Setup Frontend:
```powershell
# Open a second terminal in project root:
corepack pnpm install

# Start Vite dev server (port 3000)
corepack pnpm run dev
```

* **Web Application:** `http://localhost:3000/`
* **Backend API Docs (Swagger):** `http://127.0.0.1:8000/docs`
* **Backend Diagnostics:** `http://127.0.0.1:8000/api/v1/health`

---

### Option 2: Production Containerized Setup (Docker Compose)
Runs the complete stack with PostgreSQL 16, FastAPI backend, and Nginx frontend:

```bash
docker-compose up --build -d
```

* **Web UI:** `http://localhost:3000/`
* **API Documentation:** `http://localhost:8000/docs`
* **Stop containers:** `docker-compose down`

---

## 🧪 Testing the Application

The test suite includes **81 automated tests** covering authentication, chat, document RAG, search, and security isolation:

```powershell
# Run the entire backend test suite
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v

# Run the 16 verified user flows
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_16_flows.py -v

# Frontend type safety & production bundle check
corepack pnpm check
corepack pnpm run build
```

Full testing documentation and test commands are available at [docs/TESTING.md](docs/TESTING.md).

---

## 🔑 Key Features Demonstrated

1. **AI Chat Copilot (RAG & Real-Time Streaming):**
   - Natural language conversational trip planning with Server-Sent Events (SSE).
   - Provider-independent design: switches between Google Gemini, OpenAI, or offline Local provider via environment configuration.
2. **Knowledge Vault & Document Ingestion (RAG):**
   - Secure upload of local field notes, PDF guidebooks, and trek maps.
   - Text cleaning, sliding-window chunking, vector embedding, and prompt-injection-safe retrieval.
3. **Omnisearch & Semantic Vector Search:**
   - Multi-modal search querying destinations, private document chunks, and past conversations with cosine ranking.
4. **Zero-Trust Multi-Tenant Isolation:**
   - Strict backend authorization guarantees users can never access another user's documents, conversations, search queries, or profiles.
5. **Community Field Notes & Crowdsourcing:**
   - Platform for verified travelers and locals to contribute unmapped routes, homestays, and cultural guidelines.

---

## 📖 Documentation Index

* 📄 **[SIH Technical Overview](docs/SIH_TECHNICAL_OVERVIEW.md)**: Full architecture, problem statement, security threat model, and scalability.
* 🛡️ **[Security Policy & Audit Log](SECURITY.md)**: Complete security matrix and vulnerability remediation log.
* 🧪 **[Testing Manual](docs/TESTING.md)**: Test suite layout, mock strategies, and CLI execution steps.
* ⚙️ **[Backend Guide](backend/README.md)**: FastAPI architecture, Alembic database migrations, and endpoints.
* 🎨 **[Frontend Audit](docs/FRONTEND_AUDIT.md)**: UI component breakdown, styling tokens, and design patterns.

---

## 👥 Smart India Hackathon Submission
* **Problem Category:** Travel & Tourism / Smart Automation / Cultural Preservation
* **Technology:** Python, FastAPI, PostgreSQL, SQLAlchemy, React 19, Tailwind CSS, TypeScript, Vite, Docker.
