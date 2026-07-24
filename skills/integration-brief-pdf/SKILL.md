---
name: integration-brief-pdf
description: Generate branded technical integration-impact PDF briefs from integration notes markdown. Use when the user mentions integration notes, API change notes, integration-impact PDF, migration checklist, SSO/SAML integration notes, breaking or non-breaking changes, skipped issues, or converting an integration markdown file into a PDF.
---

# Integration Brief PDF

Use this skill to convert integration-focused markdown notes into a branded technical PDF for integrators, API consumers, SSO administrators, and implementation teams.

**Design intent:** integrators are busy and the cost of missing a breaking change is high. The PDF must surface "what could break my integration" and "what I have to do" within the first half of page 1, while preserving every line of source detail underneath for the person who has to implement the change.

## Non-negotiables

- Preserve the markdown title exactly.
- Preserve the Summary text exactly.
- Preserve Totals exactly when present.
- Preserve each change heading exactly, including BREAKING / NON-BREAKING / DEPRECATION labels.
- Preserve Source lines exactly.
- Preserve Files lines exactly, including file paths and inline code.
- Preserve What changed text exactly.
- Preserve Impact bullets exactly.
- Preserve Skipped Issues text exactly.
- Preserve Migration Checklist items exactly, including nested checkbox hierarchy.
- Do not invent integration impacts, migration steps, breaking changes, deprecations, or skipped issues.
- If source counts disagree with parsed items, preserve the source text and mention the mismatch only in the final response. Do not add production notes to the customer PDF.

## Output structure

Create a technical PDF with this order:

1. **Masthead.** Exact title. No subtitle.
2. **At-a-glance card.** A visually distinct block at the top of page 1 (0.5 pt navy hairline border, paper-colored background, ~14 pt internal padding) containing, in order:
   - **Counts strip.** Three large-numeral counters side by side: `{n} BREAKING` (orange), `{n} DEPRECATION` (orange), `{n} NON-BREAKING` (navy). Counts are derived strictly from the Summary/Totals text — do not recount changes yourself.
   - **Top actions.** A `Top actions for integrators` sub-heading followed by 1–3 single-line bullets summarizing the most urgent migration steps. Each bullet is the title or first imperative clause of the highest-severity unchecked items in the Migration Checklist, rendered verbatim. Cap at 3. If the checklist has zero unchecked items, omit the sub-heading entirely.
3. **Summary** paragraph (and Totals if present).
4. **Integration-relevant changes.** Each `### ...` change block opens with its exact classification badge ([BREAKING] / [DEPRECATION] / [NON-BREAKING], orange for the first two and navy for NON-BREAKING), followed by the exact change heading. Source / Files / What changed / Impact follow underneath, in source order.
5. **Skipped issues.** Visually secondary (smaller heading, slightly muted ink). Preserve the exact list.
6. **Migration checklist.** Preserve checklist text and nested checklist structure exactly. Render unchecked items with a 3 pt orange left rule running the height of the checklist block to draw the eye.

No cover page by default. Use additional pages as needed; do not shrink technical copy below readable print size to force a one-page output.

## Parsing rules

Use these markdown anchors when present:

- `## Summary`
- `## Changes`
- `### ...`
- `**Source:**`
- `**Files:**`
- `**What changed:**`
- `**Impact:**`
- `## Skipped Issues`
- `## Migration Checklist`

Treat each `###` heading under `## Changes` as a separate integration change. Keep horizontal rules out of the PDF unless needed as section dividers.

For the at-a-glance card:

- Pull BREAKING / DEPRECATION / NON-BREAKING counts from the Summary or Totals text only. If a count is absent, render it as `0` rather than guessing.
- Pull `Top actions for integrators` items by scanning the `## Migration Checklist` for unchecked items (`- [ ] …`) in source order, taking up to 3. Use the item's text verbatim. Do not synthesize or summarize.

## Classification display

Use source classifications exactly. Common labels include:

- BREAKING
- NON-BREAKING
- DEPRECATION
- SKIP

Use orange for BREAKING, DEPRECATION, and all attention markers; navy for NON-BREAKING. Do not reclassify source items.

## Writing rules

- Prefer exact source language over concision.
- Do not rewrite protocol, API, payload, field, serializer, authentication, file path, migration, or checklist wording.
- Do not add marketing copy.
- The labels **At a glance** and **Top actions for integrators** are intentional and approved. Other meta labels — "for busy readers", "dev-provided", "production note", "recommended use" — remain banned unless the user asks for them.
- Keep technical terms as written in the source markdown.

## Visual hierarchy

| Element | Font | Size | Weight | Color | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Document title | Lexend | 22 pt | 600 | navy | 18 pt below |
| At-a-glance card heading | Lexend | 11 pt | 600 | navy | inside card |
| Counts strip — numerals | Lexend | 28 pt | 700 | orange (BREAKING/DEPRECATION) or navy (NON-BREAKING) | aligned baseline |
| Counts strip — labels | Lexend | 9 pt | 600 | matching numeral color | tracked +25, uppercase |
| Top actions bullet | Lexend | 10.5 pt | 400 | ink | navy 2pt round bullet |
| Section heading (`##`) | Lexend | 14 pt | 600 | navy | 16 pt above, 6 pt below |
| Change heading (`###`) | Lexend | 11.5 pt | 600 | navy (label color for the badge prefix) | 12 pt above |
| Body | Lexend | 10 pt | 400 | ink | 1.45 line height |
| Inline code / file paths / payload fields | mono | 9.5 pt | 400 | ink | subtle background tint OK |
| Skipped Issues heading | Lexend | 11 pt | 600 | ink at 80% | smaller than other section headings |
| Checklist unchecked left rule | — | 3 pt | — | orange `#ED601A` | runs height of checklist block |

Page margins: 54 pt top/bottom, 60 pt left/right. Never set body type below 10 pt or mono below 9 pt; add a page instead.

## PDF requirements

- Use Medtrics print defaults: Lexend/Helvetica, navy `#1F3064`, orange `#ED601A`, paper `#FBF9F3`, ink `#2D3448`.
- Use print tokens in `pt` for sizing and spacing.
- Use monospaced styling for inline code, file paths, payload fields, and protocol elements.
- Avoid gradients, shadows, rgba, filters, masks, backdrop filters, and opacity.
- Do not use inline styles.
- Generate screenshots/contact sheet and inspect them. On the contact sheet, confirm: (a) the at-a-glance card sits entirely above the fold of page 1, (b) the BREAKING and DEPRECATION counts (when non-zero) render in orange, (c) the orange left rule appears next to the Migration Checklist whenever any item is unchecked.
- Run overflow checks before final response.
