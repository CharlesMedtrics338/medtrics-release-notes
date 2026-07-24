# medtrics-release-notes

Release communications for Medtrics — both **customer-facing** (executive voice for institutional administrators) and **internal** (the `#dream-team` post for the dev team). One command after every Monday deploy delivers the audience-appropriate announcements with PDFs to clients, and the internal-team digest to `#dream-team`.

## What it delivers

- **`/release-slack`** runs the customer-facing pipeline: pulls upstream task and code-change data → generates per-ticket exec-voice summaries via parallel analyzer agents → synthesizes them into one cohesive customer-facing narrative via the bundled **storyteller** skill → validates that narrative through the bundled **ip-guard** skill (no internal-system names, code artifacts, ticket IDs, file paths, or architecture-mechanism vocabulary) → renders both PDFs → composes the Slack message → previews to you → posts on confirmation.
- **`/internal-notes`** runs the internal-team pipeline: same source data, different shape and audience. Keeps ticket identifiers, developer Slack `@`-mentions, client institution names, and direct Optimus URLs. Composes a Slack-mrkdwn post via the bundled **internal-storyteller** skill → previews to you → posts to `#dream-team` on confirmation. No PDF, no IP guard (internal vocabulary is the whole point).
- The remaining commands (`/notes`, `/deploy-notes`, `/integration-notes`) are building blocks that produce markdown files only.

## Commands

| Command | What it does | When to run it |
|---|---|---|
| `/release-slack` | End-to-end customer Monday command. Message + 2 PDFs into the channel from `SLACK_CHANNEL_RELEASE`. | After every production deploy, **for clients**. |
| `/internal-notes` | End-to-end internal command. Slack message into `#dream-team` (`SLACK_CHANNEL_INTERNAL`), ticket IDs + dev @-mentions + client tags intact. | After every production deploy, **for the dev team**. |
| `/notes` | All 3 note types (dev / deploy / integration) as markdown files in parallel. | Paper-trail backup or when you also need the internal `/dev-notes`. |
| `/deploy-notes` | Client-facing release notes markdown only. | Non-Slack delivery (paste into email, help center). |
| `/integration-notes` | Integration-partner markdown only. | Separate partner channel. |

## Bundled skills

The plugin ships with six skills, all packaged inside the plugin so installing it gives you the full pipeline in one shot:

| Skill | Purpose |
|---|---|
| `medtrics-release-notes:storyteller` | Transforms per-ticket release summaries into a cohesive executive-voice narrative for institutional administrators (DIOs, deans, IT directors). Decides *what to say*. Never names internal systems, code artifacts, or implementation mechanisms. Customer-facing. |
| `medtrics-release-notes:internal-storyteller` | **New in 0.7.0.** Composes the internal `#dream-team` Slack post from per-ticket analyzer blocks. Keeps ticket IDs, developer `<@SLACK_ID>` mentions, client institution tags (`KFSHRC`, `MSUCVM`, `ADTALEM`), and Optimus URLs. Sections are `*Enhancements & New Features*` and `*Bug Fixes*`. Slack mrkdwn, message-only — no PDF, no IP guard. |
| `medtrics-release-notes:copy-audit` | Sentence-level polish pass that runs between storyteller and ip-guard. Strips AI-sounding language, bloated verbs (`serves as`, `boasts a`, `helps to`), dead openings (`Furthermore`, `Moreover`), negative-parallelism patterns (`Not X. Y.`), decorative metaphor verbs (`mapped`, `surfaced`, `unpacked`), and engagement bait. Customer-facing only. |
| `medtrics-release-notes:ip-guard` | Deterministic safety net that scans customer-facing output for internal-system names, code-artifact jargon, ticket / MR identifiers, file paths, and architecture mechanism vocabulary. Blocks delivery on violation. Iterates with the storyteller + copy-audit up to 3 times to remediate. **Not** run against the internal-storyteller output — internal vocabulary is expected there. |
| `medtrics-release-notes:release-brief-pdf` | Converts the polished release-notes markdown into a branded customer-facing PDF (Lexend/Helvetica, navy `#1F3064`, orange `#ED601A`, paper `#FBF9F3`). Originally authored by `santhosh@medtricslab.com`. |
| `medtrics-release-notes:integration-brief-pdf` | Converts an integration-notes markdown into a branded technical integration-impact PDF. Same brand tokens; preserves BREAKING / NON-BREAKING / DEPRECATION / SKIP labels. Integration audience is technical — this output bypasses both copy-audit and ip-guard. |

The storyteller, copy-audit, ip-guard, and PDF skills are invoked automatically by `/release-slack`. Each can also be invoked standalone if you want a partial output without the rest of the pipeline.

## Engineering commands moved out

For code review, plan, rebase, MR-feedback, bug-report, branch context, and the internal dev-notes changelog, install the companion plugin **`medtrics-dev-workflow`**.

## Host-repo requirements

The plugin shells out to `git` and reads Optimus + GitLab over HTTP. It only works inside a Medtrics monorepo checkout with the conventions in the legacy CLAUDE.md (`src/apps/...`, `develop` base branch, ticket id regex `M1-\d+ | GEN-\d+ | DEV-\d+ | RD-\d+ | do-\d+`).

## .env keys (in the host-repo root, not the plugin folder)

| Key | Required for | Notes |
|---|---|---|
| `OPTIMUS_API_KEY` | all commands | |
| `GITLAB_TOKEN` | all commands | |
| `GITLAB_PROJECT_ID` | all commands | |
| `GITLAB_URL` | optional | defaults to `https://gitlab.com` |
| `SLACK_CHANNEL_RELEASE` | `/release-slack` only | channel id (`C0123ABC`) preferred, or `#channel-name` |
| `SLACK_CHANNEL_INTERNAL` | `/internal-notes` only | channel id `C1BCUHXT9` (= `#dream-team`) |
| `SLACK_BOT_TOKEN` | `/release-slack` and `/internal-notes` | `xoxb-...` bot token. **NOT** a user token (`xoxp-`). Same token works for both posts; the bot must be invited to both channels. |

## Slack bot setup (one-time, ~10 minutes)

`/release-slack` does NOT use the Slack MCP. It talks to the Slack Web API directly using a bot token in your `.env`, the same way the plugin uses `GITLAB_TOKEN` to talk to GitLab without a GitLab MCP.

1. Go to https://api.slack.com/apps and click **Create New App** → **From scratch**.
2. Name it something like `Medtrics Release Bot` and pick your Medtrics workspace.
3. Under **OAuth & Permissions** → **Scopes** → **Bot Token Scopes**, add:
   - `chat:write` — to post the announcement message.
   - `files:write` — to upload the two PDFs.
   - `channels:read` — to resolve `#channel-name` to a channel id (skip if you'll use the channel id directly).
4. Click **Install to Workspace** at the top of OAuth & Permissions, approve the install.
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`).
6. Invite the bot to **both** channels:
   - In your release channel (for `/release-slack`): `/invite @Medtrics Release Bot`.
   - In `#dream-team` (for `/internal-notes`): `/invite @Medtrics Release Bot`.
7. Add to your host-repo `.env`:
   ~~~
   SLACK_BOT_TOKEN=xoxb-12345...
   SLACK_CHANNEL_RELEASE=C0123ABC       # customer release channel, preferred over a #name
   SLACK_CHANNEL_INTERNAL=C1BCUHXT9     # #dream-team (internal-notes destination)
   ~~~

Prefer the channel id over the name: ids never change, names can be renamed. Right-click the channel in Slack → View channel details → channel id at the bottom.

## Typical Monday workflow

~~~
$ cd ~/code/medtrics
$ git checkout develop && git pull
$ # production deploy completes
$ # open Cowork
/release-slack
~~~

`/release-slack` then:
1. Pulls all deploy-ready tickets and their code-change data in parallel.
2. Runs the per-ticket analyzer agents under the exec-voice rubric — each ticket becomes one user-outcome sentence with a domain tag, no jargon, no IDs.
3. Invokes the **storyteller** skill to synthesize all per-ticket outcomes into one cohesive narrative grouped by domain area.
4. Invokes the **copy-audit** skill to polish the prose — strips AI-sounding language, bloated verbs, dead openings, negative-parallelism patterns, decorative metaphor verbs, and engagement bait.
5. Invokes the **ip-guard** skill to validate the polished narrative — blocks delivery on violation, iterates the storyteller + copy-audit loop up to 3 times to remediate, stops cleanly if still unresolved.
6. Generates the integration-notes markdown (technical audience, unchanged, exempt from copy-audit and ip-guard).
7. Invokes `release-brief-pdf` and `integration-brief-pdf` to render branded PDFs.
8. Composes a single Slack mrkdwn message.
9. Shows you the preview — message + the two PDF paths.
10. On your `y`, posts the message to `SLACK_CHANNEL_RELEASE` and uploads both PDFs as replies in the same thread.

For a specific ticket set:
~~~
/release-slack tickets M1-583,GEN-128592,M1-848
~~~

Dry-run (see what would post without posting):
~~~
/release-slack dry-run
~~~

## Internal `#dream-team` workflow

After (or alongside) the customer post, run the internal digest:

~~~
/internal-notes                                  # same scope as /release-slack
/internal-notes tickets M1-986,M1-1039,M1-1118   # specific tickets
/internal-notes dry-run                          # preview discovery
~~~

`/internal-notes` then:

1. Pulls the same deploy-ready tickets and code-change data — plus Optimus assignee and GitLab MR author info.
2. Resolves each developer's Slack user ID via `slack_search_users` (best-effort; falls back to plain name).
3. Extracts client tags (`KFSHRC`, `MSUCVM`, `ADTALEM`, etc.) from the ticket description; defaults to `TBC` for platform-wide work.
4. Runs the per-ticket analyzer under the **internal** rubric — keeps ticket IDs, mechanism specifics, and client motivation.
5. Invokes the **internal-storyteller** skill to compose a Slack mrkdwn post grouped into `*Enhancements & New Features*` and `*Bug Fixes*`.
6. Shows you the preview.
7. On your `y`, posts the message to `SLACK_CHANNEL_INTERNAL` (`#dream-team` / `C1BCUHXT9`). No PDF, no thread — single message.

The internal post deliberately bypasses the IP guard and the copy-audit skill. Both are configured for customer-facing copy and would refuse the message.

## Output paths

Everything lands under `.claude/outputs/notes/` in your host repo:

~~~
.claude/outputs/notes/
├── deploy/
│   ├── release-notes-2026-05-19.md
│   └── release-notes-2026-05-19.pdf
├── integration/
│   ├── integration-notes-2026-05-19.md
│   └── integration-notes-2026-05-19.pdf
├── release-slack/
│   └── release-slack-2026-05-19.md     ← copy of customer post + ts + permalink
└── internal/
    └── internal-notes-2026-05-19.md    ← copy of #dream-team post + ts + permalink
~~~

## Install (Cowork)

1. Cowork → Settings → Plugins → Upload plugin.
2. Select `medtrics-release-notes.plugin`.
3. Add the `.env` keys above to your host-repo root.
4. Complete the Slack bot setup above.

## Version history

Detailed release history lives in [`CHANGELOG.md`](./CHANGELOG.md). Current version: **0.7.0**.

## Repository layout

```
medtrics-release-notes/
├── .claude-plugin/plugin.json
├── commands/             # /release-slack, /deploy-notes, etc.
├── skills/               # storyteller, copy-audit, ip-guard, release-brief-pdf, integration-brief-pdf
├── scripts/              # gather, prompts, slack upload, ip guard, build
├── tests/                # pytest suite (not shipped in .plugin)
├── CHANGELOG.md
├── CONTRIBUTING.md       # contributor workflow (not shipped in .plugin)
├── LICENSE
├── README.md
├── requirements.txt      # stdlib-only at runtime
└── requirements-dev.txt  # pytest, ruff, mypy
```

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the development flow, test instructions, and release process.
