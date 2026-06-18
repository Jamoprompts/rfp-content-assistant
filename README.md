# RFP Content Assistant - proof of concept

A small, working prototype of the core loop an AI-enabled RFP team runs: take an
incoming RFP question, pull the right answers from a governed content library,
flag anything stale or unapproved for SME review, and draft a grounded response
that invents nothing.

Built to demonstrate that workflow end to end. The data is fictional
("Meridian Private Markets") so nothing is confidential.

## Why this exists

The pattern is: maintain a content library with SMEs, keep answers accurate and
current, use AI to draft and optimize responses, and keep the process documented
and repeatable. This is a miniature of that, end to end, so a conversation can be
about a real thing I built rather than a thing I am interested in.

## What it does

1. **Retrieve.** Ranks library blocks against an incoming question by keyword overlap and returns the top matches with a confidence label.
2. **Govern.** Flags any block that is stale (older than a set threshold) or not in `approved` status, before it can be used.
3. **Ground.** Assembles a prompt that instructs the model to use only the approved blocks and to say what is missing rather than invent it.
4. **Draft.** Calls Claude if an API key is present; otherwise prints the exact prompt and a deterministic stitched draft so the pipeline runs offline.
5. **Audit.** `--audit` produces a library-health report of every block needing SME attention.

This mirrors how platforms like Responsive and Loopio structure a content library
(reusable, owned, dated answer blocks) without requiring access to them.

## Run it

```
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
notification step.

## What it demonstrates

- Maintaining a governed content library and keeping answers current
- Using AI for drafting with a strict, approved-sources-only, no-fabrication prompt
- Surfacing stale or unapproved content for human review
- Separating the source of truth (the library) from the model (the last step only)
- Documenting the workflow so it reruns with little rework
