# aiact-check

A CLI scanner that checks your AI-powered project for **EU AI Act** compliance — detects AI usage, flags prohibited practices, classifies risk tier, generates an obligation checklist, tracks regulatory deadlines, and scaffolds compliance docs.

> ⚠️ **Disclaimer:** aiact-check provides heuristic guidance only and does **not** constitute legal advice. Consult a qualified professional for compliance decisions.

## Why

EU AI Act deadlines have arrived — prohibitions since **Feb 2025**, Article 50 transparency since **Aug 2026**, high-risk (Annex III) obligations by **Dec 2027** — but tooling is enterprise-grade. Solo devs and small teams shipping AI features have no lightweight way to answer:

- Does my project fall under the AI Act at all?
- Am I close to a **prohibited practice** (Art. 5)?
- Do I have **transparency obligations** (chatbots, synthetic content, deepfakes)?
- Is my system **high-risk** (Annex III)?
- What do I need to do, **by when**?

`aiact-check` answers these offline, in seconds, with zero mandatory dependencies.

## Install

```bash
pip install aiact-check          # (once published) — or:
pip install git+https://github.com/fuleinist/aiact-check

# optional YAML report output
pip install "aiact-check[yaml]"
```

Requires Python ≥ 3.10. Stdlib-only at runtime (`pyyaml` optional).

## Usage

### Scan a project

```bash
aiact-check scan .                       # terminal summary
aiact-check scan my-app --format json --output report.json
aiact-check scan my-app --format markdown
```

Exit codes: `0` = clean/limited risk · `1` = transparency or high-risk obligations · `2` = prohibited-practice signals · `3` = usage/scan error.

### Deadlines

```bash
aiact-check deadlines
```

### Scaffold compliance docs

```bash
aiact-check init-docs                    # creates aiact-compliance/
aiact-check init-docs --report report.json   # embed live checklist from a scan
```

Generates `AI_POLICY.md`, `TECHNICAL_DOCUMENTATION.md` (Annex IV skeleton), `TRANSPARENCY_NOTICE.md` (Art. 50 templates), and `CHECKLIST.md`.

### Project context (`aiact-check.toml`)

Declare what the scanner can't infer:

```toml
[project]
role = "provider"        # provider | deployer | both
market = "eu"            # eu | none
users = "consumers"

[classification]
chatbot = true
generates_content = ["text", "audio"]
# override = "high-risk" # force a tier
# high_risk_domain = "employment"
```

## How it works

1. **Scan** — walks the project, parses manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`) against a curated AI library registry, and matches ~25 regex heuristics over source files (LLM API calls, prompt construction, face recognition, emotion recognition, social scoring, HR screening, credit scoring, deepfake generation, …).
2. **Classify** — maps detections + your config onto the AI Act pyramid: `prohibited` → `high-risk` → `transparency` → `limited` → `none`. Every finding explains **why** it triggered and cites the article (Art. 5, Annex III, Art. 50…).
3. **Obligations** — builds a concrete checklist per tier (Art. 4 literacy, Art. 50(1)/(2)/(4) transparency, Art. 9–17 + 43/47/49 high-risk set, Art. 53 GPAI), each with deadline and severity. Obligations whose deadline has passed escalate to `action-required`.
4. **Report** — terminal, JSON (stable schema v1.0), YAML, or markdown.

Rules live in data tables (`aiact_check/knowledge.py`) — extend by adding entries, no logic changes.

## Limitations (by design)

- Heuristic static analysis: false positives/negatives are possible; every finding asks you to verify context.
- No behavioural analysis of trained models, no network calls, no telemetry.
- Jurisdiction: the Act's extraterritorial reach (Art. 2) means "market = none" is not a safe harbour if output is used in the EU.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
