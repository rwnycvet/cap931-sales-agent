import requests
from bs4 import BeautifulSoup

url = "https://www.nymcu.org"                         # the site to download
headers = {"User-Agent": "Mozilla/5.0"}               # look like a normal browser
page = requests.get(url, headers=headers, timeout=15) # download the page
print("Status:", page.status_code)                    # 200 means success

soup = BeautifulSoup(page.text, "html.parser")        # read the HTML
text = soup.get_text(separator=" ", strip=True)       # keep only the words
print(text[:1500])                                    # show the first 1,500 characters