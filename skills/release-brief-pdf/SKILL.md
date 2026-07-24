---
name: release-brief-pdf
description: Generate concise branded customer-facing PDF release briefs from dev-team markdown release notes. Use when the user mentions release notes, deploy notes, milestone notes, customer-facing release brief, branded release PDF, or converting a markdown release note file into a PDF.
---

# Release Brief PDF

Use this skill to convert dev-team markdown release notes into a concise branded customer-facing PDF.

**Design intent:** the PDF must be scannable in 15 seconds and complete in 90. A busy program director, DIO, or IT lead should be able to read only the Key takeaways and the bold ledes and still walk away with the right institutional picture. Each release item is its own entry, headed by the ticket identifier and title the client can quote back to support; the supporting prose underneath is for the reader who wants the detail.

## Non-negotiables

- Preserve the markdown release title exactly.
- Preserve the Key takeaways list exactly, including the trailing `[TICKET-ID]` reference chip on each bullet. Render each bullet as a single line; do not wrap an item across more than two lines (if it does, shorten upstream, not in the PDF).
- Preserve the Summary paragraph exactly.
- Preserve each per-ticket entry exactly: the `### [ID] Title` header AND the bold one-line takeaway AND the description. The verbatim ticket title in the header renders exactly as written — do not clean, shorten, or rephrase it in the PDF.
- Keep every ticket identifier with its entry, and render it as a distinct chip in the entry header.
- Do not invent missing release items and do not merge two ticket entries into one.
- If the summary count and itemized count disagree, preserve the summary, include every itemized entry found in the source, and note the mismatch only in the final response. Do not put source-count mismatch notes in the customer PDF.

## Output structure

Create a short PDF with no cover page by default. Start directly with the release title.

Use this order:

1. **Masthead.** Title. No subtitle.
2. **Key takeaways card.** A visually distinct block at the very top of page 1: a 0.5pt navy hairline border, paper-colored background, ~14pt internal padding. Each bullet is a single line with a navy 2pt round dot and ends with its `[TICKET-ID]` reference chip (navy monospace on a light navy-tint background). Any bullet beginning with "Heads up:" renders the prefix in orange (`#ED601A`) bold; the body stays in ink. The whole card sits above Summary and never wraps onto page 2.
3. **Summary** paragraph.
4. **In this release.** One entry per ticket, in source order. Each entry:
   - A header line: the **ticket identifier as a filled navy chip** (white monospace text), immediately followed by the **verbatim ticket title** in navy 600. The title may wrap to two lines; the chip stays on the first line.
   - The **bold one-line takeaway** as the first sentence of the body paragraph (no extra line break between header and body), then the supporting sentences in regular weight.
   - Any entry whose header is prefixed `[!HEADSUP]` renders as an **attention entry**: a 3pt orange left rule running the height of the entry, an orange "Heads up" tag before the chip, and the identifier chip filled in orange instead of navy. The `[!HEADSUP]` marker itself is not printed — it only selects the treatment.
5. **Looking ahead** (when present). Plain paragraph. No special treatment.

Keep the reference chips (`[ID]` in Key takeaways, the filled chip in each entry header) crisp and consistent. They are the client's handle for citing a change with support, so they must be legible, not decorative.

## Writing rules

- Prefer original markdown language over rewritten summaries.
- Reproduce ticket titles verbatim in the entry headers. Do not condense or paraphrase a title or a description unless the user explicitly asks for a shorter customer summary.
- If the user asks for a one-page version, clearly state that descriptions may need to be shortened before making that tradeoff.
- Avoid adding hype or internal language of your own. (Internal-flavored wording that is already inside a verbatim ticket title is preserved as-is; that is expected.)
- The labels **Key takeaways**, **In this release**, and **Looking ahead** are first-class section names from the storyteller output and render verbatim. Other meta labels — "for busy readers", "at a glance", "dev-provided", "production note", "recommended use", "action guide" — remain banned unless the user asks for them.
- Keep the PDF faithful to the markdown source.

## Visual hierarchy

The PDF must read at a glance. Use type and spacing to do most of the work; do not invent new layout elements beyond what's specified here.

| Element | Font | Size | Weight | Color | Spacing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Release title (`#`) | Lexend | 22 pt | 600 | navy `#1F3064` | 18 pt below |
| Key takeaways heading | Lexend | 11 pt | 600 | navy | inside the card, 8 pt below |
| Key takeaways bullet | Lexend | 11 pt | 400 | ink `#2D3448` | 6 pt between bullets |
| Key takeaways "Heads up:" prefix | Lexend | 11 pt | 600 | orange `#ED601A` | inline |
| Reference chip (`[ID]` in a takeaway) | mono | 8.5 pt | 600 | navy on `#ECEFF6` | inline, 3.5pt horizontal padding |
| Section heading (`##`) | Lexend | 14 pt | 600 | navy | 16 pt above, 6 pt below |
| Entry identifier chip (in `### [ID] Title`) | mono | 9 pt | 700 | white on navy `#1F3064` (orange `#ED601A` for a Heads-up entry) | 1pt/5pt padding, 6pt right of it to the title |
| Entry title (verbatim, in `###`) | Lexend | 11.5 pt | 600 | navy | on the header line, 1.3 line height |
| "Heads up" tag (attention entries) | Lexend | 8 pt | 700 | orange `#ED601A`, uppercase, tracked | before the chip |
| Bold body lede (first sentence of an entry) | Lexend | 10.5 pt | 600 | ink | inline with body |
| Body | Lexend | 10.5 pt | 400 | ink | 1.45 line height |
| Attention-entry left rule | — | 3 pt | — | orange `#ED601A` | runs the height of the entry, ~11 pt gap to text |

Entries are separated by ~13 pt of vertical space. Page margins: 54 pt top, 54 pt bottom, 60 pt left and right. Body column width: roughly 480 pt. Never set body type below 10 pt; if content won't fit, add a page rather than shrink type.

## PDF requirements

- Use Medtrics print defaults: Lexend/Helvetica, navy `#1F3064`, orange `#ED601A`, paper `#FBF9F3`, ink `#2D3448`.
- Use print tokens in `pt` for sizing and spacing.
- Render the `{ medtrics }` wordmark + "Medtrics · Confidential" + page `n / total` in the page footer.
- Avoid gradients, shadows, rgba, filters, masks, backdrop filters, and opacity.
- Do not use inline styles.
- Generate screenshots/contact sheet and inspect them. On the contact sheet, confirm: (a) the Key takeaways card sits entirely above the fold of page 1, (b) every entry opens with its identifier chip + verbatim title header followed by a visibly bold first sentence, (c) each `[!HEADSUP]` entry shows the orange left rule, the orange "Heads up" tag, and an orange identifier chip, and every such entry has a matching "Heads up:" takeaway bullet, (d) no stray empty chip renders under the "In this release" heading.
- Run overflow checks before final response.
