# Experiment results

Same evidence for every run (evidence.json). Auto-scores only; fill in the 'Unsupported claims' column by reading each brief.

| Condition | Run | Time (s) | Words | Headings (of 5) | Real leaders | Invented names | Product words in Needs | Unsupported claims (manual) |
|---|---|---|---|---|---|---|---|---|
| A_chain_gpt-oss-120b | 1 | 7.7 | 408 | 5 | 5 | none | none | 3 |
| A_chain_gpt-oss-120b | 2 | 40.2 | 539 | 5 | 5 | none | none | 5 |
| B_single_gpt-oss-120b | 1 | 19.0 | 403 | 5 | 5 | none | agent, isolation, ncua, triage | 2 |
| B_single_gpt-oss-120b | 2 | 18.0 | 442 | 5 | 5 | none | agent, isolation, ncua, rollback, triage | 3 |
| C_chain_gpt-oss-20b | 1 | 6.2 | 344 | 5 | 5 | none | none | 2 |
| C_chain_gpt-oss-20b | 2 | 34.2 | 317 | 5 | 5 | none | ncua | 1 |

## Manual review notes

**What counts as an unsupported claim:** a statement about MCU or a competitor that is not in evidence.json (MCU's pages) and not labeled as a guess, for example invented competitor positioning, assets or staff details the pages never mention, or product-sheet claims presented as facts about MCU. Product features listed as customer needs are counted separately by the "Product words in Needs" column.

| Run | Unsupported claims found |
|---|---|
| A1 (chain, 120b) | CrowdStrike "positions itself as a leading EDR provider"; SentinelOne "AI-driven endpoint protection platform" (no competitor info was given); "ATMs and POS terminals" at the Chelsea branch (not on the site) |
| A2 (chain, 120b) | CrowdStrike and SentinelOne positioning (invented, 2); mobile app "runs on development, testing, and customer-facing devices"; VaultRight "adds POS terminals, kiosks, and PCs"; staff "work from multiple sites" (remote/hybrid not on the site) |
| B1 (single, 120b) | Company Strategy lists NCUA/FFIEC compliance as an MCU priority (from the product sheet, not the site); "MCU's small security staff" (from the product sheet). All 6 Likely Needs are product features |
| B2 (single, 120b) | "Emphasizes compliance with banking regulations and a strong risk-management posture" (not on the site); "concerns raised by the COO and CTO" (stated as fact); "limited internal security team". All 6 Likely Needs are product features |
| C1 (chain, 20b) | "Grants to … St. Francis College" (it was a degree-access partnership, not a grant); "small security team" stated about MCU. Talking points are a feature list with little tie to MCU; title shortened to "CL" |
| C2 (chain, 20b) | "Limited security staff" stated about MCU. NCUA/FFIEC appears in Likely Needs |

## Findings

1. **Chain vs. single prompt:** the chain removed product features from Likely Needs (0 product words in both 120b chain runs; in both single-prompt runs all 6 "needs" were GreatShield features). The single prompt also moved product-sheet claims into Company Strategy. The chain does **not** stop speculation: chain runs still added unsupported details.
2. **Invented competitor positioning (4 of 8 claims in the 120b chain runs):** the brief prompt asks for "one line per competitor on its positioning from the competitor research". In this experiment no competitor research was given ("None"), and gpt-oss-120b filled the gap from its own knowledge in both chain runs. The single-prompt and 20b runs wrote "no positioning available" instead. Fix: only ask for positioning when research exists.
3. **120b vs. 20b:** gpt-oss-20b was slightly faster on the first run (6.2 s vs 7.7 s) and made fewer unsupported claims here, but leaked NCUA/FFIEC into needs once and its talking points were generic feature lists. gpt-oss-120b's briefs were more tailored to MCU but more speculative. With only 2 runs each, this is a trade-off to watch, not a proven ranking.
4. **Timing:** every second run took 34-40 s because the Groq free tier throttles after a burst of calls, so only first-run times are compared.
