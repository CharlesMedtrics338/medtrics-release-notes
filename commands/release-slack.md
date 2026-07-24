---
description: Post a combined deploy + integration release update (message + both branded PDFs) to a configured Slack channel after Monday deploys
---

# Release Slack Announcement

Generate a single client-facing release package — a Slack message plus the matching deploy and integration PDFs — and deliver it to a configured channel after the user explicitly approves. Designed to be the once-per-deploy command that fires after a Monday production push.

This command never posts to Slack without explicit user confirmation in the same session.

## Usage

~~~
/release-slack                                  # status mode (default): all current deploy-ready tickets
/release-slack tickets M1-583,GEN-128592        # explicit ticket list (paste from Optimus Plan Deploy view)
/release-slack mr 6567                          # summarize a single GitLab MR
/release-slack dry-run                          # print what would be gathered/posted, then exit without posting
~~~

You may combine the mode with `dry-run`, e.g. `/release-slack tickets M1-583 dry-run`.

## Pipeline overview

~~~
1. validate .env keys
2. gather data in parallel (deploy + integration variants)
3. generate the two markdown notes files
     - deploy: exec-voice narrative via the storyteller skill (writes draft to /tmp)
     - integration: technical change notes (unchanged audience: integration partners)
4. polish the deploy draft via the copy-audit skill
     - strips AI-sounding language, bloated verbs, dead openings, negative-parallelism
       patterns, decorative metaphor verbs, and engagement bait
     - writes the polished file into .claude/outputs/notes/deploy/
5. run the ip-guard against the deploy markdown
     - on PASS: proceed
     - on FAIL: iterate storyteller + copy-audit rewrites up to 3 times,
       then stop if unresolved
     - integration-notes is exempt — that audience needs technical detail
6. invoke the bundled PDF skills to convert each markdown → PDF
7. compose the Slack mrkdwn message (one combined post)
8. preview to the user — message + the two PDF paths
9. on user confirm: post message + upload both PDFs to the same thread via slack_upload.py
~~~

## Output

- Slack post to the channel resolved from `SLACK_CHANNEL_RELEASE`. Both PDFs are uploaded as replies in the same thread. Posted only after the user confirms.
- Markdown sources written to:
  - `.claude/outputs/notes/deploy/release-notes-<YYYY-MM-DD>.md`
  - `.claude/outputs/notes/integration/integration-notes-<YYYY-MM-DD>.md`
- Branded PDFs written next to the markdowns:
  - `.claude/outputs/notes/deploy/release-notes-<YYYY-MM-DD>.pdf`
  - `.claude/outputs/notes/integration/integration-notes-<YYYY-MM-DD>.pdf`
- A copy of the posted Slack message text written to `.claude/outputs/notes/release-slack/release-slack-<YYYY-MM-DD>.md` with the channel, permalink, and ts.

Compute the date via `date +%Y-%m-%d` in Bash — do NOT hardcode or guess.

## Required .env keys

| Key | Purpose | Required |
|---|---|---|
| `OPTIMUS_API_KEY` | gather Optimus tickets | Yes |
| `GITLAB_TOKEN` | gather GitLab MR diffs | Yes |
| `GITLAB_PROJECT_ID` | GitLab project to query | Yes |
| `GITLAB_URL` | GitLab base URL | optional, defaults to `https://gitlab.com` |
| `SLACK_CHANNEL_RELEASE` | channel id (`C0123ABC`) or `#channel-name` | Yes |
| `SLACK_BOT_TOKEN` | `xoxb-...` token from a Slack app with `chat:write` + `files:write` scopes | Yes |

If any of these is missing, abort early with a clear "Missing required env keys: [...]" message — do NOT proceed to any data gathering, file generation, or Slack call.

## Flow

### Step 1: validate environment

Read `.env` from the current working directory. Verify the six required keys above are present. If any are missing, list them and stop.

### Step 2: gather data in parallel

For `status` mode (default):

~~~
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py status --output /tmp/release_slack_deploy_data.json --include-description &
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py status --output /tmp/release_slack_integration_data.json --include-description --filter-integration &
wait
~~~

For `tickets <id1,id2,...>`:

~~~
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py tickets <id1,id2,...> --output /tmp/release_slack_deploy_data.json --include-description &
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py tickets <id1,id2,...> --output /tmp/release_slack_integration_data.json --include-description --filter-integration &
wait
~~~

For `mr <iid>`:

~~~
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py mr <iid> --output /tmp/release_slack_deploy_data.json --include-description &
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py mr <iid> --output /tmp/release_slack_integration_data.json --include-description --filter-integration &
wait
~~~

For `dry-run`: append `--dry-run` to both calls, print the discovered issues+MRs, and exit before any file generation or Slack call.

### Step 3: generate the two markdown notes files

Follow the orchestration described in `/deploy-notes` and `/integration-notes` for the gathered JSON files from step 2. The two paths diverge here:

- **Deploy draft — exec voice.** Run the per-ticket analyzer agents with the exec-voice rubric defined in `commands/deploy-notes.md`, then invoke the bundled `medtrics-release-notes:storyteller` skill on the collected per-ticket blocks. The storyteller writes its draft to `/tmp/release_notes_draft.md` — not yet to the final output path.
- **Integration markdown — technical, unchanged.** Run the integration-notes orchestration as before. This audience (integration partners) needs endpoint paths, field names, and migration specifics. Write directly to `.claude/outputs/notes/integration/integration-notes-<YYYY-MM-DD>.md`.

Create the directories with `mkdir -p` if they don't exist.

If both markdowns end up empty (no in-scope tickets), print `No deploy-ready tickets found. Nothing to post.` and stop before the copy-audit, IP guard, or PDF steps.

### Step 4: polish the deploy draft via the copy-audit skill

Invoke `medtrics-release-notes:copy-audit` against `/tmp/release_notes_draft.md`. The skill applies the team's writing rules — strips AI-sounding language, bloated verbs (`serves as`, `boasts a`, `helps to`), dead openings (`Furthermore`, `Moreover`), negative-parallelism patterns (`Not X. Y.`), decorative metaphor verbs (`mapped`, `surfaced`, `unpacked`), and engagement bait (`Let that sink in`).

The polished output lands at `.claude/outputs/notes/deploy/release-notes-<YYYY-MM-DD>.md`. This is the file the IP guard scans and the PDF skill renders.

If copy-audit changes meaning rather than just sentence-level form, prefer the storyteller's wording for that sentence and rerun copy-audit on the rest.

### Step 5: run the IP guard against the deploy markdown

The deploy markdown is the only customer-facing prose in this pipeline. Before any PDF is rendered or any Slack call is made, the markdown must pass the IP guard.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ip_guard.py \
    --input .claude/outputs/notes/deploy/release-notes-<YYYY-MM-DD>.md \
    --json-out /tmp/ip_guard_result.json
guard_exit=$?
```

Behavior by exit code:

| Exit | Meaning | Action |
|---|---|---|
| `0` | PASS | Proceed to Step 5. |
| `2` | FAIL — blocking violation(s) | Read `/tmp/ip_guard_result.json`, pass the `violations` array back to the storyteller for rewrite. Re-run the guard. Iterate up to 3 times. If still failing, stop, print residual violations with line offsets, and exit without rendering PDFs or calling Slack. |
| `1` | Configuration error | Surface stderr, stop. |

The integration markdown is **not** sent through the guard. Integration partners reasonably consume technical detail.

### Step 6: invoke the bundled PDF skills

Invoke each bundled skill via the Skill tool, passing the path to the corresponding markdown file. Each skill produces a PDF next to the source markdown.

1. Invoke `medtrics-release-notes:release-brief-pdf` with the deploy markdown path. Expected output: `.claude/outputs/notes/deploy/release-notes-<YYYY-MM-DD>.pdf`.
2. Invoke `medtrics-release-notes:integration-brief-pdf` with the integration markdown path. Expected output: `.claude/outputs/notes/integration/integration-notes-<YYYY-MM-DD>.pdf`.

These skills handle their own HTML/CSS templates, brand tokens (Lexend/Helvetica, navy `#1F3064`, orange `#ED601A`, paper `#FBF9F3`, ink `#2D3448`), and WeasyPrint rendering. Do NOT pre-supply HTML or attempt to render the PDF yourself — let each skill do its job.

If either skill returns an error or fails to produce the expected PDF, surface the error and stop before composing the Slack message.

### Step 7: compose the Slack mrkdwn message

Compose a single combined message in Slack mrkdwn flavor. Rules:

- Bold: `*text*` (single asterisks), not `**text**`
- Italic: `_text_`
- Code: backticks
- Lists: `•` for bullets
- No tables, no images, no headers (Slack has none)
- Cap roughly 1500 chars

Structure:

~~~
:rocket: *Medtrics Release — <Weekday>, <Month> <D>, <YYYY>*

We deployed today. Both the customer release notes and integration impact PDFs are attached in this thread.

*What's new for you*
• <one-line plain-English benefit> — _<TICKET-ID>_
• ...

*Integration changes*
• <one-line API/data change, with backwards-compat note if relevant> — _<TICKET-ID>_
• ...

Full details in the attached PDFs. Questions? Reply in thread.
~~~

Rules for the bullet lines:
- Each line one sentence, no jargon. Lead with the user benefit verb.
- Ticket id at the end in italics.
- Omit a section heading entirely if it has no items.
- The two PDFs carry the full detail — keep the message scannable. 3–6 bullets per section is the sweet spot.

Write the composed message to `/tmp/release_slack_message.txt` so the upload script can read it byte-for-byte.

### Step 8: preview to user

Print the composed Slack message inside a fenced block AND list the two PDFs with their absolute paths and file sizes. Then ask:

~~~
Ready to post to <#CHANNEL>?
  Message will go to: <channel display>
  PDFs that will upload to the thread:
    - release-notes-<YYYY-MM-DD>.pdf  (X KB)
    - integration-notes-<YYYY-MM-DD>.pdf  (Y KB)

  [y] post message and upload both PDFs
  [n] cancel (no Slack action taken; markdowns + PDFs already saved locally)
  [e] let me edit the draft message first
~~~

If user picks `e`, accept their edits, re-show the preview, loop until `y` or `n`.

### Step 9: post + upload (only if user said `y`)

Run the bundled upload script:

~~~
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_upload.py \
    --channel "$SLACK_CHANNEL_RELEASE" \
    --message-file /tmp/release_slack_message.txt \
    --pdf .claude/outputs/notes/deploy/release-notes-<YYYY-MM-DD>.pdf \
    --title "Release Notes — <YYYY-MM-DD>" \
    --pdf .claude/outputs/notes/integration/integration-notes-<YYYY-MM-DD>.pdf \
    --title "Integration Impact — <YYYY-MM-DD>"
~~~

The script:
1. Loads `SLACK_BOT_TOKEN` from `.env` (or process env).
2. Resolves the channel (id pass-through, or name → id via `conversations.list`).
3. Posts the message via `chat.postMessage`.
4. Uploads each PDF as a thread reply via `files.getUploadURLExternal` + `files.completeUploadExternal`.
5. Prints a JSON line `---SLACK_UPLOAD_RESULT---` followed by `{"ok": true, "channel": "...", "ts": "...", "uploaded": [...]}` on success.

Parse the JSON result. If `ok=true`, save a copy of the message text to `.claude/outputs/notes/release-slack/release-slack-<YYYY-MM-DD>.md` with a header showing the channel, ts, and PDF filenames. Print a one-line confirmation: `Posted to <#channel>. Thread ts=<ts>. PDFs uploaded: release-notes-<YYYY-MM-DD>.pdf, integration-notes-<YYYY-MM-DD>.pdf`.

If the script exits non-zero, surface its stderr verbatim and do NOT retry automatically.

## Failure modes and behavior

| Condition | Behavior |
|---|---|
| Missing required env keys | Abort before any tool call, list missing keys |
| Gather returns zero tickets | Print "Nothing to post" and stop before PDFs/Slack |
| Storyteller produces empty output | Print "No customer-visible changes in this release" and stop |
| `ip_guard.py` exits 2 after 3 storyteller rewrites | Print residual violations with line offsets, do not render PDFs, do not call Slack. The user can hand-edit the markdown and rerun the guard, then re-enter the pipeline at the PDF step. |
| Either PDF skill fails | Surface the skill error, do not proceed to Slack |
| Channel name resolves to nothing | Print error, do not post |
| `slack_upload.py` returns non-zero | Print stderr, do not retry |
| User declines at preview | No Slack call; markdowns + PDFs remain on disk for manual use |

## Things this command does NOT do

- Does not run `/dev-notes` (internal-only changelog).
- Does not modify any Optimus tickets or GitLab MRs.
- Does not write to `.env` or to the plugin directory.
- Does not retry Slack failures.
- Does not auto-schedule itself. A scheduled task that invokes `/release-slack` will still stop at the preview step and wait for confirmation.

## Coding Standards

- **Data gathering is handled by the Python scripts.** Do NOT run individual git commands or curl for upstream data.
- **Synthesis is handled by the `storyteller` skill.** Do NOT compose the customer-facing narrative directly in the command body — invoke the skill so the voice and audience contract stay in one place.
- **Validation is handled by `ip_guard.py`.** Do NOT skip the guard. The guard is the deterministic safety net that keeps internal-system names, code artifacts, ticket identifiers, and architecture mechanism vocabulary out of customer-facing copy.
- **PDF rendering is handled by the bundled skills.** Do NOT inline HTML/CSS or call WeasyPrint directly.
- **Slack delivery is handled by `slack_upload.py`.** Do NOT use the Slack MCP — the bundled script handles message + file uploads.
- **Output filenames use today's date computed via `date +%Y-%m-%d` in Bash** — never hardcoded or guessed.
- **Channel resolution is exact-match only.** If `SLACK_CHANNEL_RELEASE` is a name that matches multiple channels, the script will error — surface it and stop.
