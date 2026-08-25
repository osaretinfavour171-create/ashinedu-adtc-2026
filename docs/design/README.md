# EARL AI — Design Artifacts

## 1. Entity-Relationship Diagram — `earlai.erd.json`

Models EARL AI's local data layer as entities. There is **no SQL database** — every
entity maps to a real JSON file loaded into memory at startup:

| Entity | Source file |
|---|---|
| `condition` | `app/data/stg_conditions/*.json` (270 files, NSTG 2022) |
| `clinical_feature`, `investigation`, `treatment` | fields inside each condition file |
| `drug` | Nigeria Essential Medicines List 2020 (890 drugs) |
| `drug_interaction` | `app/data/interactions.json` (164 pairs, DDInter v1.0) |
| `pidgin_term`, `pidgin_phrase` | `app/pidgin/pidgin_glossary.json`, `pidgin_phrases.json` |
| `symptom_bit` | `app/binary_matcher.py` SYMPTOM_BITS (57 bits, O(1) matching) |
| `session` | `app/data/conversation_history.json` |

**How to view:** open [erd-editor.io](https://erd-editor.io) in a browser and
import this file (File → Import → JSON), or install the
[VS Code extension](https://marketplace.visualstudio.com/items?itemName=dineug.vuerd-vscode)
and open `earlai.erd.json` directly. Export PNG from the editor for reports.

## 2. Architecture Diagram — `architecture.html`

Standalone dark-themed HTML/SVG diagram of the full pipeline:

```
CHEW terminal → Pidgin NLP → Binary Matcher → Graph Reasoner → Orchestrator
                                    ↓                ↓              ↓
                             Session Store     Knowledge Graph   DocReader / LLM fallback
```

Graph engine handles ~90% of queries in ~1 ms; Qwen 1.5B / MedGemma 4B handle
edge cases via llama.cpp. Everything runs on 127.0.0.1 with zero network egress.

**How to view:** open `architecture.html` in any browser. The toolbar exports
PNG / PDF for the report and Devpost submission.

Generated with [erd-editor](https://github.com/dineug/erd-editor)'s document
format and the design system of
[Cocoon-AI/architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator).
