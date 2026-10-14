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
    return soup.get_text(separator=" ", strip=True)

st.title("Sales Account Research Assistant")

product_name = st.text_input("Product Name")
company_url = st.text_input("Company URL")
product_category = st.text_input("Product Category")
competitors_urls = st.text_area("Competitors URLs (one per line)")
value_proposition = st.text_area("Value Proposition")
target_customer = st.text_input("Target Customer")
product_overview = st.file_uploader("Product overview PDF (optional)", type=["pdf"])
if st.button("Generate"):



    website_text = get_page_text(company_url)[:4000]

    prompt = f"You are a sales research analyst helping a sales rep prepare for a first meeting. Write a short account brief about the target company. The rep sells {product_name}, a {product_category} product. Its value: {value_proposition}. The target company's website is {company_url}, and the rep will be meeting with {target_customer}. Keep it under 200 words, use bullet points under three headings: Company Overview, Likely Needs, and Talking Points. Write it for a rep with 10 minutes to prepare. Use only the information provided here, including the website text. If you don't know a fact about the company, write 'Unknown – verify' instead of guessing. Do not invent statistics, case studies, or product features, Here is text from the company's website: {website_text}."
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
)
    st.write (response.choices[0].message.content)
