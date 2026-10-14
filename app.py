import os
from dotenv import load_dotenv
from groq import Groq
import streamlit as st
import requests
from bs4 import BeautifulSoup

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

def get_page_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    page = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(page.text, "html.parser")
    for tag in soup(["nav", "header", "footer", "script", "style"]):   # NEW
        tag.decompose()                                                 # NEW
    return soup.get_text(separator=" ", strip=True)

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

    prompt = f"""You are a sales research analyst helping a sales rep prepare for a first meeting.
Write a one-page account brief about the target company.

The rep sells {product_name}, a {product_category} product. Its value: {value_proposition}.
The target company's website is {company_url}. The rep will meet with {target_customer}.

Use these headings, with short bullet points under each:
1. Company Strategy: what the company does and its current priorities
2. Leadership: key leaders named in the text and why each matters to this sale
3. Competitor Mentions: use only the competitor check results below
4. Likely Needs
5. Talking Points

Rules:
- Keep it under 350 words. Write for a rep with 10 minutes to prepare.
- Use only the information provided here. If a fact is missing, write 'Unknown – verify'.
- Do not invent names, titles, statistics, case studies, or product features.
- Do not claim the company uses a competitor unless the results say it is mentioned.
- Do not say where facts came from; sources are listed separately.

Competitor check results: {competitor_results}

Homepage text: {website_text}

Other company pages: {extra_text}"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
    )
    st.write(response.choices[0].message.content)

    st.markdown("**Sources**")
    for source in sources:                        # NEW: list every page used
        st.markdown(f"- {source}")