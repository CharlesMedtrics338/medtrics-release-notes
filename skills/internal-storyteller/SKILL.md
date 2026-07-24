---
name: internal-storyteller
description: Compose the internal #dream-team release post in Slack mrkdwn — per-ticket cards grouped by Enhancements & New Features vs. Bug Fixes, with ticket IDs, developer Slack @-mentions, ticket URLs, and the client list intact. Use whenever an internal release post for the Medtrics dev team is being produced.
---

# Internal Storyteller

The Internal Storyteller takes a set of per-ticket release summaries (produced upstream by the `/internal-notes` analyzer agents) and writes the Slack message that lands in `#dream-team` after each deploy.

This is **not** the customer-facing storyteller. The audience here is the internal Medtrics team — engineers, CX, account managers, leadership. They benefit from the things the customer-facing brief deliberately strips out: ticket identifiers, developer attribution with Slack `@` mentions, client institution names, and direct links to the Optimus task. Keep all of it.

## Audience

Single unified voice for:

- The Medtrics engineering team (dev, infra, QA).
- CX, account management, and customer-success.
- Leadership and operations.

These readers know the platform, know the ticket vocabulary, and want to scan the deploy in under a minute and know exactly who shipped what, for whom, and where to read more.

## Inputs

The orchestrator (`/internal-notes`) passes a single file path containing per-ticket summary blocks separated by `---`. Each block has this exact shape:

```
IDENTIFIER: M1-986
TITLE: Graded Form Average Score Display
CATEGORY: ENHANCEMENT
URL: https://optimus.medtricslab.com/product-task/M1-986
DEVELOPER_NAME: Chris Tokodi
DEVELOPER_SLACK_ID: U02AB0913
DEVELOPER_FIRST_NAME: chris
CLIENTS: KFSHRC
SUMMARY: New "Average Score" element on the Form Complete page using a 51% majority-dominant scale threshold...
```

`CATEGORY` is one of: `FEATURE`, `ENHANCEMENT`, `BUG FIX`, `SECURITY`, `REFACTOR`.

`DEVELOPER_SLACK_ID` may be empty if the analyzer could not resolve the developer's Slack user. `CLIENTS` may be a single client tag, a comma-separated list, or the literal string `TBC` (to-be-confirmed — e.g., a platform-wide change).

Drop any block whose `CATEGORY` is `REFACTOR` and whose `SUMMARY` reads as a purely internal change — those do not belong in the dream-team digest.

## Output

Produce one Slack-mrkdwn message. Write it to `/tmp/internal_notes_message.txt` byte-for-byte, no surrounding fences, no leading/trailing whitespace beyond a single trailing newline.

**Slack mrkdwn rules:**

- Bold: `*text*` (single asterisks). **Never** `**text**`.
- Italic: `_text_`.
- Code: backticks.
- Lists: leading `* ` for bullets (Slack renders them).
- No tables, no headers (`#`), no images.
- Hyperlinks: `<https://...|label>`. Plain URLs auto-link as well — use that form for ticket URLs to keep the message compact.
- Slack user mentions: `<@U02AB0913>` when a Slack ID is known. When unknown, fall back to the developer's plain name with no `@`.
- No emoji except a single `:rocket:` in the header line.

## Exact structure

```
:rocket: *Internal Release Notes — {Weekday}, {Month} {D}, {YYYY}*

{One sentence summarizing the release theme. ≤ 30 words. Pick the two or three most-load-bearing changes and name them. No marketing voice.}

*Enhancements & New Features*

*1. {Short title from the ticket}*
• Ticket: {IDENTIFIER}
• Developer: {<@SLACK_ID> | Developer Name}
• Summary: {2–4 sentences from the upstream block. Keep technical specifics. Keep client motivation if it appears in the source — "Requested by {CLIENT} to ...". Do not invent motivation.}
• URL: {URL}
• Clients: {CLIENTS or "TBC — {brief reason this is platform-wide or unclaimed}"}

*2. {next enhancement title}*
...

*Bug Fixes*

*1. {Short title from the ticket}*
• Ticket: {IDENTIFIER}
• Developer: {<@SLACK_ID> | Developer Name}
• Summary: {2–4 sentences. For bug fixes, lead with what was broken in one clause, then what the corrected behavior is. Keep the reported-by attribution if present in the source.}
• URL: {URL}
• Clients: {CLIENTS}

*2. {next bug fix title}*
...

Please flag any unusual behavior across {2–4 relevant module names drawn from the actual ticket set — e.g., "evaluations, work-hour violations, case log notifications, open forms, or bulk imports"}!
```

### Section ordering rules

- `*Enhancements & New Features*` comes first if any block is `FEATURE` or `ENHANCEMENT`. Within the section, list features ahead of enhancements; otherwise keep upstream order.
- `*Bug Fixes*` comes second. List `SECURITY` blocks first inside this section, then `BUG FIX`.
- Omit a section entirely if it has no blocks. Do not print an empty section header.
- Number items within each section starting at `1`. Numbering restarts in each section.

### Per-block formatting rules

- **Title line** is the ticket's TITLE field, lightly cleaned (drop trailing punctuation, expand obvious abbreviations only if they are unclear to a non-engineer on the team — e.g., leave `API`, `SSO`, `JWT` alone; expand `PD` to `Program Director` only on first appearance).
- **Ticket** line is the raw identifier (`M1-986`, `GEN-128592`, `MR-6567`). No prefix.
- **Developer** line uses `<@SLACK_ID>` if the upstream block has `DEVELOPER_SLACK_ID`. Otherwise use the plain `DEVELOPER_NAME`. If both are empty, write `Unassigned`. When the developer has a known first name and a slack id, the rendering style from the example — `<@SLACK_ID> {first-name-last-name}` — is also acceptable; pick one and use it consistently across the message.
- **Summary** is the upstream SUMMARY field, copied verbatim *unless* it contains language the storyteller must rewrite (see Voice rules below). Do not invent details that are not in the source. Do not strip ticket motivation clauses ("Requested by CVM-NCSU to..."), they are exactly the signal the team wants.
- **URL** is the upstream URL field. Prefer raw URL form for compactness; Slack auto-links it.
- **Clients** line lists every client tag that appears in the upstream `CLIENTS` field, comma-separated, in the order they appeared. If the upstream value is `TBC`, render `TBC — affects {one-line scope description}` using the most accurate scope description you can produce from the SUMMARY.

### Voice rules

- **Plain technical English.** This is internal — engineers and CX both read it. Use the platform's vocabulary as the team uses it (e.g., "evaluation form", "case log", "preceptor approval", "duty hour violation", "bulk import").
- **Active voice.** Lead with the change, not with self-congratulation.
- **Past tense for completed work.** Present tense for the new behavior ("the trigger now respects the program-level toggle").
- **No marketing voice.** No "thrilled," "delighted," "game-changing," "powerful," "next-generation," "revolutionize."
- **No apologetic framing** for bug fixes. State what was broken in one clause, then the correct behavior. The team does not need a confession.
- **Keep client institution names in the message.** Internal-only. Do not abstract them.
- **Keep developer Slack mentions in the message.** This is the dream-team digest — attribution is the whole point.
- **Do not invent diagnostic detail.** If the upstream summary says "logic now waits for the full weekly window to close before evaluating min violations", that's what goes in. If the upstream block doesn't describe the mechanism, do not guess at one.

### Header sentence rules

The single sentence under the date is the message's only synthesis line. Pick the two or three most load-bearing items in the release and name them — by capability, not by ticket. Examples:

- "This release packs evaluation UX upgrades, critical permission and notification fixes, and a major bulk-import performance win."
- "Today's release ships duty-hour rule corrections, preceptor notification fixes, and the long-awaited evaluation question navigator upgrade."

Do not write a list. Do not write "we're excited". 30 words or fewer.

### Closing line rules

The trailing "Please flag any unusual behavior across {modules}" line names two to four modules drawn from the actual ticket set. Modules are platform-level concepts:

- evaluations
- scheduling
- duty hours / work-hour violations
- case logs
- notifications
- open forms
- bulk imports
- reporting
- access / permissions
- integrations

Pick the ones most directly touched by the tickets in this release. Do not name every module in the platform.

## Length

The message should comfortably fit in a single Slack post. Practical cap: ~3500 characters of body text. If the release has more than ~8 items total, the message can stretch — Slack tolerates up to roughly 40,000 characters per message — but each per-block summary must stay at 2–4 sentences, no exceptions. If you find yourself writing a fifth sentence, you are drifting into the dev-notes audience, not the dream-team audience.

## When upstream is empty

If the input file has zero usable blocks (every block dropped, or the upstream collected nothing), return exactly:

```
NO_INTERNAL_NOTES — nothing customer-visible shipped this deploy
```

The orchestrator will detect this and skip the Slack post.

## Failure handling

If a per-block field is malformed (missing `IDENTIFIER`, missing `TITLE`, missing `SUMMARY`, or `CATEGORY` is not one of the allowed values), drop that block from the message and append a single line at the very bottom of the message:

```
_Dropped {N} malformed upstream block(s) — orchestrator should re-run the analyzer for: {LIST_OF_IDENTIFIERS_IF_KNOWN}_
```

Never silently invent a category, title, or developer.

## What this skill does not do

- Does not post to Slack. That is `scripts/slack_upload.py` invoked by `/internal-notes`.
- Does not call the IP guard. The internal post is meant to carry internal vocabulary; the guard would refuse it.
- Does not render a PDF. Internal notes are Slack text only.
- Does not look up Slack user IDs. The analyzer's job is to resolve `DEVELOPER_SLACK_ID` via the Slack MCP before invoking this skill; if it is empty, this skill falls back to the plain developer name.
