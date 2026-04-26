# 🔗 SupplyChainIQ v6.0
**Enterprise-Grade Risk Intelligence for the SME-Led Global Economy**

SupplyChainIQ is a high-performance, AI-driven risk intelligence platform designed to democratize complex supply chain analysis. By merging static private datasets with live global news feeds, it provides SMEs with a "Digital Twin" of their logistics network—detecting disruptions before they hit the balance sheet.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SDG 9](https://img.shields.io/badge/SDG%209-Industry%20%26%20Innovation-orange)](https://sdgs.un.org/goals/goal9)

---

## 📸 Platform Overview

![SupplyChainIQ Dashboard](docs/images/setup_screen.png)

---

## 💡 The Core Value

SupplyChainIQ v6.0 introduces **Intra-Country Local Intelligence**. While enterprise tools focus on global shipping lanes, we empower businesses to pivot from global trade to domestic logistics with a single click.

1.  **Dual-Stream Hybrid RAG**: Merges your private business context with the **GDELT 2.1 Live News Feed**.
2.  **Local Focus Optimization**: Automatically suppresses "maritime noise" (like Suez Canal updates) to prioritize domestic trucking, labor, and weather risks.
3.  **Encrypted Key Vault**: Securely manages your Groq, Gemini, and OpenAI keys with Fernet (AES-256) encryption.

---

## 🏗️ System Architecture

```mermaid
graph TD
    classDef default fill:#111827,stroke:#374151,color:#D1D5DB,rx:5px,ry:5px
    classDef layerBoundary fill:#1F2937,stroke:#3B82F6,stroke-width:2px,color:#60A5FA,font-weight:bold,rx:8px,ry:8px
    classDef coreBoundary fill:#1F2937,stroke:#A855F7,stroke-width:2px,color:#C084FC,font-weight:bold,rx:8px,ry:8px
    classDef nodeItem fill:#374151,stroke:#6B7280,stroke-width:1px,color:#F9FAFB

    subgraph L1 [USER INPUT]
        direction LR
        I1(Plain-text description):::nodeItem
        I2(CSV / XLSX upload):::nodeItem
        I3(PDF / TXT documents):::nodeItem
        I4(Local Focus Toggle):::nodeItem
    end
    class L1 layerBoundary

    subgraph L2 [INGESTION ENGINE]
        direction LR
        E1[Multi-Format Parser <br/> pypdf • pandas • openpyxl]:::nodeItem
        E2[Two-Pass Entity Extractor <br/> Suppliers • Logistics • Industry • Regions]:::nodeItem
    end
    class L2 layerBoundary

    subgraph L3 [INTELLIGENCE CORE]
        R1[Dual-Stream Hybrid RAG Base]:::nodeItem
        R2[Live GDELT 2.1 News API <br/> 6-Hour TTL Cache]:::nodeItem
        C1[Multi-Stage Reranker <br/> Boosts local infra • Suppresses maritime noise]:::nodeItem
        C2[LLM Router <br/> Groq primary → Claude → GPT-4o → Gemini]:::nodeItem
        C3[Self-Healing JSON Engine]:::nodeItem
    end
    class L3 coreBoundary

    subgraph L4 [OUTPUT GENERATION]
        direction LR
        O1[Structured Risk Brief <br/> Severity • Evidence • Actions]:::nodeItem
        O2[Digital Twin Graph <br/> Framer Motion • React 18]:::nodeItem
        O3[Scenario Simulator <br/> Before/After delta • Route Pivot]:::nodeItem
    end
    class L4 layerBoundary

    subgraph L5 [SECURITY & INFRASTRUCTURE]
        direction LR
        S1[Fernet AES-256 Vault]:::nodeItem
        S2[FastAPI Async Backend]:::nodeItem
    end
    class L5 layerBoundary

    I1 & I2 & I3 & I4 --> E1
    E1 --> E2
    E2 --> R1 & R2
    R1 --> C1
    R2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> O1 & O2 & O3
    O2 -.-> S1 & S2
```

---

## 🛠️ Feature Showcase

### 📊 Intelligent Risk Briefing
![Risk Brief](docs/images/risk_brief.png)
Structured analysis with per-node severity, confidence scores, and evidence-backed recommendations.

### 📍 Supply Chain Digital Twin (Graph)
![Digital Twin Graph](docs/images/graph_view.png)
An interactive SVG visualization showing the flow of goods from Tier-2 suppliers to the final destination.

### 🧪 Scenario Simulation
![Scenario Simulator](docs/images/simulator.png)
"What-if" modeling to visualize the risk delta when switching suppliers or rerouting cargo.

### 🇮🇳 Local Focus Engine
![Local Focus](docs/images/local_focus.png)
Pivots the RAG pipeline to domestic-only risk vectors, suppressing global geopolitical noise.

---

## 📈 Performance Benchmarks (V6 Baseline)

Against the project's original V1 baseline, SupplyChainIQ v6.0 achieves a significant delta in reliability:

| Metric | Target | Result (V6) | Delta |
| :--- | :--- | :--- | :--- |
| **Mean Precision** | >70% | **77.5%** | 🚀 +41.3% |
| **Mean Recall** | >70% | **74.2%** | ✅ Stable |
| **Mean F1 Score** | >70% | **75.5%** | 🚀 +31.2% |
| **Graph Render** | <500ms | **180ms** | ⚡ Optimized |

---

## 🚀 Quick Start

### 1. Setup Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8005
```

### 2. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Configure
Navigate to `http://localhost:3000`. Enter your **Groq API Key** in the setup screen. Your key is encrypted at rest using Fernet and never leaves your local environment.

---

## 🔐 Security & Infrastructure
*   **Encrypted Storage**: API keys are stored in a separate `vault.db` and encrypted with a 32-byte master key.
*   **Hybrid Storage**: Uses SQLite with `aiosqlite` for high-concurrency, asynchronous I/O.
*   **JWT Auth**: All endpoints are protected by standard Bearer token authentication.

---

## 📄 License
MIT License. Built for the UK AI Hackathon 2026.
