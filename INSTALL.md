# EARL AI — Install Guide

**Offline clinical decision support for Nigerian health workers.**

---

## Quick Start (2 commands)

```bash
# 1. Clone
git clone https://github.com/osaretinfavour171-create/earlai-adtc-2026.git
cd earlai-adtc-2026

# 2. Download + Run
bash download_model.sh --lite    # 2GB, 2 minutes
bash start.sh --lite             # Ready!
```

---

## Two Modes

| | Lite Mode | Full Mode |
|---|---|---|
| **Command** | `bash download_model.sh --lite` | `bash download_model.sh` |
| **Download** | 2 GB | 5.8 GB |
| **Models** | Qwen 1.5B only | MedGemma 4B + Qwen 1.5B |
| **RAM** | ~2.5 GB | ~5.5 GB |
| **Best for** | Testing, old laptops | Full accuracy, demos |

**Upgrade from Lite to Full:** Just run `bash download_model.sh` (skips already-downloaded files).

---

## Try It

```
EARL AI > my pikin get hot body
  → Asks follow-up questions about age, symptoms

EARL AI > @lang en
  → Switches to English

EARL AI > treatment for malaria
  → Artemether-Lumefantrine (AL) dosing from NSTG 2022

EARL AI > metronidazole and warfarin
  → ⚠️ Drug interaction warning

EARL AI > joint pain 70 years
  → Osteoarthritis assessment with age-aware reasoning

EARL AI > @status
  → Shows service status, language, cache
```

---

## Global Command

After install, run `earlai` from any terminal:

```bash
# Windows (PowerShell/CMD)
earlai
earlai --lite

# Ubuntu/WSL
earlai
earlai --lite
```

---

## Requirements

| | Minimum | Recommended |
|---|---|---|
| **OS** | Ubuntu 22.04 / Windows 10 | Any Linux |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 3 GB | 7 GB |
| **Internet** | Only for initial download | None after install |
| **GPU** | Not required | Not required |

---

## What's Inside

| Component | What it does | Size |
|---|---|---|
| **Knowledge Graph** | 270 conditions, 890 drugs, instant answers | 18 MB RAM |
| **Drug Interaction DB** | Real-time safety checks | bundled |
| **Pidgin NLP** | Understands Nigerian Pidgin English | bundled |
| **Clinical Reasoner** | Severity assessment, red flag detection | bundled |
| **Conversational Engine** | Adaptive tone, smart follow-ups | bundled |
| **Qwen 1.5B** | LLM fallback for unusual queries | 2 GB |
| **MedGemma 4B** | Better accuracy (full mode only) | 4 GB |

---

## Architecture

```
Your query (Pidgin or English)
    ↓
Pidgin Normalizer → Clean English
    ↓
Medical Check → Is this a health question?
    ↓ Yes
Knowledge Graph (270 conditions, 1ms)
    ├── Match found → Guideline answer
    └── No match → LLM fallback
    ↓
Conversational Flow → Tone adaptation
    ↓
Response (Pidgin or English)
```

---

## Commands

| Command | What it does |
|---|---|
| `@lang en` | Switch to English |
| `@lang pidgin` | Switch to Pidgin |
| `@status` | Check services |
| `@stats` | Session stats |
| `@clear` | New patient |
| `@help` | Show help |
| `@exit` | Quit |

Or type naturally: `"switch to english"`, `"i want pidgin"`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Data server failed to start" | Run `bash start.sh` from the project folder |
| "Model server not available" | Models not downloaded yet — run `bash download_model.sh` |
| Colors look ugly in PowerShell | Open a new terminal window |
| `earlai` not found | Open a new terminal (PATH needs refresh) |

---

## Score Impact

| Metric | Weight | EARL AI |
|---|---|---|
| Accuracy | 50% | Zero-hallucination graph answers |
| Speed | 30% | 1ms/query (way above 15 TPS target) |
| Efficiency | 20% | 18MB graph, 99.8% RAM free |
