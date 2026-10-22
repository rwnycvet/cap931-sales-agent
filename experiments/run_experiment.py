"""Controlled experiment for the CAP 931 report (Fix #6).

Question 1: Does the 3-step prompt chain beat a single prompt?
Question 2: How does gpt-oss-120b compare with a different model on the same evidence?

Controlled: every run uses the SAME evidence (pages are downloaded once and
saved to evidence.json), the same product PDF, and the same rules.
Changed: only the prompt design (chain vs single) or the model.

Run from the project folder:
    uv run python experiments/run_experiment.py

Results are saved in experiments/results/ (one .md per run + summary.md).
"""
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent_core import (  # noqa: E402
    ModelError,
    build_brief_prompt,
    build_extract_prompt,
    build_needs_prompt,
    call_model,
    check_competitors,
    get_page_text,
    read_pdf_text,
)

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
EVIDENCE_FILE = HERE / "evidence.json"
PDF_FILE = HERE / "GreatShield_Product_Overview.pdf"

MAIN_MODEL = "openai/gpt-oss-120b"
ALTERNATIVE_MODELS = ["llama-3.3-70b-versatile", "openai/gpt-oss-20b"]  # first one that works is used
RUNS_PER_CONDITION = 2
PAUSE_SECONDS = 20  # stay under Groq free-tier rate limits

# Standard test case
CASE = {
    "product_name": "GreatShield EDR",
    "company_url": "https://www.nymcu.org",
    "extra_pages": [
        "https://www.nymcu.org/about-mcu/",
        "https://www.nymcu.org/about-mcu/leadership-team",
        "https://www.nymcu.org/about-mcu/mcu-in-the-community",
    ],
    "product_category": "Endpoint Detection and Response (EDR)",
    "competitors": ["https://www.crowdstrike.com", "https://www.sentinelone.com"],
    "value_proposition": ("Enterprise-grade endpoint protection with audit-ready compliance reporting, "
                          "built for mid-sized financial institutions without large security teams."),
    "target_customer": "Kelly Gerber, Chief Risk Officer",
}

# Ground truth from MCU's leadership page (checked by hand: 6/6 earlier)
REAL_EXECUTIVES = ["Kyle Markland", "Kelly Gerber", "Cania Infante", "Frank Madeira", "Jim Mill",
                   "Michael Savino", "Toni-Ann Sforza", "Andrew Weltman"]
HEADINGS = ["Company Strategy", "Leadership", "Competitor Mentions", "Likely Needs", "Talking Points"]
# Words that only appear in the product sheet. If they show up under "Likely Needs",
# the model mixed product features into the customer's needs.
PRODUCT_WORDS = ["isolation", "rollback", "triage", "agent", "console", "ncua", "greatshield"]


# ---------- Evidence (collected once, reused by every run) ----------

def collect_evidence():
    if EVIDENCE_FILE.exists():
        print(f"Using saved evidence from {EVIDENCE_FILE.name}")
        return json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
    print("Downloading pages (once)...")
    full_text = get_page_text(CASE["company_url"])
    website_text = full_text[:4000]
    extra_text = ""
    for url in CASE["extra_pages"]:
        page_text = get_page_text(url)
        extra_text += page_text[:3000] + "\n\n"
        full_text += " " + page_text
    product_text = ""
    if PDF_FILE.exists():
        product_text, _ = read_pdf_text(str(PDF_FILE))
    else:
        print(f"WARNING: {PDF_FILE.name} not found – running without the product sheet.")
    evidence = {
        "website_text": website_text,
        "extra_text": extra_text,
        "product_text": product_text,
        "competitor_results": check_competitors(CASE["competitors"], full_text),
    }
    EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence


# ---------- The two prompt designs ----------

def run_chain(client, model, ev):
    facts = call_model(client, build_extract_prompt(ev["website_text"], ev["extra_text"]), model)
    needs = call_model(client, build_needs_prompt(CASE["product_category"], facts), model)
    return call_model(client, build_brief_prompt(
        CASE["product_name"], CASE["product_category"], CASE["value_proposition"],
        CASE["company_url"], CASE["target_customer"], needs, ev["product_text"],
        ev["competitor_results"], facts), model)


def run_single(client, model, ev):
    """Everything in one prompt: raw page text + product sheet + the same rules."""
    raw_pages = f"Homepage text: {ev['website_text']}\n\nOther company pages: {ev['extra_text']}"
    prompt = build_brief_prompt(
        CASE["product_name"], CASE["product_category"], CASE["value_proposition"],
        CASE["company_url"], CASE["target_customer"],
        needs="(work out the likely needs yourself from the company facts)",
        product_text=ev["product_text"], competitor_results=ev["competitor_results"],
        facts=raw_pages)
    return call_model(client, prompt, model)


# ---------- Automatic scoring ----------

def section(text, start, end):
    match = re.search(start + r"(.*?)" + end, text, re.S | re.I)
    return match.group(1) if match else ""


def score(brief):
    normalized = brief.replace("\u2011", "-").replace("\u2010", "-").replace("\u202f", " ").replace("\u00a0", " ")
    needs = section(normalized, "Likely Needs", "Talking Points").lower()
    leadership = section(normalized, "Leadership", "Competitor Mentions")
    # Names written like "First Last – Title" in the Leadership section
    named = set(re.findall(r"^[\s*\-•]*(?:\*\*)?([A-Z][a-zA-Z'\-\.]+(?: [A-Z][a-zA-Z'\-\.]+)+)(?:\*\*)?\s*[–—-]\s",
                           leadership, re.M))
    invented = sorted(n for n in named if not any(n in real or real in n for real in REAL_EXECUTIVES))
    return {
        "words": len(brief.split()),
        "headings": sum(h.lower() in normalized.lower() for h in HEADINGS),
        "real_leaders": sum(name in normalized for name in REAL_EXECUTIVES),
        "invented_names": invented,
        "product_words_in_needs": sorted(w for w in PRODUCT_WORDS if w in needs),
    }


# ---------- Main ----------

def pick_alternative(client):
    for model in ALTERNATIVE_MODELS:
        try:
            call_model(client, "Reply with the word OK.", model)
            return model
        except ModelError as error:
            print(f"  {model} not available: {error}")
    return None


def main():
    load_dotenv()
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    RESULTS.mkdir(exist_ok=True)
    evidence = collect_evidence()

    alternative = pick_alternative(client)
    conditions = [("A_chain_gpt-oss-120b", run_chain, MAIN_MODEL),
                  ("B_single_gpt-oss-120b", run_single, MAIN_MODEL)]
    if alternative:
        conditions.append((f"C_chain_{alternative.split('/')[-1]}", run_chain, alternative))

    rows = []
    for name, runner, model in conditions:
        for run in range(1, RUNS_PER_CONDITION + 1):
            print(f"Running {name}, run {run}...")
            start = time.time()
            try:
                brief = runner(client, model, evidence)
            except ModelError as error:
                print(f"  FAILED: {error}")
                rows.append((name, run, None, None))
                time.sleep(PAUSE_SECONDS)
                continue
            seconds = round(time.time() - start, 1)
            result = score(brief)
            (RESULTS / f"{name}_run{run}.md").write_text(
                f"# {name} – run {run}\n\nModel: {model}\nTime: {seconds} s\n"
                f"Auto-score: {result}\n\n---\n\n{brief}\n", encoding="utf-8")
            rows.append((name, run, seconds, result))
            print(f"  done in {seconds} s: {result}")
            time.sleep(PAUSE_SECONDS)

    lines = ["# Experiment results", "",
             "Same evidence for every run (evidence.json). Auto-scores only; "
             "fill in the 'Unsupported claims' column by reading each brief.", "",
             "| Condition | Run | Time (s) | Words | Headings (of 5) | Real leaders | Invented names "
             "| Product words in Needs | Unsupported claims (manual) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, run, seconds, r in rows:
        if r is None:
            lines.append(f"| {name} | {run} | failed | | | | | | |")
        else:
            lines.append(f"| {name} | {run} | {seconds} | {r['words']} | {r['headings']} | "
                         f"{r['real_leaders']} | {', '.join(r['invented_names']) or 'none'} | "
                         f"{', '.join(r['product_words_in_needs']) or 'none'} | |")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved {RESULTS / 'summary.md'}")


if __name__ == "__main__":
    main()
