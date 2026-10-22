import os

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from agent_core import (
    ModelError,
    build_brief_prompt,
    build_extract_prompt,
    build_needs_prompt,
    build_one_pager,
    build_sources_text,
    call_model,
    check_competitors,
    clean_lines,
    get_page_text,
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

if st.button("Generate"):
    error_message = validate_inputs(product_name, company_url, value_proposition, target_customer)
    if error_message:
        st.error(error_message)
        st.stop()

    try:
        full_text = get_page_text(company_url)
    except Exception:
        st.error(f"Could not load {company_url}. Check the address and try again.")
        st.stop()
    website_text = full_text[:4000]

    sources = [company_url]
    extra_text = ""
    for page_url in clean_lines(extra_pages):
        try:
            page_text = get_page_text(page_url)
            extra_text += page_text[:3000] + "\n\n"
            full_text += " " + page_text
            sources.append(page_url)
        except Exception:
            st.warning(f"Could not load {page_url} – skipped.")

    competitor_results = check_competitors(clean_lines(competitors_urls), full_text)
    for result in competitor_results:
        st.write(result)

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
