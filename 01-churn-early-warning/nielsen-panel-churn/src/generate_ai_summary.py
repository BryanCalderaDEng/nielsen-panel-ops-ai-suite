"""
generate_ai_summary.py
---------------------------------
Takes the numeric output of detect_churn_risk.py (outputs/detection_summary.json)
and calls the Claude API to produce a plain-English operational briefing --
the kind of artifact a Panel Operations supervisor would actually read
instead of a raw CSV.

This is the "AI-Assisted Workflows / Intelligent Scorecards" piece of the
JD: the model doesn't invent numbers, it narrates numbers you already
computed deterministically. That distinction (LLM for communication, not
for arithmetic) is worth stating explicitly in an interview.

Requires: ANTHROPIC_API_KEY environment variable.
Run:
    python generate_ai_summary.py
"""

import json
import os
from anthropic import Anthropic

OUT_DIR = "../outputs"


PROMPT_TEMPLATE = """You are a Panel Operations analyst writing a daily briefing for a supervisor at Nielsen. \
You are given a JSON object with churn-risk detection results for a synthetic TV/audio measurement panel. \
Write a concise operational briefing (under 300 words) with three sections:

1. HEADLINE — one sentence, the single most important thing to know today.
2. AT-RISK PANELISTS — summarize the top-risk cohort (don't list all 15 individually; group by
   market/pattern, e.g. "8 of the top 15 at-risk panelists are concentrated in Monterrey and show
   a compliance drop paired with missing-report days, suggesting equipment issues rather than
   voluntary disengagement").
3. RECOMMENDED ACTIONS — 2-3 concrete, operational next steps a panel ops team could take this week.

Be specific and quantitative where the data supports it. Do not invent numbers not present in the
JSON. Write in a direct, professional tone -- no filler, no "I hope this finds you well."

DETECTION RESULTS JSON:
{data}
"""


def main():
    with open(f"{OUT_DIR}/detection_summary.json") as f:
        summary_data = json.load(f)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Skipping live API call and writing a")
        print("placeholder so the pipeline still runs end-to-end for the demo.")
        briefing = (
            "[PLACEHOLDER -- set ANTHROPIC_API_KEY to generate a live briefing]\n\n"
            f"Total panelists monitored: {summary_data['total_panelists']}\n"
            f"High-risk panelists (score >= {summary_data['alert_threshold']}): "
            f"{summary_data['high_risk_count']}\n"
            f"Market-level anomaly days flagged: {summary_data['market_anomaly_count']}"
        )
    else:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": PROMPT_TEMPLATE.format(data=json.dumps(summary_data, indent=2)),
            }],
        )
        briefing = "".join(
            block.text for block in message.content if block.type == "text"
        )

    with open(f"{OUT_DIR}/daily_briefing.txt", "w") as f:
        f.write(briefing)

    print(briefing)
    print("\nWrote: outputs/daily_briefing.txt")


if __name__ == "__main__":
    main()
