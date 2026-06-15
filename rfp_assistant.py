#!/usr/bin/env python3
"""
RFP Content Assistant - proof of concept
-----------------------------------------
Mirrors the core loop of an AI-enabled RFP team:
  1. A new RFP question comes in.
  2. Retrieve the most relevant blocks from the content library.
  3. Flag stale or unapproved content for SME review (governance).
  4. Assemble a grounded prompt and draft an answer from ONLY the retrieved blocks.

The LLM call is pluggable: if ANTHROPIC_API_KEY is set the script will call Claude;
otherwise it prints the exact assembled prompt and a deterministic stitched draft,
so the pipeline is fully demonstrable offline. Nothing is fabricated: the draft is
built only from library content, and low-confidence / stale matches are surfaced,
never hidden.

Usage:
    python3 rfp_assistant.py "Describe your approach to ESG."
    python3 rfp_assistant.py --audit          # staleness report across the whole library
"""

import json
import re
import sys
import os
from datetime import datetime, date
from pathlib import Path

LIBRARY = Path(__file__).parent / "content_library.json"
STALE_AFTER_DAYS = 365          # content older than this is flagged
TOP_K = 3
STOPWORDS = set("a an the of to and or is are do does your you our we please describe "
                "provide what how many overview approach for in on with across".split())


def tokenize(text):
    toks = re.findall(r"[a-zA-Z]+", text.lower())
    return [t for t in toks if t not in STOPWORDS and len(t) > 2]


def load_blocks():
    data = json.loads(LIBRARY.read_text())
    return data["blocks"]


def score(query_tokens, block):
    """Simple keyword-overlap relevance over question + answer + category."""
    hay = tokenize(block["question"] + " " + block["answer"] + " " + block["category"])
    if not hay:
        return 0.0
    hay_set = set(hay)
    overlap = sum(1 for t in query_tokens if t in hay_set)
    return overlap / max(len(set(query_tokens)), 1)


def days_old(iso):
    d = datetime.strptime(iso, "%Y-%m-%d").date()
    return (date.today() - d).days


def flags_for(block):
    flags = []
    age = days_old(block["last_updated"])
    if age > STALE_AFTER_DAYS:
        flags.append(f"STALE ({age} days old, last updated {block['last_updated']})")
    if block["status"] != "approved":
        flags.append(f"STATUS: {block['status'].upper()}")
    return flags


def retrieve(query, blocks):
    qt = tokenize(query)
    ranked = sorted(((score(qt, b), b) for b in blocks), key=lambda x: x[0], reverse=True)
    return [(s, b) for s, b in ranked if s > 0][:TOP_K]


def confidence(score_val):
    if score_val >= 0.5:
        return "HIGH"
    if score_val >= 0.25:
        return "MEDIUM"
    return "LOW"


def build_prompt(query, hits):
    ctx = "\n\n".join(
        f"[{b['id']} | {b['category']} | updated {b['last_updated']} | {b['status']}]\n{b['answer']}"
        for _, b in hits
    )
    return (
        "You are drafting a response to an RFP question for a private markets firm.\n"
        "Use ONLY the approved content blocks below. Do not invent facts, figures, or claims.\n"
        "If the blocks do not fully answer the question, say what is missing and which SME to ask.\n"
        "Keep the tone professional and concise.\n\n"
        f"RFP QUESTION:\n{query}\n\n"
        f"APPROVED CONTENT BLOCKS:\n{ctx}\n\n"
        "DRAFT RESPONSE:"
    )


def try_claude(prompt):
    """Call Claude if a key + SDK are present; otherwise return None."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def stitched_draft(hits):
    """Deterministic offline draft: stitch the retrieved approved answers."""
    parts = [b["answer"] for _, b in hits if b["status"] == "approved"]
    if not parts:
        return "(No approved content matched. Route to the relevant SME before responding.)"
    return " ".join(parts)


def answer(query):
    blocks = load_blocks()
    hits = retrieve(query, blocks)
    print("=" * 70)
    print(f"RFP QUESTION: {query}")
    print("=" * 70)
    if not hits:
        print("\nNo matching content found. Route to Content Manager / SME to author a new block.")
        return
    print("\nRETRIEVED BLOCKS (review before sending):")
    for s, b in hits:
        line = f"  - {b['id']}  [{confidence(s)} confidence, score {s:.2f}]  {b['category']}"
        print(line)
        for f in flags_for(b):
            print(f"      !! {f}")
    print("\nASSEMBLED PROMPT (what gets sent to Claude/Copilot):")
    prompt = build_prompt(query, hits)
    print("  " + prompt.replace("\n", "\n  "))
    print("\nDRAFT RESPONSE:")
    drafted = try_claude(prompt)
    source = "Claude (live)" if drafted else "offline stitch (set ANTHROPIC_API_KEY for live drafting)"
    if not drafted:
        drafted = stitched_draft(hits)
    print(f"  [{source}]\n  " + drafted.replace("\n", "\n  "))
    stale = [b["id"] for _, b in hits if flags_for(b)]
    if stale:
        print(f"\n  ACTION: {len(stale)} retrieved block(s) need SME review before this goes out: {', '.join(stale)}")


def audit():
    blocks = load_blocks()
    print("CONTENT LIBRARY HEALTH AUDIT")
    print("=" * 70)
    issues = 0
    for b in sorted(blocks, key=lambda x: x["last_updated"]):
        fl = flags_for(b)
        status = "  OK" if not fl else "  FLAG"
        print(f"{status}  {b['id']:<10} {b['category']:<28} updated {b['last_updated']}")
        for f in fl:
            print(f"          -> {f}")
            issues += 1
    print("=" * 70)
    print(f"{len(blocks)} blocks, {issues} flag(s) needing SME attention.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] == "--audit":
        audit()
    else:
        answer(" ".join(sys.argv[1:]))
