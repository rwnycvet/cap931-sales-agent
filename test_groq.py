import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])
response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Explain what a sales account executive does, in under 100 words, as a numbered list, for a new sales rep on their first day."}],
)
print(response.choices[0].message.content)