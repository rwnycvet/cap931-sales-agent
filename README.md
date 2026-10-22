# Sales Account Research Assistant

**CAP 931 Capstone: Build a Sales Agent Prototype Using Multi-Agent GPT Models**
Richard Watson Jr. · Per Scholas AI Prompt Engineering

A Streamlit app that helps a sales rep prepare for a first meeting. You give it a prospect's website, your product details and competitor URLs. It reads the prospect's public pages and produces a sourced **one-page account brief**: company strategy, leadership, competitor mentions, likely needs and talking points.

- **Live demo:** https://cap931-sales-agent-rwjr.streamlit.app (the app sleeps when idle; the first load can take about 30 seconds)
- **Final report:** [docs/Richard_Watson_Jr_CAP_931_KB_Report.pdf](docs/Richard_Watson_Jr_CAP_931_KB_Report.pdf)
- **Presentation:** [docs/CAP931_Presentation.pdf](docs/CAP931_Presentation.pdf)
- **Sample output:** [docs/sample_account_brief.md](docs/sample_account_brief.md)

---

## How it works

The app uses a **three-step prompt chain** plus plain Python for the jobs that need exact answers.

```
Inputs (form + optional product PDF)
        │
        ▼
Python: fetch pages (requests + BeautifulSoup), strip nav/header/footer
Python: URL safety check (blocks private/internal addresses), auto-find About/Leadership/News/Careers pages
Python: competitor check (is each competitor named on the prospect's pages?)
LLM:    competitor research (summarize each competitor's own homepage)
Python: read product PDF (pypdf)
        │
        ▼
Step 1 – EXTRACT  (LLM)  List only facts stated on the pages
Step 2 – NEEDS    (LLM)  Infer 3–5 needs from company facts only (no product sheet)
Step 3 – WRITE    (LLM)  Write the brief from facts + needs + product info
        │
        ▼
Python: add sources list, header, date → downloadable one-pager (.md)
```

**Why split it up:** with a single prompt, the model mixed product features into the "customer needs" and invented details. Separating extraction, needs analysis and writing, and hiding the product sheet from the needs step, fixed that. Tasks with one right answer (competitor mentions, the sources list) are done in Python, not by the model.

**Model:** `openai/gpt-oss-120b` via the Groq API (free tier, fast inference).

## Inputs

| Field | Required | Example |
|---|---|---|
| Product Name | Yes | GreatShield EDR |
| Company URL | Yes (must start with `http`) | https://www.nymcu.org |
| Extra company pages | No, one per line | About, Leadership, News pages |
| Product Category | No | Endpoint Detection and Response |
| Competitor URLs | No, one per line | https://www.crowdstrike.com |
| Value Proposition | Yes | One sentence on what the product does for the customer |
| Target Customer | Yes | Kelly Gerber, Chief Risk Officer |
| Product overview PDF | No | Product sheet |
| Auto-find pages | Checkbox (on) | Finds up to 5 About, Leadership, News, Careers, Investor pages |
| Research competitor websites | Checkbox (on) | Summarizes each competitor's homepage |

## Run it locally

Requirements: [uv](https://docs.astral.sh/uv/) (it installs the right Python version, 3.14, for you), and a free [Groq API key](https://console.groq.com/keys).

```bash
git clone https://github.com/rwnycvet/cap931-sales-agent.git
cd cap931-sales-agent
uv sync
```

Create a file named `.env` in the project folder:

```
GROQ_API_KEY=your_key_here
```

Start the app:

```bash
uv run streamlit run app.py
```

It opens at http://localhost:8501.

> If you see a 403 error from Groq, turn off your VPN and try again.

## Run the tests

```bash
uv run pytest
```

The 42 tests cover required fields, URL validation (blocking private and internal addresses), page extraction, failed requests, competitor checks, PDF parsing, prompt construction, source preservation, AI model failures, page discovery and competitor research. They use fakes instead of the internet or the Groq API, so they run in under a second with no API key.

## Deployment

The app is deployed on **Streamlit Community Cloud** from this repository's `main` branch. It redeploys automatically on every push.

- `requirements.txt` is generated with `uv export --no-hashes --no-emit-project -o requirements.txt`
- The API key is stored in Streamlit's **Secrets** settings (TOML), never in the repo
- `.env` is listed in `.gitignore`

## Project structure

```
app.py              Streamlit page: form, buttons, messages (imports agent_core)
agent_core.py       All logic: URL safety, page fetching and discovery, competitor check and research, PDF, prompts, model call, one-pager
tests/              42 automated pytest tests for agent_core.py
experiments/        Controlled experiment: chain vs single prompt, gpt-oss-120b vs 20b (script, evidence, results)
requirements.txt    Dependencies for Streamlit Cloud
pyproject.toml      Project metadata (uv)
notes.md            Development log with timestamps
test_groq.py        Early API connection test
test_fetch.py       Early page-fetching test
docs/               Final report, presentation, sample output
```

## Results (standard test case)

Test case: selling **GreatShield EDR** to **Municipal Credit Union (MCU)**, with the Chief Risk Officer as the contact.

- Leadership names and titles checked against MCU's leadership page: **6/6 correct**
- Every company fact traces to a listed source page
- Competitor section comes from the Python check, not the model

## Controlled experiment

`uv run python experiments/run_experiment.py` runs the same saved evidence through three setups, twice each: the 3-step chain and a single prompt on gpt-oss-120b, and the chain on gpt-oss-20b. Results are in [experiments/results/summary.md](experiments/results/summary.md).

- **Chain vs. single prompt:** in both single-prompt runs, all six "likely needs" were product features; the chain runs had none.
- **Found a bug:** with no competitor research available, gpt-oss-120b invented competitor positioning. The prompt now describes competitors only when research exists.
- **120b vs. 20b:** 20b was slightly faster and more cautious; 120b wrote briefs more tailored to the prospect. Two runs each, so this is a trade-off, not a proven ranking.

## Limitations

- Reads the homepage, pages the user enters and up to 5 auto-found pages; it does not search outside news or job boards, and auto-discovery can miss the best page
- "Not mentioned on the website" does not mean "not a customer"; the rep still needs to ask
- Pages built with JavaScript may load empty
- Output wording varies between runs; a human should review the brief before use
- No login or rate limiting yet; the public demo uses a free API quota

## Security notes

- API keys live in `.env` locally and in Streamlit Secrets in production
- User-entered URLs are fetched by the server, so `is_safe_url()` only allows http/https and blocks private, loopback, link-local and reserved IP addresses (SSRF protection); pages over 2 MB are refused
- Web page text is passed to the model, so pages could contain prompt-injection attempts; the brief should always be reviewed

## AI assistance

I built this project with guidance from Claude (Anthropic) as a tutor. AI help is described in the final report.
