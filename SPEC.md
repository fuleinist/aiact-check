# aiact-check — SPEC

A CLI scanner that checks your AI-powered project for EU AI Act compliance.

## Problem

EU AI Act compliance deadlines have arrived (GPAI + Article 50 transparency: Aug 2, 2026;
high-risk obligations: Dec 2, 2027), but tooling is enterprise-grade. Solo developers and
small teams shipping AI features have no lightweight way to know:

- Does my project fall under the AI Act at all?
- Am I using a banned practice (Article 5)?
- Do I have Article 50 transparency obligations (chatbots, synthetic content, deepfakes)?
- Is my system high-risk (Annex III)?
- What documentation do I need, and by when?

## Features

### F1 — Project scanning (`aiact-check scan`)
Statically scan a project directory for AI/ML usage signals:
- Dependency manifests: `requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`,
  `go.mod`, `Gemfile` — match against a curated registry of AI libraries/providers
  (openai, anthropic, langchain, transformers, torch, ollama, elevenlabs, replicate, ...)
- Source code heuristics: LLM API calls, prompt strings, model loading, generation endpoints
- Output: detected AI capabilities classified by role (provider SDK, local model,
  speech, vision, embeddings, agent framework)

### F2 — Risk classification
Classify detected capabilities against the AI Act pyramid:
- **Prohibited (Art. 5)**: social scoring, manipulative/subliminal techniques, untargeted
  facial-image scraping, emotion recognition at work/school, biometric categorisation for
  sensitive attributes, real-time remote biometric ID in public spaces (law-enforcement carve-outs aside)
- **High-risk (Annex III)**: employment/HR screening, credit scoring, education assessment,
  critical infrastructure, law enforcement, migration, judicial, essential services eligibility
- **Transparency risk (Art. 50)**: chatbots/conversational agents, synthetic content generation
  (text/audio/image/video), deepfake generation, emotion recognition (non-banned contexts)
- **Limited/minimal risk**: everything else
Classification is heuristic and rules-based; every finding explains WHY it triggered and cites the article.

### F3 — Obligation checklist generation
Based on classification, generate a concrete obligation checklist:
- Art. 50(1): inform users they are interacting with AI (chatbots)
- Art. 50(2): mark synthetic content machine-readably (providers of generative systems)
- Art. 50(4): label deepfakes / AI-generated public-interest text
- Art. 53: GPAI model documentation, copyright policy, training-data summary (if training/fine-tuning a GPAI model)
- High-risk (Art. 8–15): risk management, data governance, technical documentation, logging,
  transparency to deployers, human oversight, accuracy/robustness/cybersecurity
Each checklist item: obligation text, applies-to (provider/deployer), status (todo), article reference.

### F4 — Deadline tracking (`aiact-check deadlines`)
Show the compliance timeline relative to today's date:
- 2025-02-02: prohibitions + AI literacy (Art. 5, Art. 4) — PASSED
- 2025-08-02: GPAI obligations, governance, penalties — PASSED
- 2026-08-02: Article 50 transparency, most remaining provisions — PASSED (in force)
- 2027-08-02: GPAI models placed on market before 2025-08-02 must comply
- 2027-12-02: high-risk systems (Annex III) placed on market before 2026-08-02
Mark each as past/due, with days remaining for future ones. If an obligation applies and its
deadline has passed → finding severity escalates to `action-required`.

### F5 — Report output (`scan --format json|yaml|markdown`)
- Machine-readable JSON/YAML report: project info, detections, classification, findings,
  obligations, deadline status
- Human-readable markdown report (default: terminal summary)
- `--output FILE` to write report to disk
- Exit codes: 0 = clean/limited risk, 1 = transparency/high-risk obligations found,
  2 = prohibited-practice signals found, 3 = usage/scan error

### F6 — Compliance docs scaffolding (`aiact-check init-docs`)
Generate starter compliance documentation in `aiact-compliance/`:
- `AI_POLICY.md` — usage policy template
- `TECHNICAL_DOCUMENTATION.md` — Annex IV skeleton (for high-risk)
- `TRANSPARENCY_NOTICE.md` — Art. 50 user-facing notice template
- `CHECKLIST.md` — current obligations from last scan (if report available)
Never overwrite existing files without `--force`.

### F7 — Project metadata (`aiact-check.toml`)
Optional config file to declare context the scanner cannot infer:
```toml
[project]
role = "provider"          # provider | deployer | both
market = "eu"              # eu | none — is the system placed on the EU market?
users = "consumers"        # consumers | business | internal

[classification]
override = "transparency"  # force a risk tier
chatbot = true             # explicit flags the scanner uses
generates_content = ["text", "audio"]
high_risk_domain = ""      # e.g. "employment"
```
Scanner still runs; config resolves ambiguity rather than replacing detection.

## Non-goals
- Not legal advice; reports carry a prominent disclaimer
- No network calls, no telemetry — fully offline static analysis
- No scanning of trained model behaviour, only code/config/deployment signals
- No EU-market jurisdiction detection beyond user declaration

## Architecture
- Python ≥3.10, zero mandatory runtime deps (stdlib only; `pyyaml` optional for YAML output,
  TOML via stdlib `tomllib`)
- Package layout:
  ```
  aiact_check/
    __init__.py        # version
    __main__.py        # python -m aiact_check
    cli.py             # argparse-based CLI (scan, deadlines, init-docs, version)
    scanner.py         # file discovery, manifest parsing, code heuristics
    knowledge.py       # AI library registry, banned/high-risk/Art.50 rule tables
    classifier.py      # detections -> risk classification + findings
    obligations.py     # classification -> obligation checklist + deadline status
    report.py          # JSON / YAML / markdown / terminal renderers
    docs.py            # init-docs templates
    config.py          # aiact-check.toml loading/merging
  tests/               # pytest suite, fixtures per feature
  ```
- Rules live in data tables (`knowledge.py`) — easy to extend, easy to test

## Acceptance criteria
- AC1: `aiact-check scan <dir>` on a fixture project with `openai` in requirements.txt
  detects the dependency, classifies transparency risk (if chatbot signals) or limited risk,
  exits 0/1 per spec
- AC2: a fixture with social-scoring signals (e.g. code computing "social score" from
  behaviour data) produces a prohibited-practice finding and exit code 2
- AC3: `--format json` emits a valid, stable-schema report parseable by `json.loads`
- AC4: `aiact-check deadlines` prints all 5 milestones with correct past/future state
  for the current date
- AC5: `aiact-check init-docs` creates the 4 template files; second run without `--force`
  exits non-zero-ish gracefully (skips, tells user)
- AC6: `aiact-check.toml` with `override = "high-risk"` forces high-risk classification
- AC7: full pytest suite green; ≥30 tests; no network access in tests
- AC8: stdlib-only install works (`pip install -e .` without extras) and CLI entry point runs

## Build cycles
1. SPEC + repo scaffold + pyproject + CLI skeleton
2. knowledge.py rule tables + scanner (manifests + code heuristics)
3. classifier + obligations + deadlines
4. report renderers (json/markdown/terminal; yaml optional)
5. init-docs + config file
6. tests + fixtures, fix gaps
7. README, polish, final verify, tag v0.1.0
