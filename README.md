# 🔗 SupplyChainIQ v3.0

**AI-Powered Supply Chain Risk Intelligence Platform for SMEs**

> *Democratizing enterprise-grade supply chain risk intelligence — making it accessible, affordable, and actionable for every business.*

[![SDG 9](https://img.shields.io/badge/SDG%209-Industry%20%26%20Innovation-orange)](https://sdgs.un.org/goals/goal9)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<p align="center">
  <img src="/Users/apple/.gemini/antigravity/brain/5cec9418-051e-4654-b0fd-c0668892de0a/1749592237077-Screenshot%202026-04-14%20at%2011.20.15%20AM.png" alt="SupplyChainIQ Main Dashboard">
</p>

---

## 🎯 The Problem

Global supply chains are under unprecedented pressure:

- **$4 trillion+** lost annually due to supply chain disruptions (World Bank)
- **70% of SMEs** have no formal risk management tooling whatsoever
- Enterprise platforms (SAP, Oracle Risk Management) cost **$200K–$2M/year** — out of reach for smaller businesses
- Critical risk signals are **siloed** across news wires, weather agencies, port authorities, and geopolitical briefs
- By the time a mid-size company hears about a Red Sea shipping crisis, their inventory has already stalled

---

## 💡 The Solution

SupplyChainIQ v3.0 is a full-stack AI risk intelligence platform that lets any business:

1. **Describe their supply chain in plain English** — no consultants, no complex forms
2. **Receive a structured, AI-generated risk brief** — covering geopolitical, climate, logistics, and supplier risks
3. **Visually explore their supply chain graph** — with an interactive, navigable node map
4. **Monitor live global news** — filtered specifically for supply chain-relevant signals
5. **Simulate disruption scenarios** — "what-if" modelling to stress-test their network
6. **Upload proprietary documents** — allowing the AI to reason on top of real company data

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 18 + Vite)                   │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────────┐ │
│  │ Chat UI      │  │ Graph Canvas  │  │ Live Intelligence Sidebar │ │
│  │ (Analysis +  │  │ (SVG Pan/Zoom │  │ (RSS Feed + Analysis      │ │
│  │  Follow-Up)  │  │  + Node Click)│  │  Stats + Severity Legend) │ │
│  └──────────────┘  └───────────────┘  └───────────────────────────┘ │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────────┐ │
│  │ Scenario Sim │  │  File Upload  │  │  History / Export Panel   │ │
│  └──────────────┘  └───────────────┘  └───────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST API (localhost:8005)
┌──────────────────────────────▼──────────────────────────────────────┐
│                        BACKEND (FastAPI + Python)                   │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────────┐ │
│  │ API Gateway  │  │ RAG Service   │  │ Encrypted Key Manager     │ │
│  │ (Auth +      │  │ (Entity NER + │  │ (Fernet AES-128 at rest)  │ │
│  │  Routing)    │  │  Risk Search) │  │                           │ │
│  └──────────────┘  └───────────────┘  └───────────────────────────┘ │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────────┐ │
│  │ LLM Service  │  │ News Service  │  │ Session / DB Layer        │ │
│  │ (Multi-Model │  │ (Live RSS +   │  │ (SQLAlchemy + SQLite      │ │
│  │  Orchestrate)│  │  NLP filter)  │  │  Async)                   │ │
│  └──────────────┘  └───────────────┘  └───────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
          ┌────────────────────┼──────────────────────────┐
          ▼                    ▼                           ▼
┌──────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│  Multi-LLM APIs  │  │  Live RSS Sources  │  │  Local SQLite DB     │
│  Groq / Gemini   │  │  Reuters / BBC /   │  │  (Sessions, Messages │
│  OpenAI / Claude │  │  FT / Guardian     │  │   Keys, Profiles)    │
└──────────────────┘  └────────────────────┘  └──────────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free API key from [Groq](https://console.groq.com/keys) (recommended — fastest inference)

### Step 1: Start the Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set your LLM API key (Groq is free and recommended)
export GROQ_API_KEY=gsk_your_key_here

# Start server on port 8005
uvicorn app.main:app --reload --port 8005
```

### Step 2: Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** and you're live.

> **Note:** If you skip the API key entirely, the app runs in **Demo Mode** using curated mock intelligence data — still fully functional for demonstrations.

---

## 📋 Complete Feature List

### 🧠 AI & Reasoning Engine

| Feature | Detail |
|---|---|
| **Natural Language Input** | Describe your supply chain in plain conversational English — no structured forms |
| **Industry-Aware Analysis** | Tailors risk weighting to your sector: Electronics prioritizes chip shortage risks; Food & Bev prioritizes spoilage and cold-chain |
| **Multi-Model LLM Support** | Native integration with **Groq (Llama 3)**, **Google Gemini 1.5**, **OpenAI GPT-4o**, and **Anthropic Claude 3.5** |
| **Intelligent Provider Fallback** | If your preferred LLM is unavailable or rate-limited, the system gracefully falls back to mock intelligence — the demo never breaks |
| **Structured JSON Response Healing** | A backend "healer" layer repairs malformed LLM output, ensuring UI components always receive valid structured data |
| **RAG Context Injection** | Retrieved risk data, uploaded file content, and user profile are injected into the LLM's hidden context block before generation |
| **User Profile Personalization** | Company name and industry type are appended to every analysis prompt for contextually grounded recommendations |
| **Conversation Memory (Multi-Turn)** | Follow-up questions are routed to a dedicated `/followup` endpoint that replays prior analysis context for coherent dialogue |
| **Local Focus Mode** | A toggle switch that restricts risk analysis to domestic/regional factors, automatically detecting the operating country from the prompt. Ideal for local supply chains without global exposure. |

<p align="center">
  <img src="/Users/apple/.gemini/antigravity/brain/5cec9418-051e-4654-b0fd-c0668892de0a/1749592237887-Screenshot%202026-04-14%20at%2011.20.30%20AM.png" alt="Local Focus Mode">
</p>

### 📊 Supply Chain Graph (Interactive Visualization)

| Feature | Detail |
|---|---|
| **Auto-Layout Algorithm** | Nodes are automatically arranged left-to-right in a columnar flow: `Suppliers → Factories → Ports → Destinations` |
| **Infinite Canvas Panning** | Click-drag the background to navigate large global networks — similar to Apple Freeform / Figma |
| **Variable Zoom (40%–250%)** | Zoom in or out with `+` / `−` buttons; zoom is centripetal (scales from canvas center) |
| **Live Zoom Percentage Readout** | A monospace percentage display between zoom buttons shows your exact zoom level in real-time |
| **Reset View Button** | Instantly snaps the graph back to default position and 100% zoom with one click |
| **Severity-Based Node Heatmapping** | Each node is color-coded by the peak severity of its associated risks: 🔴 Critical → 🟠 High → 🟡 Medium → 🟢 Low |
| **Hover Edge Highlighting** | Hovering a node illuminates all of its connected shipping lanes (edges) so dependency paths are instantly clear |
| **Click-to-Inspect Node Detail** | Clicking any node opens a detail panel below showing all linked risks, their causes, confidence scores, and recommended actions |
| **Auto-Select Highest Risk Node** | On graph load, the highest-severity node is automatically pre-selected so attention is immediately drawn to the critical point |
| **Graph Capacity Counter** | The legend displays total node and edge counts so complexity is always visible at a glance |
| **Animated Dot-Grid Background** | A subtle dot-grid canvas shifts as you pan, reinforcing the "infinite workspace" feel |
| **Directional Arrowhead Edges** | Cubic Bézier edges with arrowheads show the flow direction of goods between nodes |

### 📰 Live Intelligence Feed (Real-Time News)

| Feature | Detail |
|---|---|
| **Live RSS Aggregation** | Pulls real-time articles from **Reuters**, **BBC Business**, **Financial Times**, and **The Guardian** |
| **Supply Chain Keyword Filter** | 20+ specialist keywords (`suez`, `tariff`, `chip`, `port`, `shipping`, etc.) filter out noise from general news |
| **Region Inference Engine** | Automatically maps article content to a geographic region tag (e.g., article mentioning "Hsinchu" → tagged as "Taiwan") |
| **Severity Scoring** | Articles are auto-scored from Low to Critical based on keywords like `blockade`, `crisis`, `attack`, `growth`, `stable` |
| **30-Minute Refresh Cache** | A server-side cache prevents hammering news sources; the feed refreshes every 30 minutes automatically |
| **Article Deduplication** | A title-hashing system prevents the same story from appearing twice if multiple outlets cover it |
| **Click-to-Read Source Links** | Every live news card is clickable and opens the full original article in a new browser tab |
| **External Link Hover Icon** | A subtle `↗` icon appears on hover to signal that each card is an interactive link |
| **Animated Pulse "LIVE" Badge** | A green pulsing dot in the sidebar header visually confirms live monitoring is active |
| **Graceful Fallback to Mock Data** | If the RSS sources are unreachable (e.g., no internet), the feed silently falls back to curated mock intelligence data |
| **60-Second Auto-Refresh Polling** | The frontend polls the backend every 60 seconds to surface breaking news without requiring a page reload |

### 📂 Document Upload & Context Analysis

| Feature | Detail |
|---|---|
| **Multi-Format File Support** | Upload and analyze **PDF**, **CSV**, **Excel (.xlsx / .xls)**, and **Plain Text (.txt)** documents |
| **PDF Text Extraction** | Uses `pypdf` to extract text from multi-page PDFs (note: scanned/image-only PDFs are flagged) |
| **CSV & Excel Parsing** | DataFrames are converted to plain text and injected into the LLM context verbatim |
| **Cross-File Analysis** | Upload multiple files in one session — the AI reasons across all of them simultaneously |
| **File Context Persistence** | Uploaded file content is stored in the session database and re-injected on every follow-up query |
| **Session-Aware Upload** | Files can be attached to an existing session ID or used to create a new one |

### 🛡️ Strategy, Risk & Simulation

| Feature | Detail |
|---|---|
| **4-Level Severity Taxonomy** | Every risk is classified as **Critical**, **High**, **Medium**, or **Low** with consistent color coding throughout the UI |
| **Risk Category Classification** | Risks are classified into four domains: `Geopolitical`, `Climate`, `Logistics`, `Supplier` |
| **Confidence Score Display** | Each risk card shows a percentage confidence score, represented as a filled progress bar |
| **"Grounded In" Evidence Blocks** | Every risk finding cites the exact data sources (e.g., "Eastern Europe: overland transport disruptions") that support the claim |
| **Recommended Action Engine** | The AI provides specific, mitigation-focused recommended actions for each risk node |
| **What-If Scenario Simulation** | A dedicated `Simulate` tab allows users to stress-test specific disruptions and model the impact on their supply chain |
| **Follow-Up Suggestion Chips** | After each analysis, the AI auto-generates 3 contextual follow-up question chips the user can tap to dive deeper |
| **Alternative Supplier Mapping** | The RAG layer retrieves specific alternative companies by country and industry for every single-source dependency identified |
| **Shipping Route Alternatives** | Calculates backup logistics routes (e.g., Cape of Good Hope as Suez alternative) with comparative transit times |

### 🏗️ Platform, UX & Productivity

| Feature | Detail |
|---|---|
| **Onboarding Setup Screen** | A full-screen guided setup to configure company name, industry type, preferred AI provider, and API key |
| **Demo Mode ("Skip Login")** | One click launches the app with curated mock intelligence — no API key needed, ideal for judges |
| **"Key Already Saved" Detection** | The setup screen detects previously stored API keys and shows a `••••••• (saved)` placeholder instead of prompting again |
| **Provider Badge in Header** | The active AI provider (e.g., `⚡ GROQ`) is shown as a badge in the top navigation bar at all times |
| **Session History Browser** | A `History` view lets users browse, search, and re-open past analyses to track risk evolution over time |
| **HTML Export** | One-click export of the full structured risk brief as a clean, shareable HTML document |
| **Markdown Export** | Export risk briefs as `.md` files for integration into documentation or GitHub wikis |
| **High-Contrast Input Fields** | Setup screen inputs use white backgrounds with black text for maximum legibility under any lighting condition |
| **Scrollable Setup Screen** | The login/setup form is fully scrollable on small viewports — the title is always visible at the top |
| **Global Analysis Stats Panel** | The sidebar shows real-time counters for total risk nodes, regions affected, industries covered, and overall severity |
| **Industrial Dark Mode UI** | A custom "Industrial Dark" theme with Glassmorphism cards, gradient backgrounds, and a precision typography system |
| **Framer Motion Animations** | Smooth entry/exit animations on cards, panels, and the graph detail drawer for a premium feel |
| **Cursor Affordance Signals** | The graph canvas cursor changes from `default` → `grab` → `grabbing` to communicate the panning interaction naturally |

### 🔐 Security & Data Layer

| Feature | Detail |
|---|---|
| **Fernet AES-128 Key Encryption** | API keys are encrypted before being written to the database — never stored in plaintext |
| **Per-User API Key Isolation** | Each user's keys are scoped to their `user_id` and cannot be accessed by other sessions |
| **SQLAlchemy Async ORM** | The database layer uses `aiosqlite` for non-blocking I/O, ensuring high throughput even under concurrent users |
| **JWT-Based Session Auth** | All API endpoints are protected by user authentication; anonymous requests are rejected |
| **CORS Configuration** | Strict CORS policy ensures only the local frontend origin can communicate with the API |

---

## 📁 Project Structure

```
supplychainiqV3.0/
│
├── backend/                        # FastAPI Python backend
│   ├── app/
│   │   ├── main.py                 # App entry point, CORS, router registration
│   │   ├── models.py               # All Pydantic request/response models
│   │   ├── database.py             # SQLAlchemy async engine + DB models
│   │   ├── dependencies.py         # JWT auth dependency injection
│   │   ├── routers/
│   │   │   ├── analysis.py         # /analyze, /followup, /alerts, /scenario endpoints
│   │   │   ├── auth.py             # Login / registration endpoints
│   │   │   └── keys.py             # Encrypted API key storage endpoints
│   │   ├── services/
│   │   │   ├── llm_service.py      # Multi-model LLM orchestration layer
│   │   │   ├── rag_service.py      # Entity extraction + risk retrieval
│   │   │   └── news_service.py     # Live RSS feed aggregator + NLP filter
│   │   └── data/
│   │       └── mock_risk_data.py   # Curated global risk intelligence dataset
│   └── requirements.txt
│
├── frontend/                       # React 18 + Vite frontend
│   ├── src/
│   │   ├── App.jsx                 # Root app, screen routing, session state
│   │   ├── components/
│   │   │   ├── SetupScreen.jsx     # Onboarding: company profile + LLM config
│   │   │   ├── Header.jsx          # Top navigation bar + provider badge
│   │   │   ├── Sidebar.jsx         # Live feed + analysis stats + severity legend
│   │   │   ├── ChatInterface.jsx   # Main chat input + message thread
│   │   │   ├── RiskBrief.jsx       # Structured risk card output (Brief tab)
│   │   │   ├── SupplyChainGraph.jsx # Interactive SVG graph with pan + zoom
│   │   │   ├── ScenarioSimulator.jsx # What-If scenario tab
│   │   │   └── HistoryScreen.jsx   # Past analysis browser
│   │   ├── hooks/
│   │   │   └── useAnalysis.js      # Analysis + follow-up state management
│   │   ├── utils/
│   │   │   └── api.js              # All API call functions + auth headers
│   │   └── styles/
│   │       └── index.css           # Global design tokens + custom utility classes
│   ├── tailwind.config.js          # Custom color palette (avoiding Tailwind conflicts)
│   └── vite.config.js              # Dev server + proxy to backend :8005
│
└── demo_files/                     # Ready-to-upload demo documents for testing
    ├── supplier_list.csv           # 15-supplier global dataset with risk metadata
    ├── logistics_routes.csv        # 12 live shipping routes with disruption status
    └── nexacore_risk_briefing.txt  # Full company risk briefing (fictional company)
```

---

## 🔌 API Reference

### Analyze Supply Chain
```http
POST /api/v1/analysis/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "description": "I run a laptop assembly plant. CPUs from TSMC Taiwan, displays from LG Korea, shipped via Singapore to Rotterdam.",
  "session_id": null
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "overall_risk_level": "High",
  "summary": "Your supply chain faces critical single-source exposure...",
  "risk_nodes": [
    {
      "node": "TSMC Taiwan",
      "risk_level": "Critical",
      "cause": "Taiwan Strait geopolitical tensions affect semiconductor supply",
      "recommended_action": "Qualify Samsung and Intel Fab as secondary sources within 18 months",
      "confidence_score": 0.91,
      "category": "geopolitical",
      "evidence": ["Taiwan Strait military exercises Q1 2026", "TSMC Hsinchu power outage March 2026"]
    }
  ],
  "supply_chain_graph": { "nodes": [...], "edges": [...] },
  "follow_up_suggestions": ["What are TSMC alternatives?", "Model a Taiwan blockade scenario"],
  "provider_meta": { "provider_used": "groq", "is_mock": false }
}
```

### Follow-Up Question
```http
POST /api/v1/analysis/followup
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "uuid-from-previous-response",
  "question": "What happens if TSMC has a 3-month outage?"
}
```

### Upload Context File
```http
POST /api/v1/analysis/upload-context
Authorization: Bearer <token>
Content-Type: multipart/form-data

background_file: <your_file.csv>
session_id: "optional-existing-session-id"
```
**Supported formats:** `.csv`, `.xlsx`, `.xls`, `.txt`, `.pdf`

### Live Alerts Feed
```http
GET /api/v1/analysis/alerts?limit=8
Authorization: Bearer <token>
```

### What-If Scenario Simulation
```http
POST /api/v1/analysis/scenario
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "uuid",
  "scenario_type": "port_closure",
  "affected_node": "Singapore"
}
```

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Frontend Framework** | React | 18 |
| **Build Tool** | Vite | 5 |
| **Styling** | Tailwind CSS + Custom Tokens | 3 |
| **Animations** | Framer Motion | 11 |
| **Icons** | Lucide React | Latest |
| **Backend Framework** | FastAPI | 0.109+ |
| **Language** | Python | 3.11+ |
| **ORM** | SQLAlchemy (Async) | 2.0+ |
| **Database** | SQLite via aiosqlite | — |
| **Encryption** | Fernet (cryptography lib) | 42+ |
| **HTTP Client** | httpx (async) | 0.26+ |
| **PDF Parsing** | pypdf | 4+ |
| **Data Processing** | pandas | 2.2+ |
| **Primary LLM** | Groq (Llama 3) | — |
| **Additional LLMs** | Gemini / GPT-4o / Claude | — |
| **News Sources** | Reuters / BBC / FT / Guardian RSS | — |

---

## 🎯 Who Is This For?

| User | Use Case |
|---|---|
| **SME Manufacturers** | Identify risks in their supplier and logistics network without expensive consultants |
| **Procurement Teams** | Screen new suppliers against real geopolitical and climate data before onboarding |
| **Logistics Managers** | Monitor live shipping route disruptions and simulate alternative routing costs |
| **Supply Chain Analysts** | Upload proprietary data files and interrogate them with AI-powered reasoning |
| **Startup Founders** | Understand their supply chain exposure when designing their first BOM |

---

## 🌍 SDG 9 Alignment

SupplyChainIQ directly supports **UN Sustainable Development Goal 9: Industry, Innovation & Infrastructure** by:

- **Democratizing access** to supply chain intelligence previously exclusive to Fortune 500 companies
- **Reducing economic fragility** of SMEs by enabling proactive risk mitigation rather than reactive crisis response
- **Supporting resilient infrastructure** by helping businesses identify alternative suppliers and routes before disruptions occur
- **Lowering barriers to innovation** by providing a no-code, conversational interface that requires no specialist training

---

## 📊 Performance Targets

| Metric | Target |
|---|---|
| AI Risk Report Generation | ≤ 15 seconds |
| Graph Render (20 nodes) | ≤ 300ms |
| News Feed Refresh | Every 30 min (server) / 60s (client poll) |
| File Upload (5MB PDF) | ≤ 5 seconds |
| API Response (follow-up) | ≤ 8 seconds |

---

## 🗺️ Roadmap

### ✅ v3.0 — Current (Hackathon Build)
- [x] Multi-turn conversational risk analysis
- [x] Interactive supply chain graph (pan, zoom, click-to-inspect)
- [x] Live RSS news feed with NLP filtering and click-through links
- [x] Multi-model LLM support (Groq, Gemini, OpenAI, Claude)
- [x] File upload context injection (PDF, CSV, Excel, TXT)
- [x] What-If scenario simulator
- [x] Encrypted API key management
- [x] Session persistence and history browser
- [x] HTML and Markdown export
- [x] Industry-aware risk personalization
- [x] Demo file dataset for testing

### 🔜 v4.0 — Post-Hackathon
- [ ] Pinecone / Chroma vector DB for true semantic RAG search
- [ ] Real-time port congestion APIs (Marine Traffic, Portcast)
- [ ] Live freight rate integration (Freightos, Xeneta)
- [ ] Predictive risk forecasting (28-day horizon)
- [ ] Email/Slack alert subscriptions for monitored routes
- [ ] Multi-language support (Spanish, Mandarin, German)
- [ ] PostgreSQL migration for production scale
- [ ] Enterprise API tier with rate limiting and billing

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Groq** — Ultra-fast LPU inference powering real-time risk analysis
- **Anthropic, Google, OpenAI** — LLM providers for high-quality reasoning
- **Reuters, BBC, Financial Times, The Guardian** — Live news sources for the intelligence feed
- **UN SDG 9** — Framework for industry innovation and infrastructure resilience
- Built for the **UK AI Hackathon 2026**

---

<p align="center">
  <b>SupplyChainIQ v3.0</b> — From raw data to strategic intelligence in seconds.<br/>
  <i>Empowering every SME with the risk awareness that was once exclusive to the Fortune 500.</i>
</p>
