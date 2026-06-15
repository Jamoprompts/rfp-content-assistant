# RFP Content Assistant — proof of concept

A small, working prototype of the core loop an AI-enabled RFP team runs: take an
incoming RFP question, pull the right answers from a governed content library,
flag anything stale or unapproved for SME review, and draft a grounded response
that invents nothing.

Built to understand the StepStone RFP Junior Analyst workflow from the inside.
The data is fictional ("Meridian Private Markets") so nothing is confidential.

## Why this exists

The job is: maintain a content library with SMEs, reconcile data, use AI to draft
and optimize responses, and keep the process documented and repeatable. This is a
miniature of that, end to end, so the conversation can be about a real thing I
built rather than a thing I'm interested in.

## What it does

1. **Retrieve.** Ranks library blocks against an incoming question by keyword overlap and returns the top matches with a confidence label.
2. **Govern.** Flags any block that is stale (older than a set threshold) or not in `approved` status, before it can be used.
3. **Ground.** Assembles a prompt that instructs the model to use *only* the approved blocks and to say what is missing rather than invent it.
4. **Draft.** Calls Claude if an API key is present; otherwise prints the exact prompt and a deterministic stitched draft so the pipeline runs offline.
5. **Audit.** `--audit` produces a library-health report of every block needing SME attention.

This mirrors how platforms like Responsive and Loopio structure a content library
(reusable, owned, dated answer blocks) without requiring access to them.

## Run it

```bash
python3 rfp_assistant.py "Describe your approach to ESG and responsible investing"
python3 rfp_assistant.py "What is your standard fee structure?"   # hits a stale block on purpose
python3 rfp_assistant.py --audit
```

To use live AI drafting: `export ANTHROPIC_API_KEY=...` then `pip install anthropic` and rerun.

## Design choices worth defending in an interview

- **Refuses to fabricate.** If retrieved content is unapproved or no approved block matches, it routes to the SME instead of drafting a confident wrong answer. Bad RFP content is worse than slow RFP content.
- **Staleness is surfaced, not buried.** A 2023 fee answer is flagged loudly; the library audit makes the maintenance backlog visible.
- **The LLM is the last step, not the source of truth.** Facts live in the owned library; the model only assembles and phrases. That separation is the whole point of content governance.

## Honest scope

This is an afternoon prototype, not a production system. Retrieval is keyword
overlap, not embeddings; the library is eight sample blocks; there is no UI or
auth. The point is to demonstrate the workflow and the judgment behind it. Next
steps would be embedding-based retrieval, a real review queue, and an SME
notification step (a natural fit for a Power Automate / Copilot Studio flow).

## How it maps to the JD

| JD line | Where it shows up here |
|---|---|
| Maintain a content library, keep responses accurate and current | `content_library.json` + staleness flags + `--audit` |
| Use AI for drafting and content optimization; craft prompts | `build_prompt()` + pluggable Claude call |
| Reconcile inconsistencies; support routine reporting | the audit report |
| Identify inefficiencies; propose practical solutions | this whole tool, plus the "next steps" automation hook |
| Contribute to SOPs and documentation | this README and the inline docstring |
