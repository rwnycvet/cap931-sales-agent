import os
from dotenv import load_dotenv
from groq import Groq
import streamlit as st
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from datetime import date

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def get_page_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    page = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(page.text, "html.parser")
    for tag in soup(["nav", "header", "footer", "script", "style"]):   # NEW
        tag.decompose()                                                 # NEW
    return soup.get_text(separator=" ", strip=True)
def ask_model(prompt):
       try:
           response = client.chat.completions.create(
               model="openai/gpt-oss-120b",
               messages=[{"role": "user", "content": prompt}],
           )
           return response.choices[0].message.content
       except Exception as error:
           st.error(f"Could not reach the AI model. Check your internet or VPN and try again. Details: {error}")
           st.stop()

st.title("Sales Account Research Assistant")

product_name = st.text_input("Product Name")
company_url = st.text_input("Company URL")
extra_pages = st.text_area("Extra company pages: About, Leadership, News (optional, one per line)")
product_category = st.text_input("Product Category")
competitors_urls = st.text_area("Competitors URLs (one per line)")
value_proposition = st.text_area("Value Proposition")
target_customer = st.text_input("Target Customer")
product_overview = st.file_uploader("Product overview PDF (optional)", type=["pdf"])
if st.button("Generate"):
    if not company_url.startswith("http"):
        st.error("Company URL must start with https://")
        st.stop()
    if not product_name or not value_proposition or not target_customer:
        st.error("Please fill in Product Name, Value Proposition, and Target Customer.")
        st.stop()
    full_text = get_page_text(company_url)
    website_text = full_text[:4000]

    sources = [company_url]                       # NEW: list of every page we used
    extra_text = ""                               # NEW: text from the extra pages
    for page_url in extra_pages.splitlines():     # NEW: loop over extra pages
        try:
            page_text = get_page_text(page_url)
            extra_text += page_text[:3000] + "\n\n"
            full_text += " " + page_text
            sources.append(page_url)
        except Exception:
            st.warning(f"Could not load {page_url} – skipped.")

    competitor_results = []
    for url in competitors_urls.splitlines():
        name = url.replace("https://", "").replace("www.", "").split(".")[0]
        if name.lower() in full_text.lower():
            result = f"{name}: mentioned on the prospect's website"
        else:
            result = f"{name}: not mentioned on the prospect's website"
        competitor_results.append(result)
        st.write(result)

    product_text = ""
    if product_overview is not None:
        try:
            reader = PdfReader(product_overview)
            for pdf_page in reader.pages:
                product_text += (pdf_page.extract_text() or "") + "\n"
            product_text = product_text[:4000]
            st.success(f"Read {len(reader.pages)} page(s) from the product PDF.")
        except Exception:
            st.warning("Could not read the PDF – continuing without it.")    

        # STEP 1 – EXTRACT facts from the website
    extract_prompt = f"""Read the company web page text below and list ONLY facts that are directly stated in it.
Group them under these headings: Company Description, Size & Members, Products & Services, Recent Initiatives, Leaders (name and exact title).
Use short bullet points. Do not interpret, guess, or add anything that is not in the text.
If a heading has nothing, write 'None found'.

Homepage text: {website_text}

Other company pages: {extra_text}"""

    facts = ask_model(extract_prompt)
    with st.expander("Step 1 – Facts extracted from the website"):
        st.write(facts)
        
    # STEP 2 – NEEDS: from company facts only (never sees the product sheet)
    needs_prompt = f"""You are a business analyst. Based ONLY on the company facts below, list 3 to 5 likely needs this company may have related to {product_category}.
For each need, give one short reason tied to a specific fact from the list.
Do not mention any vendor, product, or product feature. If the facts don't support a need, leave it out.

Company facts:
{facts}"""

    needs = ask_model(needs_prompt)
    with st.expander("Step 2 – Likely needs (from company facts only)"):
        st.write(needs)
        
    # STEP 3 – WRITE the brief using only the extracted facts
    brief_prompt = f"""You are a sales research analyst helping a sales rep prepare for a first meeting.
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

    brief = ask_model(brief_prompt)
    st.write(brief)

    # Build the sources list as text (used on screen AND in the download)
    sources_text = ""
    for source in sources:
        sources_text += f"- {source}\n"

    st.markdown("**Sources**")
    st.markdown(sources_text)

    # Build the one-pager document
    today = date.today().strftime("%B %d, %Y")
    one_pager = f"""# Account Brief

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

    st.download_button(
        label="Download one-pager",
        data=one_pager,
        file_name="account_brief.md",
        mime="text/markdown",
        on_click="ignore",
    )