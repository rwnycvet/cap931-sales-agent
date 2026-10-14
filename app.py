import os
from dotenv import load_dotenv
from groq import Groq
import streamlit as st

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

st.title("Sales Account Research Assistant")

product_name = st.text_input("Product Name")
company_url = st.text_input("Company URL")
product_category = st.text_input("Product Category")
competitors_urls = st.text_area("Competitors URLs (one per line)")
value_proposition = st.text_area("Value Proposition")
target_customer = st.text_input("Target Customer")
product_overview = st.file_uploader("Product overview PDF (optional)", type=["pdf"])
if st.button("Generate"):
    prompt = f"You are a sales research analyst helping a sales rep prepare for a first meeting. Write a short account brief about the target company. The rep sells {product_name}, a {product_category} product. Its value: {value_proposition}. The target company's website is {company_url}, and the rep will be meeting with {target_customer}. Keep it under 200 words, use bullet points under three headings: Company Overview, Likely Needs, and Talking Points. Write it for a rep with 10 minutes to prepare."
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
)
    st.write (response.choices[0].message.content) 