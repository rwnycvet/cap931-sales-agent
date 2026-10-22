"""Core logic for the Sales Account Research Assistant.

Nothing in this file uses Streamlit or needs an API key, so every function
here can be tested with pytest (see tests/test_agent_core.py).
app.py imports these functions and only handles the web page.
"""
import ipaddress
import socket
from datetime import date
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

MODEL_NAME = "openai/gpt-oss-120b"
MAX_PAGE_BYTES = 2_000_000  # 2 MB
MAX_PDF_CHARS = 4000


class ModelError(Exception):
    """Raised when the AI model can't be reached or returns nothing."""


# ---------- Input checks ----------

def is_safe_url(url):
    """Return True only for http/https URLs that point to a public IP address."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname:
        return False
    try:
        ip_text = socket.gethostbyname(parsed.hostname)
    except socket.gaierror:
        return False
    ip = ipaddress.ip_address(ip_text)
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        return False
    return True


def validate_inputs(product_name, company_url, value_proposition, target_customer):
    """Return an error message for the user, or None if the inputs are OK."""
    if not company_url.startswith("http"):
        return "Company URL must start with https://"
    if not is_safe_url(company_url):
        return "That Company URL can't be used. It must be a public website."
    if not product_name or not value_proposition or not target_customer:
        return "Please fill in Product Name, Value Proposition, and Target Customer."
    return None


def clean_lines(text):
    """Split a text box into lines, dropping blank lines and extra spaces."""
    return [line.strip() for line in text.splitlines() if line.strip()]


# ---------- Website data ----------

def get_page_text(url):
    """Download a public web page and return its readable text."""
    if not is_safe_url(url):
        raise ValueError(f"Blocked unsafe URL: {url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    page = requests.get(url, headers=headers, timeout=15, stream=True)
    content = page.raw.read(MAX_PAGE_BYTES + 1, decode_content=True)
    if len(content) > MAX_PAGE_BYTES:
        raise ValueError(f"Page too large: {url}")
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["nav", "header", "footer", "script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def competitor_name(url):
    """Turn a competitor URL into a short name: https://www.crowdstrike.com -> crowdstrike."""
    host = urlparse(url).hostname or url
    host = host.removeprefix("www.")
    return host.split(".")[0]


def check_competitors(competitor_urls, website_text):
    """Return one result line per competitor saying if it's named on the prospect's pages."""
    results = []
    for url in competitor_urls:
        name = competitor_name(url)
        if name.lower() in website_text.lower():
            results.append(f"{name}: mentioned on the prospect's website")
        else:
            results.append(f"{name}: not mentioned on the prospect's website")
    return results


# ---------- Product PDF ----------

def read_pdf_text(pdf_file):
    """Return (text, page_count) from a PDF. Text is cut to MAX_PDF_CHARS."""
    reader = PdfReader(pdf_file)
    text = ""
    for pdf_page in reader.pages:
        text += (pdf_page.extract_text() or "") + "\n"
    return text[:MAX_PDF_CHARS], len(reader.pages)


# ---------- AI model ----------

def call_model(client, prompt):
    """Send one prompt to the model. Raise ModelError on any failure."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content
    except Exception as error:
        raise ModelError(
            f"Could not reach the AI model. Check your internet or VPN and try again. Details: {error}"
        ) from error
    if not answer:
        raise ModelError("The AI model returned an empty answer. Please try again.")
    return answer


# ---------- Prompts (3-step chain) ----------

def build_extract_prompt(website_text, extra_text):
    """STEP 1 – EXTRACT facts from the website."""
    return f"""Read the company web page text below and list ONLY facts that are directly stated in it.
Group them under these headings: Company Description, Size & Members, Products & Services, Recent Initiatives, Leaders (name and exact title).
Use short bullet points. Do not interpret, guess, or add anything that is not in the text.
If a heading has nothing, write 'None found'.

Homepage text: {website_text}

Other company pages: {extra_text}"""


def build_needs_prompt(product_category, facts):
    """STEP 2 – NEEDS from company facts only (never sees the product sheet)."""
    return f"""You are a business analyst. Based ONLY on the company facts below, list 3 to 5 likely needs this company may have related to {product_category}.
For each need, give one short reason tied to a specific fact from the list.
Do not mention any vendor, product, or product feature. If the facts don't support a need, leave it out.

Company facts:
{facts}"""


def build_brief_prompt(product_name, product_category, value_proposition, company_url,
                       target_customer, needs, product_text, competitor_results, facts):
    """STEP 3 – WRITE the brief using only the extracted facts."""
    return f"""You are a sales research analyst helping a sales rep prepare for a first meeting.
Write a one-page account brief about the target company.

The rep sells {product_name}, a {product_category} product. Its value: {value_proposition}.
The target company's website is {company_url}. The rep will meet with {target_customer}.

Use these headings, with short bullet points under each:
1. Company Strategy: what the company does and its current priorities
2. Leadership: key leaders and why each might matter to this sale
3. Competitor Mentions: use only the competitor check results below
4. Likely Needs: use only the needs analysis below, keeping each reason
5. Talking Points

Rules:
- Keep it under 350 words. Write for a rep with 10 minutes to prepare.
- Use only the verified facts below. If something is missing, write 'Unknown – verify'.
- Describe {product_name} using ONLY the value proposition and the product overview below. Do not add features, pricing, or deployment claims that are not in them.
- Do not state what a leader decides, owns, or prefers unless the facts say so. You may suggest why they might care, labeled as 'likely'.
- Do not invent names, titles, statistics, or case studies.
- Do not claim the company uses a competitor unless the results say it is mentioned.
- Do not say where facts came from; sources are listed separately.
- Company Strategy and Likely Needs must come only from the verified company facts, never from the product overview.
- Every statement about a leader's role or interest must include the word 'likely'.
- A competitor not being mentioned on the website does not mean the company doesn't use it. Never describe this as an opening or opportunity.
- Start directly with heading 1. Do not write a title, a meeting line, or a closing note.

Needs analysis (from company facts only): {needs}
Product overview (from uploaded PDF): {product_text or 'None provided'}
Competitor check results: {competitor_results}

Verified facts about the company:
{facts}"""


# ---------- One-pager ----------

def build_sources_text(sources):
    """Turn the list of source URLs into a Markdown bullet list."""
    sources_text = ""
    for source in sources:
        sources_text += f"- {source}\n"
    return sources_text


def build_one_pager(product_name, target_customer, company_url, brief, sources_text, today=None):
    """Build the downloadable Markdown one-pager."""
    if today is None:
        today = date.today().strftime("%B %d, %Y")
    return f"""# Account Brief

- **Product:** {product_name}
- **Meeting with:** {target_customer}
- **Company:** {company_url}
- **Date:** {today}
- **Prepared by:** Sales Account Research Assistant

---

{brief}

---

## Sources
{sources_text}
"""
