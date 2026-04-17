# SupplyChainIQ — Validated Performance Benchmarks

**Provider:** Groq (llama3-8b-8192 LPU)  
**Measured:** 11 April 2026 at 23:31 IST  
**Environment:** Local development (MacOS, localhost:8005)  

| Metric | Mean | Min | Max |
|---|---|---|---|
| RAG Retrieval (in-memory) | 0ms | 0ms | 0ms |
| CSV File Parse & DataFrame Conversion | 7ms | 7ms | 7ms |
| LLM Analysis — Simple Chain (Groq llama3-8b) | 944ms | 944ms | 944ms |
| LLM Analysis — Complex Chain 4 regions (Groq llama3-8b) | 2.01s | 2.01s | 2.01s |
| LLM Analysis — Food & Beverage Chain (Groq llama3-8b) | 0ms | 0ms | 0ms |

## LLM Analysis — Per Test Case

| Test Case | Response Time | Risk Nodes Identified | Overall Risk |
|---|---|---|---|
| Simple Chain (1 region) | 0.94s | 4 | High |
| Complex Chain (4 regions) | 2.01s | 5 | High |

> Benchmarks measured by firing real API requests to Groq's LPU inference API.
> RAG retrieval uses in-memory search over the curated risk knowledge base.
