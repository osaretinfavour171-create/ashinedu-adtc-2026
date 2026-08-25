## Inspiration

In rural Nigeria, a Community Health Extension Worker sees 40 patients a day. Her treatment guideline book is in formal English. Her patients speak Pidgin. She does her best — but _"her best"_ means guessing on drug doses and skipping interactions she's unsure about.

75 million Nigerians speak Pidgin. Zero medical AIs understood them. We asked a simple question: _what if the computer spoke her language?_ That question became **EARL AI**.

## What it does

EARL AI is an **offline clinical reasoning engine** for Nigerian health workers. Type a symptom in Pidgin or English — `"my pikin get hot body"` — and get an instant answer from Nigeria's official treatment guidelines.

- Understands **Nigerian Pidgin** — not a dictionary, a full NLP layer
- **Knowledge graph** — 270 conditions, 890 drugs from NSTG 2022
- **Drug interaction checks** — 164 curated interactions with severity levels
- **Smart follow-ups** — asks age, weight, symptoms before answering
- **Conversational intelligence** — adapts tone, tracks topics, detects urgency
- **Runs offline** — zero internet after install, works on any 4GB laptop

## How we built it

We stopped trying to fine-tune big models and built something different: a **graph-based reasoning engine**.

1. **Knowledge graph** — Parsed all 270 NSTG 2022 conditions into a traversable graph with symptom indexes, drug indexes, and red flag detection
2. **Pidgin NLP** — Built a normalizer with 264 medical terms and 475 phrase mappings using longest-match-first algorithm
3. **Binary symptom engine** — 57 symptom bits mapped to binary vectors with bitwise AND matching (0.1 microseconds per query)
4. **Clinical reasoner** — Assesses severity, detects emergencies, calculates drug doses from patient weight
5. **Conversational engine** — Inspired by Fish Audio's multi-turn pattern: topic tracking, adaptive tone, smart follow-ups
6. **Dual-model architecture** — Qwen 1.5B (fast fallback) + MedGemma 4B (best accuracy), both via llama.cpp

**Stack:** Python (NLP + orchestrator) · Go (DocReader, <5ms lookups) · llama.cpp (inference) · Binary bitwise matching · Pure JSON data (no database)

## Challenges we ran into

- **The 8GB RAM wall** — MedGemma 4B alone uses 5GB. We had to make the graph handle 90% of queries so the model only kicks in for edge cases
- **Pidgin is messy** — `"e dey"` means different things in different contexts. We built context-aware normalization, not dictionary lookup
- **Zero hallucination or nothing** — A medical AI that invents a wrong dose is worse than no AI. The graph answers only from verified guidelines
- **Binary matching accuracy** — Single symptoms like "fever" match every condition. We solved this by routing single-word queries to the graph reasoner and multi-word queries to the binary engine
- **Cross-platform on a budget** — Windows dev machine, Linux eval box. We cross-compiled Go binaries from WSL

## Accomplishments that we're proud of

- **1ms per query** — The graph engine responds faster than most web APIs, with zero hallucination
- **18MB of RAM** — The entire reasoning engine fits in less than a single photo
- **270 conditions, 890 drugs** — Every answer traces back to an official Nigerian guideline
- **Pidgin that actually works** — understands `"my pikin get hot body and dey vomit"` as a clinical query
- **Binary symptom engine** — 57-bit vectors with bitwise matching in 0.1 microseconds
- **Runs on anything** — Lite mode: 2GB download, works on a 4GB laptop
- **111 passing tests** — every component tested, every edge case caught

## What we learned

- **Bigger isn't always better** — an 18MB graph outperforms a 4GB model on 90% of clinical queries
- **Language is the real barrier** — the gap isn't computing power, it's that medical AI speaks English while patients speak Pidgin
- **Offline is non-negotiable** — if it doesn't work offline, it doesn't work in rural Nigeria
- **Binary vectors beat string matching** — bitwise operations are 10,000x faster for symptom matching

## Design Documents

- **[ERD Diagram](docs/design/earlai.erd.json)** — 10 entities, 48 columns, 6 relationships (open in [erd-editor.io](https://erd-editor.io) or VS Code)
- **[Architecture Diagram](docs/design/architecture.html)** — Full system architecture (open in browser, supports PNG/PDF export)

## What's next for EARL AI

- Expand from 270 to **500+ conditions**
- Add **voice input** in Pidgin
- Support **Hausa, Yoruba, and Igbo**
- **Pre-loaded Raspberry Pi kits** for clinics with no computers
- Make it the **standard clinical tool** for every primary healthcare centre in Nigeria
