# EARL AI — ADTC 2026 Technical Writeup

## Problem

Nigeria has a severe shortage of doctors — roughly 1 physician per 2,500 people in rural areas. Community Health Extension Workers (CHEWs) and pharmacists at primary healthcare centres handle the bulk of patient consultations but often lack immediate access to current treatment guidelines or drug interaction databases.

The challenge: these health workers speak **Nigerian Pidgin English** (spoken by 75M+ people), but clinical reference materials are in formal English. There is no offline tool that bridges this language gap while providing evidence-based clinical decision support.

## Solution

EARL AI (formerly PidginPharma) is an **offline clinical decision support system** that:

1. **Understands Pidgin** — A NLP normalizer maps 264 medical terms and 475 Pidgin phrases to canonical English
2. **Clinical Knowledge Graph** — A graph-based reasoning engine loads all 270 NSTG 2022 conditions into memory (~100MB) and provides instant, zero-hallucination diagnosis and treatment recommendations
3. **Drug interaction lookup** — A Go-based DocReader searches 164 drug interactions with age-aware ranking
4. **LLM fallback** — MedGemma 1.5-4B or Qwen 2.5-1.5B handles unusual queries the graph can't match (optional, not required)
5. **Responds in Pidgin** — A reformulator translates the clinical answer back into natural Pidgin English while preserving drug names, doses, and severity levels

### Architecture Diagram

```
User query (Pidgin/English)
  │
  ├── [PidginNormalizer] → clean English query
  │
  ├── [Cache] → instant response for repeated queries
  │
  ├── [DocReader] → drug interactions (instant, <5ms)
  │
  ├── [Clinical Engine] → musculoskeletal queries (age-aware)
  │
  ├── [Knowledge Graph] → 270 conditions, symptom→treatment
  │     • Matches symptoms to conditions
  │     • Assesses severity (mild/moderate/severe/emergency)
  │     • Detects red flags → immediate referral
  │     • Generates follow-up questions if confidence is low
  │     • RAM: ~100MB | Speed: <1 second | Hallucination: ZERO
  │
  ├── [Conservative Care] → simple conditions (rest + water)
  │
  ├── [LLM Fallback] → unusual queries only (MedGemma/Qwen)
  │
  └── [PidginReformulator] → Pidgin-flavoured answer
```

## Knowledge Graph Engine

The core innovation is a **graph-based clinical reasoning engine** that replaces neural inference for most queries:

### How It Works

1. **Load**: All 270 NSTG 2022 condition JSONs are parsed into `ConditionNode` objects with symptom indexes, drug indexes, and red flag detection
2. **Match**: When a user describes symptoms, the graph traverses symptom→condition edges to find the best match
3. **Reason**: The reasoner assesses severity based on age, gender, symptom pattern, and red flags
4. **Decide**: Determines treatment path — conservative (rest/water), drugs (with dosing from guidelines), or refer (emergency)
5. **Format**: Outputs a structured clinical answer in Pidgin or English

### Why Graph > Neural Model for Clinical Decisions

| Aspect | Neural Model (MedGemma 4B) | Knowledge Graph |
|--------|---------------------------|------------------|
| **RAM** | 2-4 GB | ~100 MB |
| **Startup** | 30-60 seconds | Instant |
| **Response** | 5-15 seconds | <1 second |
| **Hallucination** | Possible (wrong dose!) | **Zero** — follows NSTG exactly |
| **Offline** | Needs model server | Fully offline, no server |
| **Accuracy** | Depends on model quality | 100% guideline-faithful |

### Graph Statistics

- **270 conditions** loaded from NSTG 2022
- **890 drugs** indexed with dosing information
- **25 symptom categories** with Nigerian Pidgin variants
- **15 red flag patterns** for emergency detection
- **30+ condition hints** for common Nigerian health complaints

### Routing Logic

The system routes queries through the most appropriate engine:

```
Drug interaction query → DocReader (instant, authoritative)
Musculoskeletal query  → Clinical Engine (age-aware reasoning)
Common condition        → Knowledge Graph (zero hallucination)
Simple condition        → Conservative Care (rest + water)
Unusual query           → LLM fallback (MedGemma/Qwen)
Emergency               → Immediate referral
```

## Design Decisions

### Model Selection

We evaluated several 1B-4B parameter models:

| Model | Params | Quality | Speed (CPU) | RAM | Verdict |
|-------|--------|---------|-------------|-----|---------|
| Qwen 2.5-1.5B-Instruct | 1.5B | Good | ~18 t/s | ~2 GB | Fallback — fast, safe for low-RAM |
| **MedGemma 1.5-4B-IT** | **4B** | **Excellent** | **~5 t/s** | **~5 GB** | **Primary — best clinical accuracy** |
| Llama 3.2 3B | 3B | Good | ~12 t/s | ~4 GB | Considered but MedGemma was better |

**Why MedGemma 4B:** It was specifically trained on medical data and produces clinically accurate, well-structured answers. For a clinical decision support tool where accuracy directly affects patient outcomes, the quality advantage outweighs the speed penalty.

**Why Qwen 2.5-1.5B as fallback:** On machines with < 6 GB free RAM, MedGemma may OOM. Qwen 1.5B runs safely and still produces reasonable clinical answers.

### Quantization: Q8_0

We chose Q8_0 (8-bit integer) over Q4_K_M because:
- **Clinical accuracy matters** — quantization artifacts in medical responses can be dangerous
- **RAM is the hard limit (8 GB)** — Q8_0 at 4B params uses ~5 GB, leaving ~3 GB for OS + other services
- Q4_K_M would save ~1.5 GB but we observed degraded dose accuracy in testing

### Architecture: Python + Go + llama.cpp

- **Go DocReader** — compiles to a single ~9 MB binary, ~8 MB idle RAM, <5 ms lookups. No Python runtime needed
- **Python orchestrator** — the Pidgin NLP layer is pure stdlib (json, re, urllib), runs anywhere Python 3.8+ exists
- **llama.cpp** — the inference engine, runs on any OS/architecture with CPU support

This stack was chosen for **zero-dependency deployment** on the ADTC Ubuntu evaluation box.

## Constraints

- **8 GB RAM ceiling** — MedGemma Q8_0 uses ~5 GB; DocReader ~8 MB; PinchTab (optional) ~300-800 MB. Peak RSS stays under 6.5 GB
- **Zero network during evaluation** — all data, models, and tools are pre-downloaded
- **Ubuntu 22.04 eval box** — all binaries are Linux x86-64 (cross-compiled from Windows dev machine)
- **No GPU** — inference runs on CPU only (4 vCPU)

## Benchmarks (Development Machine: Windows, Intel i5, 16 GB RAM)

| Metric | MedGemma 1.5-4B Q8_0 | Qwen 2.5-1.5B Q8_0 |
|--------|----------------------|---------------------|
| Model size | 4.13 GB | 1.78 GB |
| Peak RSS | ~5.5 GB | ~2.2 GB |
| Prompt eval | ~40 t/s | ~41 t/s |
| Generation | ~5 t/s | ~18 t/s |
| Time to first token | ~0.8 s | ~0.3 s |
| Drug interaction lookup | <5 ms | <5 ms |
| Condition search (270 docs) | <5 ms | <5 ms |

## Test Prompts (used in development)

1. `"my pikin get hot body and dey vomit"` — Tests Pidgin normalization, child age detection, fever differential diagnosis
2. `"artemether lumefantrine and quinine, e dey safe?"` — Tests drug interaction lookup, severity ranking, Pidgin response

## Security

A full security audit (see `SECURITY_AUDIT.md`) identified and fixed 8 findings:
- Request body size limits on HTTP endpoints
- Context length caps for LLM inference
- Content-Type validation, input length limits
- Network binding warnings
- File-size validation on data loading

All services bind to `127.0.0.1` (localhost only) — zero network exposure.
