# Changelog

All notable changes to `medtrics-release-notes` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.0] - 2026-07-14

### Changed
- **Per-ticket customer-facing format.** The `/deploy-notes` release brief now
  renders one entry per ticket instead of grouping changes by domain area. Each
  entry is headed by the ticket's **identifier + verbatim Optimus title**
  (`### [M1-1054] CRITICAL BUG: Security > SQL Injection & SSRF ...`), followed
  by the exec-voice bold lede and description. Every **Key takeaways** bullet
  now ends with its `[TICKET-ID]` reference chip. Rationale: clients routinely
  reference these identifiers with support, so the customer-facing brief must
  carry them.
- **`skills/storyteller`** rewritten: output structure replaced
  `## What's improved for your programs` / `## What you should know` with a
  single `## In this release` section of per-ticket `### [ID] Title` blocks.
  Awareness items (default-behavior / permission changes) carry a `[!HEADSUP]`
  marker and are ordered last. Titles are reproduced **verbatim by default**;
  cleaning is available only on explicit operator request.
- **`skills/release-brief-pdf`** layout updated: each entry renders as a card
  with a filled navy identifier chip + verbatim title header; `[!HEADSUP]`
  entries get an orange left rule, an orange "Heads up" tag, and an orange chip.
  Key-takeaways `[ID]` chips render as navy monospace tags.
- **`scripts/ip_guard.py`** relaxed: ticket identifiers (`M1-NNN`, `GEN-NNNNNN`,
  `DEV-NNN`, `RD-NNN`, `do-NNN`) are **no longer blocked**, and any markdown
  heading line containing a `[TICKET-ID]` bracket is exempt from scanning so the
  verbatim title header is preserved. MR references, internal system names, code
  artifacts, file paths, and mechanism vocabulary remain blocked in the
  narrative prose. `skills/ip-guard/SKILL.md` updated to match.

### Notes
- This is a customer-visible policy change: verbatim titles mean internal-
  flavored wording (`CRITICAL BUG:`, `FEATURE:`, `Redo M1-xxxx`, client codes,
  and security classes) appears in the client-facing brief by design. Use the
  explicit cleaned-titles override when a specific title should be softened.

## [0.7.0] - 2026-05-22

### Added
- **`/internal-notes` command.** New on-demand workflow for the internal
  Medtrics dev team Slack digest. Pulls the same Optimus tickets + GitLab MRs
  as `/deploy-notes`, but keeps everything the customer-facing brief strips:
  ticket identifiers, developer Slack `@`-mentions, client institution names
  (e.g., `KFSHRC`, `MSUCVM`, `ADTALEM`), and direct Optimus URLs. Previews the
  composed message in chat; posts to `#dream-team` (channel id `C1BCUHXT9`)
  only after explicit user approval.
- **`skills/internal-storyteller`.** Composes the Slack-mrkdwn message from
  the per-ticket analyzer blocks. Sections are `*Enhancements & New Features*`
  and `*Bug Fixes*`; each item carries Ticket, Developer (`<@SLACK_ID>` when
  resolvable, plain name otherwise), 2–4-sentence Summary, URL, and Clients
  (or `TBC` with a one-line scope description for platform-wide work).
- Slack developer-ID resolution via `slack_search_users` (best-effort; falls
  back to plain name when no match).
- `SLACK_CHANNEL_INTERNAL` env key (default `#dream-team` / `C1BCUHXT9`).

### Changed
- **`scripts/gather_notes_data_optimus.py`** now emits `assignee_name`,
  `assignee_email`, `assignee_id`, and `task_type` on each issue, and
  `author_name` / `author_username` on each MR. Backward-compatible — fields
  are empty strings when upstream omits them. Required by `/internal-notes`;
  ignored by `/deploy-notes`, `/integration-notes`, and `/release-slack`.
- **`scripts/prepare_note_prompts.py`** extends the per-prompt header to
  optionally include Assignee, Assignee Email, Assignee Slack ID, Clients,
  and MR Author(s) when those fields are present on the issue. The
  customer-facing analyzer prompts ignore them; the internal analyzer
  consumes them.

### Notes
- `/internal-notes` deliberately does **not** run through the IP guard or
  `copy-audit` skill. Both are configured for customer-facing copy and would
  refuse internal vocabulary.
- The internal post is Slack-only — no PDF.

## [0.6.0] - 2026-05-22

### Changed
- **Customer release brief is now scannable in 15 seconds.** The storyteller
  prepends a `## Key takeaways` section (3–5 one-line bullets, with a
  `Heads up:` prefix for any awareness item) and requires every domain block
  under `## What's improved for your programs` and every item under
  `## What you should know` to open with a bold one-line takeaway. Length
  budget stays at 350–650 words.
- **`release-brief-pdf` adds a visual hierarchy spec.** A Key-takeaways card
  with a hairline border sits at the top of page 1 above the Summary, and the
  `What you should know` section is marked with a 3 pt orange left rule.
  Heading sizes, weights, and spacing are now in a single table so the PDF
  renders consistently across releases.
- **`integration-brief-pdf` gains an at-a-glance card.** A counts strip
  (BREAKING / DEPRECATION / NON-BREAKING) and up to three "Top actions for
  integrators" sit at the top of page 1. Counts are derived strictly from the
  source Summary/Totals; top actions are pulled verbatim from the unchecked
  Migration Checklist items.
- `commands/deploy-notes.md` and `commands/integration-notes.md` updated to
  reflect the new output structures.

## [0.5.2] - 2026-05-22

### Added
- `CHANGELOG.md` (this file). Version history previously lived at the bottom of
  the README; it now has a proper home.
- `requirements.txt` declaring the runtime and dev dependency surface
  (scripts are currently stdlib-only; `reportlab` is bundled with the
  `release-brief-pdf` skill's renderer).
- `LICENSE` (Proprietary — internal use at Medtrics).
- `CONTRIBUTING.md` describing the contribution flow.
- `tests/` directory with a smoke test for `ip_guard.py` and a README explaining
  how to run the suite.
- `scripts/build_plugin.py` — versioned bundler that reads
  `.claude-plugin/plugin.json`, excludes dev-side files, and produces the
  shippable `.plugin` artifact. Includes a post-build self-check that refuses
  to ship a bundle missing `.claude-plugin/plugin.json` or its explicit
  directory entry, or whose manifest description exceeds 256 chars.
- Executable bit set on all `scripts/*.py` files.

### Changed
- README's "Version history" section trimmed to a pointer at `CHANGELOG.md`.

### Fixed
- The `.plugin` zip now writes explicit directory entries (`.claude-plugin/`,
  `commands/`, `skills/`, `scripts/`, and each nested skill directory).
  Earlier 0.5.x builds with file-only entries were rejected by the Cowork
  plugin loader with *"Zip must contain a .claude-plugin/plugin.json file"*
  even though the file was present — the loader requires the directory entry.
  Fixed in `scripts/build_plugin.py`; v0.4.0 used the same pattern, so this
  restores parity.

## [0.5.1] - 2026-05-22

### Added
- Bundled `copy-audit` skill. Previously installable as a separate skill, now
  ships inside the plugin so installing the `.plugin` file delivers the full
  pipeline in one shot.
- New pipeline step between `storyteller` and `ip-guard`. `copy-audit` polishes
  the storyteller's draft sentence-by-sentence — strips AI-sounding language,
  bloated verbs (`serves as`, `boasts a`, `helps to`), dead openings
  (`Furthermore`, `Moreover`), negative-parallelism patterns (`Not X. Y.`),
  decorative metaphor verbs (`mapped`, `surfaced`, `unpacked`), and engagement
  bait.

### Changed
- Storyteller now writes its draft to `/tmp/release_notes_draft.md`. The
  copy-audit pass writes the polished file to the final
  `.claude/outputs/notes/deploy/` path. This keeps the unaudited draft out of
  the deliverable directory.
- Storyteller title format updated from `# Medtrics Release — {Weekday}, ...`
  to `# Medtrics Release: {Weekday}, ...` — the em-dash violated `copy-audit`'s
  punctuation rules.
- Failure-loop now iterates the storyteller → copy-audit → ip-guard chain up to
  3 times before stopping.
- `commands/release-slack.md` step numbering shifted (Step 4 = copy-audit,
  Step 5 = ip-guard, …) and the failure-mode table updated.

### Fixed
- Plugin validation failure on install caused by overlong YAML/JSON
  `description` fields. `plugin.json` description trimmed from 577 chars to 225;
  `storyteller` SKILL.md description from 379 to 226; `ip-guard` SKILL.md from
  283 to 231. Pre-existing skill descriptions (`release-brief-pdf` 277,
  `integration-brief-pdf` 331) shipped successfully in 0.4.0 so they were left
  alone.

## [0.5.0] - 2026-05-22

### Added
- New `storyteller` skill. Transforms per-ticket release summaries into a
  cohesive executive-voice narrative aimed at institutional administrators
  (DIOs, deans, IT directors, program directors). Never names internal
  systems, code artifacts, or implementation mechanisms.
- New `ip-guard` skill plus `scripts/ip_guard.py`. Deterministic regex scanner
  that blocks customer-facing release notes from leaking internal system names
  (issue tracker, source-control host, observability vendors, framework names,
  language runtimes, datastores, cloud providers), code artifact jargon
  (`serializer`, `viewset`, `model`, `migration`, `endpoint`, `queryset`,
  `schema`, etc.), ticket / MR identifiers (`M1-NNN`, `!1234`), file paths,
  and architecture mechanism vocabulary (queue, worker, cache, cron, webhook,
  race condition).
- New Step 4 in `commands/release-slack.md` that runs `ip_guard.py` against the
  customer-facing markdown before any PDF render or Slack call. On block, the
  storyteller iterates up to 3 times to remediate.

### Changed
- `commands/deploy-notes.md` analyzer rubric rewritten for exec voice. Per-ticket
  agents now produce one user-outcome sentence per ticket with a domain tag and
  a change kind, rather than the previous category / identifier / title / summary
  block.
- README expanded with the new bundled-skills table, updated pipeline narrative,
  and an explanation of the IP guard's contract.

### Fixed
- None.

## [0.4.0] - 2026-05-20

### Added
- Bundled `release-brief-pdf` and `integration-brief-pdf` skills (originally by
  `santhosh@medtricslab.com`). Installing the plugin now delivers PDF rendering
  inline rather than requiring a separate skill install.
- `scripts/slack_upload.py` for direct Slack Web API delivery using the modern
  `files.getUploadURLExternal` + `files.completeUploadExternal` flow.
- `/release-slack` now generates branded PDFs and uploads them to the message
  thread automatically.
- New required env key: `SLACK_BOT_TOKEN` (Slack bot OAuth token with
  `chat:write` + `files:write` scopes).

### Changed
- `/release-slack` no longer uses the Slack MCP. It now talks to the Slack Web
  API directly via the bundled upload script.

### Fixed
- None.

## [0.3.0] - 2026-05-01

### Changed
- Trimmed plugin to four client-facing commands (`/notes`, `/deploy-notes`,
  `/integration-notes`, `/release-slack`). Engineering commands moved to the
  companion plugin `medtrics-dev-workflow`.

### Removed
- Internal-team commands (code review, plan, rebase, MR-feedback, bug-report,
  branch-context, dev-notes changelog) extracted to `medtrics-dev-workflow`.

## [0.2.0] - 2026-04-15

### Added
- `/release-slack` command for message-only Slack delivery via the Slack MCP.

## [0.1.0] - 2026-03-01

### Added
- Initial release: four note-generation commands (`/dev-notes`,
  `/deploy-notes`, `/integration-notes`, `/notes`).
- `scripts/gather_notes_data_optimus.py` and `scripts/prepare_note_prompts.py`.

[Unreleased]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.6.0...HEAD
[0.6.0]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.5.2...v0.6.0
[0.5.2]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.5.1...v0.5.2
[0.5.1]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.5.0...v0.5.1
[0.5.0]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.4.0...v0.5.0
[0.4.0]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.3.0...v0.4.0
[0.3.0]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.2.0...v0.3.0
[0.2.0]: https://gitlab.com/medtrics/medtrics-release-notes/-/compare/v0.1.0...v0.2.0
[0.1.0]: https://gitlab.com/medtrics/medtrics-release-notes/-/releases/v0.1.0
