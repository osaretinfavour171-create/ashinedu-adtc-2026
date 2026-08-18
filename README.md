# PidginPharma

**Offline clinical decision support for Nigerian community health workers.**
Built for the ADTC 2026 Hackathon.

PidginPharma helps Community Health Extension Workers (CHEWs) and
pharmacists at primary healthcare centres across Nigeria answer clinical
questions — in English, Nigerian Pidgin, or a mix — using **official
Nigerian drug formulary data and standard treatment guidelines stored
locally with zero network dependency**.

```
you> my pikin get hot body and dey vomit
```

## What it does

| Layer | Tech | Role |
|---|---|---|
| **Pidgin Layer** | Python | Normalizes Pidgin/mixed input into clean English; reformulates answers back into Pidgin-flavoured text |
| **DocReader** | Go | Local HTTP server (`POST /search`) over the drug-interaction matrix + NSTG condition index |
| **Orchestrator** | Python | REPL that routes Pidgin → English → (DocReader + local model) → Pidgin |
| **PinchTab (optional)** | Go | Browser layer over the pre-converted EML/STG HTML; semantic accessibility-tree retrieval when RAM allows |

## Data (all local, official)

- **Nigeria Essential Medicines List 2020** (PDF, text layer) — `app/data/EML_2020.pdf`
- **Nigeria Standard Treatment Guidelines 2022** — 270 structured clinical
  conditions in `app/data/stg_conditions/*.json` + reference PDF
- **Drug-interaction matrix** — 164 curated interactions in
  `app/data/interactions.json` (severity, mechanism, recommendation)

## Setup

```bash
# 1. (one time, needs internet) download models + tools
bash download_model.sh          # MedGemma 1.5-4B (~4.1 GB) + Qwen 2.5-1.5B fallback (checksum-verified)

# 2. start everything and open the REPL
bash start.sh
```

`start.sh` starts:
- DocReader (Go) on `127.0.0.1:8765`
- llama-server with MedGemma (falls back to Qwen if MedGemma is absent) on `127.0.0.1:8080`
- the interactive REPL
- with `--pinchtab`: also serves the converted HTML docs on `127.0.0.1:8766`
  for the optional PinchTab browser layer (~300-800 MB extra RAM)

## Usage

```bash
# Interactive REPL (Pidgin output by default)
bash start.sh

# Plain English answers only
bash start.sh --lang en

# One-shot query (useful for testing)
python app/orchestrator.py --once "artemether and quinine, e dey safe?"

# With the optional PinchTab browser layer (DocReader stays the default path)
python app/orchestrator.py --pinchtab --once "my pikin get hot body and dey vomit"

# Skip the model (answers from official data only)
python app/orchestrator.py --no-model --once "treatment for acute diarrhoea"
```

Example questions:
- "my pikin get hot body and dey vomit"
- "di patient dey run stomach since yesterday"
- "metronidazole plus warfarin, e dey safe?"
- "artemether lumefantrine and quinine"
- "treatment for bronchial asthma"

## Architecture

```
Pidgin input ──► PidginNormalizer ──► clean English query
                         │
                         ├──► DocReader (Go, local)   → official conditions + interactions
                         │
                         ├──► llama-server (local)    → clinical answer draft
                         │
                         └──► PidginReformulator ──► Pidgin-flavoured answer
```

Safety rules baked into the model prompt: never invent doses, use official
data first, flag red flags (convulsions, difficulty breathing, altered
consciousness, dehydration, pregnancy complications), refer when unsure.

## Tests

```bash
cd tests
python -m unittest discover -v     # Pidgin layer + data integrity (offline)
# HTTP tests run automatically when the DocReader server is up
```

## Layout

```
app/
  orchestrator.py          # REPL + pipeline wiring
  llm.py                   # llama-server client (localhost only)
  docreader_client.py      # DocReader HTTP client
  pidgin/                  # Pidgin language layer
    normalizer.py          # Pidgin -> English
    reformulator.py        # English -> Pidgin
    pidgin_glossary.json   # 264 clinical terms + Pidgin variants
    pidgin_phrases.json    # 475 multi-word phrase mappings
  docreader/               # Go server (interactions + condition index)
  data/                    # EML PDF, STG PDF + 270 conditions, interactions.json
models/                    # GGUF models (downloaded)
tools/                     # docreader.exe, llama.cpp, Go
tests/                     # unit + integration tests
```

> **Clinical disclaimer:** PidginPharma is a decision-support aid. It does
> not replace clinical judgment or referral to a higher-level facility.
