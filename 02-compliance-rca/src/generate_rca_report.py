"""
generate_rca_report.py
---------------------------------
Takes the deterministic SQL evidence bundle (../outputs/rca_evidence.json)
and calls the Claude API to draft a structured 5-Whys Root Cause Analysis
report -- the artifact a Panel Operations analyst would attach to an
incident ticket or send to their supervisor.

Same design principle as Project 1: the LLM narrates and structures,
it never invents a number. Every figure in the SQL evidence traces back
to run_rca_queries.py; Claude's job is turning that into the 5-Whys
format and a recommended action, which is a judgment/communication task
suited to an LLM, not an arithmetic one.

Requires: ANTHROPIC_API_KEY environment variable.
"""

import json
import os
from anthropic import Anthropic

OUT_DIR = "../outputs"

PROMPT_TEMPLATE = """You are a Panel Operations analyst at Nielsen writing a formal Root Cause Analysis (RCA) \
for a compliance drop incident, to attach to an internal ticket. You are given SQL query results as evidence.

Write the RCA in this exact structure:

## Incident Summary
One or two sentences: what dropped, where, by how much, since when. Cite the specific numbers from
the evidence.

## 5 Whys
Walk through five sequential "why" questions, each answer grounded in the evidence provided (market,
device_type, and date patterns). If the evidence doesn't support a why beyond a certain point, say so
explicitly rather than speculating further -- for example, "Why the firmware update caused this specific
failure is outside what this data can show; would require the vendor's firmware changelog."

## Recommended Actions
2-3 concrete, operational next steps a panel ops team could take this week.

Rules:
- Do NOT invent any number not present in the JSON evidence.
- Be specific: name the actual market, device_type, and date from the evidence, not placeholders.
- Keep the whole report under 350 words.
- Professional, direct tone -- no filler.

SQL EVIDENCE (JSON):
{data}
"""


def main():
    with open(f"{OUT_DIR}/rca_evidence.json") as f:
        evidence = json.load(f)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Writing a placeholder so the pipeline")
        print("still runs end-to-end for the demo.")
        cohort = evidence["flagged_cohort"]
        report = (
            "[PLACEHOLDER -- set ANTHROPIC_API_KEY to generate a live RCA report]\n\n"
            f"Flagged cohort: {cohort['market']} / {cohort['device_type']} "
            f"(rate change: {cohort['rate_change']})\n"
            f"Estimated incident start: {evidence['estimated_incident_start_date']}"
        )
    else:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": PROMPT_TEMPLATE.format(data=json.dumps(evidence, indent=2)),
            }],
        )
        report = "".join(block.text for block in message.content if block.type == "text")

    with open(f"{OUT_DIR}/rca_report.md", "w") as f:
        f.write(report)

    print(report)
    print(f"\nWrote: {OUT_DIR}/rca_report.md")


if __name__ == "__main__":
    main()
