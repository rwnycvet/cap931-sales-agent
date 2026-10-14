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
Experiments: “Prompt v1 (full app): model can’t open URLs; it answered from memory and invented stats and features (hallucination). No sources.”
Challenges: “401 Invalid API Key: .env was changed by accident; generated a new key.”
Prompt v2: added "use only provided info / no invented stats" rule → [what changed]
Prompt v2: added "use only provided info, write 'Unknown – verify', no invented stats"
→ fake case study and made-up numbers gone; but company facts all Unknown.
Conclusion: prompt rules reduce hallucination but can't add facts → need real web data.