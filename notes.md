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

Test data can leak into real output, so remove it after testing.

---

# Oct 14, 2026 – Session Notes (Part 2)

## Time Log
| Time | Task | Duration |
|---|---|---|
| 13:56 – 14:38 | Built competitor mention check (for loop + string search); positive control test | ~40 min |
| 14:38 – 14:45 | Prompt v4: competitor results into prompt; Sources section from Python | ~10 min |
| 14:45 – 15:00 | Researched MCU site for extra pages (About, Leadership, Community); no News page found | ~15 min |
| 15:00 – 15:17 | Added extra-pages input + try/except; Prompt v5 with assignment headings; target = Chief Risk Officer | ~20 min |
| **Total** | | **~1 hr 20 min** |

## Competitor Mention Check
- Python searches the prospect's full website text for each competitor name. No AI, so no hallucination.
- Competitor name taken from URL: "https://www.crowdstrike.com" → "crowdstrike" (.replace, .split)
- Case-insensitive match using .lower()
- Results: crowdstrike ❌, sentinelone ❌ (expected; a credit union's site doesn't list security vendors)
- Positive control: "fraud.com" → ✅ "fraud" (proves the check can detect a match, not just fail)
- Lesson: test data (fraud.com) leaked into the brief → remove test values before real runs
- Limitation: "not mentioned on the website" ≠ "not a customer"

## Prompt v4
Changes from v3:
- Competitor check results passed into the prompt as a list
- Added heading: Competitor Mentions
- "Do not claim the company uses a competitor unless the results say it is mentioned"
- "Do not say where facts came from; sources are listed separately"
- Sources section generated by Python (st.markdown), not the model → links are always real

Result: Competitor section matched the Python check exactly; the false "all facts from website" claim was gone.

## Extra Company Pages
- New input box: Extra company pages (one per line)
- Pages used: /about-mcu/, /about-mcu/leadership-team, /about-mcu/mcu-in-the-community
- No News/Press page found on MCU site → press releases not available (limitation)
- Each page: first 3,000 characters added to prompt; full text added to competitor search
- try/except: if a page fails to load, show a warning and continue instead of crashing
- Every successfully loaded page added to the Sources list

## Research Finding: Target Customer
- MCU leadership page has no CISO or CIO
- Chief Risk Officer: Kelly Gerber → used as Target Customer
- Implication: pitch to risk, compliance and audit rather than technical features
- Discovery question: "Who owns cybersecurity decisions at MCU, and how does it report to risk?"

## Prompt v5
Changes from v4:
- Rewritten as a multi-line prompt (f"""...""") for readability
- Headings match the assignment's required outputs: Company Strategy, Leadership, Competitor Mentions, Likely Needs, Talking Points
- Rules section as a bulleted list; added "Do not invent names, titles"
- Word limit raised to 350 for five sections
- Separate labeled inputs: competitor results, homepage text, other company pages

Result:
- Headings matched the assignment
- Talking points tailored to the Chief Risk Officer (risk agenda, regulatory confidence)
- Strategy section used Community page content (MCU Foundation, impact reports)
- Sources listed all 4 pages

Issues found:
- Leadership: model said no names were found, though the leadership page has them. Suspected cause: 3,000-character cutoff keeps only the repeated site menu. Needs testing.
- Logic error: "no competitor lock-in, position as fresh option." Absence of a mention was treated as proof of no vendor.
- Assumptions: said the Chief Risk Officer oversees "security programs" and referenced a "fraud team" (not stated on the site)

## Concepts Learned
- for loop; .splitlines() turns a text box into a list of lines
- Lists: [] creates one, .append() adds to it
- if / else
- String methods: .replace(), .split(), .lower(); `in` to search text
- += adds onto an existing value
- try / except: error handling so one failed page doesn't crash the app
- Triple-quoted f-strings for multi-line prompts
- Positive control: testing that a check can return "yes," not just "no"

---

# Oct 14, 2026 – Session Notes (Part 3)

## Time Log
| Time | Task | Duration |
|---|---|---|
| 15:17 – 15:42 | Reviewed Prompt v5 output; diagnosed missing leadership names with a DEBUG test | ~25 min |
| 15:42 – 15:49 | Fixed get_page_text() to strip site menus; re-tested | ~7 min |
| 15:49 – 15:56 | Reviewed improved output; identified CTO as a second buyer; planned input validation | ~7 min |
| **Total** | | **~40 min** |

## Challenge: Leadership Names Missing
**Problem:** The brief said no leadership names were found, even though the leadership page lists them.

**Hypothesis:** Each extra page was cut to its first 3,000 characters, and every MCU page starts with the same long site menu. The names were further down and got cut off.

**Test (before changing any code):** Added a temporary DEBUG line:
`st.write("DEBUG – Gerber in all text:", "gerber" in full_text.lower(), "| in prompt text:", "gerber" in extra_text.lower())`
- Result: **True | False** → the name was downloaded but did not reach the prompt. Hypothesis confirmed.

**Fix:** In get_page_text(), removed the page's menu and code sections before extracting text:
```python
for tag in soup(["nav", "header", "footer", "script", "style"]):
    tag.decompose()
```
- Because every page goes through this one function, the fix cleaned all pages at once (homepage, About, Leadership, Community).

**Re-test:** DEBUG → **True | True**. DEBUG line then removed.

**Lesson:** Test the cause before changing the code. A one-line True/False check separated "not downloaded" from "downloaded but cut off," which need completely different fixes.

## Results After the Fix
- Leadership section now lists 4 executives with titles (CRO, CTO, CEO, CFO), up from only the name I typed in
- Company facts became specific: member-owned, not-for-profit, 630,000+ members
- New strategy signal found: recent selection of VaultRight for branch workflow (closest thing to a press release)
- Talking points referenced real initiatives (efficiency push, member trust)

## Research Finding: Two Buyers
- Earlier I said there is no CISO or CIO. Correct, but the leadership team has a **Chief Technology Officer (Jim Mill)**.
- Likely buying roles:
  - **CTO (Jim Mill)**: technical evaluator; owns the technology the security tool runs on
  - **Chief Risk Officer (Kelly Gerber)**: business sponsor; owns the risk the tool reduces
- Discovery question: "Who owns cybersecurity decisions at MCU: technology, risk, or both?"

## Remaining Model Issues
- Assumed Kelly Gerber is the "primary decision-maker for security posture" (not stated on the site)
- Still adds regulations from training (GLBA, NYDFS) rather than from source pages
- "Value proposition: Unknown – verify": Value Proposition box was left empty, and the app ran anyway → needs input validation

## Accuracy Check (TO DO)
- [ ] Verify leadership names and titles against https://www.nymcu.org/about-mcu/leadership-team
- Result: __/4 correct

## Next: Input Validation (planned)
- Stop the app with an error if Company URL doesn't start with http, or if Product Name, Value Proposition or Target Customer is empty
- Uses st.error() and st.stop()
- Test 3 cases: missing field, URL without https://, all fields correct

## Concepts Learned
- Debugging with a temporary True/False check (`"word" in text`)
- HTML structure: pages are built from tagged sections (nav, header, footer, main)
- BeautifulSoup: soup([...]) finds sections; .decompose() deletes them
- Why functions matter: one fix in get_page_text() improved every page

---

# Oct 14, 2026 – Session Notes (Part 4)

## Time Log
| Time | Task | Duration |
|---|---|---|
| 15:56 – 16:09 | Added input validation; tested 3 cases; created standard test case | ~15 min |
| 16:09 – 16:24 | Reviewed output with full value proposition; built prompt chaining (v6) | ~15 min |
| 16:24 – 16:57 | Reviewed Step 1 extracted facts; corrected press-release limitation | ~30 min |
| **Total** | | **~1 hr** |

## Input Validation
Added at the start of the Generate block:
- Company URL must start with "http" → otherwise st.error() + st.stop()
- Product Name, Value Proposition and Target Customer must not be empty → otherwise error + stop
- `not variable` = True when a box is empty; `or` = any one missing triggers the error

Tests (3 cases):
| Test | Input | Result |
|---|---|---|
| 1 | Required fields empty | ✅ Red error, no brief generated |
| 2 | URL without https:// | ✅ Red error, no brief generated |
| 3 | All fields valid | ✅ Brief generated normally |

## Standard Test Case (use the same inputs every run so experiments are comparable)
| Field | Value |
|---|---|
| Product Name | GreatShield EDR |
| Company URL | https://www.nymcu.org |
| Extra pages | https://www.nymcu.org/about-mcu/ · https://www.nymcu.org/about-mcu/leadership-team · https://www.nymcu.org/about-mcu/mcu-in-the-community |
| Product Category | Endpoint Detection and Response (EDR) |
| Competitors | https://www.crowdstrike.com · https://www.sentinelone.com |
| Value Proposition | Enterprise-grade endpoint protection with audit-ready compliance reporting, built for mid-sized financial institutions without large security teams. |
| Target Customer | Kelly Gerber, Chief Risk Officer |

## Prompt v5 with full value proposition (single prompt)
Improvements:
- Talking points tied the product to specific leaders (CRO = audit reporting, CTO = lean team, CFO = budget)
- Found a 5th leader (COO) and named NCUA (the correct federal regulator for credit unions)

Problems, showing that single-prompt rules get lost:
- Invented product features: "single pane of glass," "low-maintenance agent," "automated remediation"
- Invented pricing and preferences: "subscription model aligns with CFO's budgeting preferences"
- Stated assumptions as fact: "Jim Mill – decision-maker for security architecture"

## Prompt v6 – Prompt Chaining
Why: one large prompt (raw web text + inputs + many rules) → the model drops some rules.

How:
- Step 1 (extract): the model reads raw web text and lists ONLY stated facts under 5 headings (Company Description, Size & Members, Products & Services, Recent Initiatives, Leaders)
- Step 2 (write): the model