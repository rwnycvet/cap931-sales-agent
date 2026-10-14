# CAP 931 Notes

## Time Log
Oct 11 – 5:38–8:00pm – built input form, connected Groq, first prompt experiments

## Challenges
- IndentationError: ...
- Groq 403 error: ...

## Experiments
Baseline:  vague question → ~1,000 words, unfocused
V1:        + length/format/audience (busy exec) → ~70 words, 8 items, strategic tone
V1 rerun:  same prompt → 7 items, different wording (output varies)
V2:        audience → new sales rep → same length/format, task-focused tone
---

# Oct 14, 2026 – Session Notes

## Time Log
| Time | Task | Duration |
|---|---|---|
| 10:19 – 10:57 | Fixed SyntaxError on file uploader line (quote/parenthesis placement); found unsaved edits; turned on VS Code Auto Save | ~40 min |
| 10:57 – 11:58 | Added Groq setup to app.py; learned f-strings and 4-part prompt structure; connected Generate button to the model | ~60 min |
| 12:09 – 12:17 | Troubleshot 401 Invalid API Key; generated new Groq key | ~10 min |
| 12:35 – 12:53 | First full app runs; found hallucinations; corrected test inputs (prospect vs. competitor) | ~20 min |
| 13:07 – 13:15 | Prompt v2: anti-hallucination rule; fixed quotes-inside-string error | ~10 min |
| 13:21 – 13:47 | Built website fetch (requests + BeautifulSoup); created get_page_text() function; Prompt v3 with real website text | ~25 min |
| **Total** | | **~3 hrs (with breaks, 10:19 – 13:52)** |

## Test Inputs
| Field | Value |
|---|---|
| Product Name | GreatShieldEDR (fictional product) |
| Product Category | Cybersecurity |
| Value Proposition | Enterprise-grade breach protection built for mid-sized teams |
| Company URL (prospect) | https://www.nymcu.org (Municipal Credit Union) |
| Competitors | crowdstrike.com |
| Target Customer | CISO |

## Experiments: Prompt Versions

### Prompt v1: 4-part structure (Role, Task, Context, Output rules)
"You are a sales research analyst helping a sales rep prepare for a first meeting. Write a short account brief about the target company. The rep sells {product_name}, a {product_category} product. Its value: {value_proposition}. The target company's website is {company_url}, and the rep will be meeting with {target_customer}. Keep it under 200 words, use bullet points under three headings: Company Overview, Likely Needs, and Talking Points. Write it for a rep with 10 minutes to prepare."

Result:
- Correct format (3 headings, bullets, short).
- Hallucinated heavily: made-up company size ("30–40 branches, 150–200 employees", which is internally implausible), a fake case study ("similar credit union reduced ransomware risk by 92%"), and invented product features ("<5-minute containment", Splunk/QRadar integration).
- Finding: the model cannot open URLs. It answered from training memory and filled gaps with plausible guesses. No sources.

### Prompt v2: added anti-hallucination rule
Added to end of v1: "Use only the information provided here. If you don't know a fact about the company, write 'Unknown – verify' instead of guessing. Do not invent statistics, case studies, or product features."

Result:
- Fake case study, invented numbers and invented features all gone.
- But company facts became almost all "Unknown – verify" (industry, size, focus). It didn't know MCU is a credit union.
- Guessed HIPAA/GDPR (wrong regulations for a US credit union) but flagged them as Unknown.
- Finding: prompt rules can stop invention, but cannot supply facts the model doesn't have. Real data is needed.

### Prompt v3: added real website text
Code: get_page_text(url) downloads the page (requests) and extracts readable text (BeautifulSoup). The first 4,000 characters of the homepage are added to the prompt.
Prompt change: "Use only the information provided here, including the website text." + "Here is text from the company's website: {website_text}"

Result:
- Grounded facts: identified as a credit union serving New Yorkers; products (checking, savings, loans, mortgages, credit cards, investments); mobile app maintenance Oct 17–18, 2026; Fraud & Security Center on site.
- Unknowns narrowed to 3 specific gaps (IT staff size, current endpoint tool, compliance frameworks), which serve as discovery questions for the CISO.
- Remaining issues:
  - Misread the Fraud & Security Center (a member education page) as a security tool to integrate with.
  - Weak talking point (EDR coverage during app maintenance) from stretching thin data.
  - Claimed "all facts drawn from website text" but added GLBA/FFIEC from training data. The model's statement about its own sources is not reliable.
- Still missing for assignment: competitor mentions, leadership names, press releases/job postings, source links.

### Summary table
| Version | Change | Hallucination | Useful facts |
|---|---|---|---|
| v1 | 4-part prompt | High (fake stats, case study, features) | Unreliable |
| v2 | + "use only provided info" rule | Low | Almost none |
| v3 | + real website text | Low (some misreads) | Good, grounded |

## Challenges & Solutions
- **SyntaxError on file_uploader line**: "(optional)" was placed outside the quotes and the closing parenthesis came too early. Fixed by keeping the whole label inside one pair of quotes and closing the parenthesis at the end of the line.
- **Edits not taking effect**: the file wasn't saved, so Python ran the old code. Turned on VS Code Auto Save.
- **401 Invalid API Key**: the .env file had been changed by accident at 11:06 a.m. Generated a new key at console.groq.com and replaced the line in .env. The error code identified the cause: 403 = network/VPN, 401 = bad key.
- **Wrong test inputs**: first test used CrowdStrike (a security vendor) as the prospect. Corrected so Company URL = the prospect (MCU) and CrowdStrike goes in Competitors.
- **SyntaxError from quotes inside the prompt**: double quotes inside a double-quoted f-string ended the string early. Fixed by using single quotes inside ('Unknown – verify').
- **URL format**: requests needs the full address including https://.

## Concepts Learned
- f-strings: insert variables into text with f"...{variable}..."
- Indentation: code that runs only after the button click is indented under `if`
- Functions: `def name(input):` ... `return result` creates reusable code
- Web scraping basics: requests.get() downloads, BeautifulSoup .get_text() extracts readable text
- Slicing: text[:4000] keeps the first 4,000 characters
- Prompt engineering: 4-part structure; anti-hallucination rules; grounding the model with real data

## AI Assistance
Used Claude as an instructor for explanations, debugging guidance and code patterns. Prompt v1 and the anti-hallucination sentence were drafted with AI assistance; I implemented, ran and evaluated all versions.
## Competitor Mentions (Oct 14)
- Python checks the prospect's full website text for each competitor name (loop + string search, no AI → no hallucination).
- Result: crowdstrike ❌, sentinelone ❌ (expected; homepage doesn't list vendors).
- Positive control: "fraud.com" → ✅, confirms check can detect a match.
- Limitation: only searches the homepage; news/press pages might mention vendors.

Concepts: for loop, .splitlines(), .replace(), .split(), .lower(), if/else, `in`