import os

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from agent_core import (
    MAX_EXTRA_CHARS,
    ModelError,
    build_brief_prompt,
    build_competitor_prompt,
    build_extract_prompt,
    build_needs_prompt,
    build_one_pager,
    build_sources_text,
    call_model,
    check_competitors,
    clean_lines,
    competitor_name,
    discover_pages,
    fetch_html,
    get_page_text,
    html_to_text,
    read_pdf_text,
    validate_inputs,
)

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])


def ask_model(prompt):
    """Call the model; on failure show a friendly error and stop the page."""
    try:
        return call_model(client, prompt)
    except ModelError as error:
        st.error(str(error))
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
auto_discover = st.checkbox("Auto-find About, Leadership, News, Careers and Investor pages", value=True)
research_competitors = st.checkbox("Research competitor websites", value=True)

if st.button("Generate"):
    error_message = validate_inputs(product_name, company_url, value_proposition, target_customer)
    if error_message:
        st.error(error_message)
        st.stop()

    try:
        homepage_html = fetch_html(company_url)
    except Exception:
        st.error(f"Could not load {company_url}. Check the address and try again.")
        st.stop()
    full_text = html_to_text(homepage_html)
    website_text = full_text[:4000]

    # Pages to read: the ones the user typed, plus any found on the homepage
    page_urls = clean_lines(extra_pages)
    if auto_discover:
        discovered = discover_pages(company_url, homepage_html, already_have=page_urls)
        if discovered:
            st.info("Auto-found pages: " + ", ".join(discovered))
        page_urls += discovered

    sources = [company_url]
    extra_text = ""
    for page_url in page_urls:
        try:
            page_text = get_page_text(page_url)
            full_text += " " + page_text
            sources.append(page_url)
            extra_text += page_text[:3000] + "\n\n"
        except Exception:
            st.warning(f"Could not load {page_url} – skipped.")
    extra_text = extra_text[:MAX_EXTRA_CHARS]

    competitor_list = clean_lines(competitors_urls)
    competitor_results = check_competitors(competitor_list, full_text)
    for result in competitor_results:
        st.write(result)

    # Research each competitor's own website
    competitor_research = ""
    if research_competitors:
        for url in competitor_list:
            name = competitor_name(url)
            try:
                competitor_text = get_page_text(url)[:3000]
            except Exception:
                st.warning(f"Could not load competitor site {url} – skipped.")
                continue
            profile = ask_model(build_competitor_prompt(name, competitor_text))
            competitor_research += f"{name}:\n{profile}\n\n"
            sources.append(url)
        if competitor_research:
            with st.expander("Competitor research (from their own websites)"):
                st.write(competitor_research)

    product_text = ""
    if product_overview is not None:
        try:
            product_text, page_count = read_pdf_text(product_overview)
            st.success(f"Read {page_count} page(s) from the product PDF.")
        except Exception:
            st.warning("Could not read the PDF – continuing without it.")

    # STEP 1 – EXTRACT facts from the website
    facts = ask_model(build_extract_prompt(website_text, extra_text))
    with st.expander("Step 1 – Facts extracted from the website"):
        st.write(facts)

    # STEP 2 – NEEDS from company facts only
    needs = ask_model(build_needs_prompt(product_category, facts))
    with st.expander("Step 2 – Likely needs (from company facts only)"):
        st.write(needs)

    # STEP 3 – WRITE the brief
    brief = ask_model(build_brief_prompt(
        product_name, product_category, value_proposition, company_url,
        target_customer, needs, product_text, competitor_results, facts,
        competitor_research,
    ))
    st.write(brief)

    sources_text = build_sources_text(sources)
    st.markdown("**Sources**")
    st.markdown(sources_text)

    one_pager = build_one_pager(product_name, target_customer, company_url, brief, sources_text)
    st.download_button(
        label="Download one-pager",
        data=one_pager,
        file_name="account_brief.md",
        mime="text/markdown",
        on_click="ignore",
    )
