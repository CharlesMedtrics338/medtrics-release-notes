---
description: Internal-team release notes for the #dream-team Slack channel — ticket IDs, developer @-mentions, and client attribution included. Distinct from /deploy-notes (customer-facing) and /integration-notes (integration partners).
---

# Internal Release Notes (#dream-team)

Generate the internal release post for the Medtrics dev team and deliver it to `#dream-team` after the user explicitly approves. This is the **internal twin** of `/deploy-notes`: same source data (Optimus tickets + GitLab MRs), different audience and different shape. Internal notes keep the things the customer-facing brief deliberately strips out — ticket identifiers, developer Slack `@` mentions, client institution names, and direct Optimus URLs.

This command never posts to Slack without explicit user confirmation in the same session.

## Usage

```
/internal-notes                                   # status mode (default): all current deploy-ready tickets
/internal-notes status                            # explicit
/internal-notes tickets M1-986,M1-1039,M1-1118    # explicit ticket list
/internal-notes mr 6567                           # summarize a single GitLab MR
/internal-notes dry-run                           # print what would be gathered/posted, then exit without posting
```

You may combine the mode with `dry-run`, e.g. `/internal-notes tickets M1-986 dry-run`.

## Pipeline overview

```
1. validate .env keys
2. gather data (Optimus tickets + GitLab MRs, with assignee + MR-author info)
3. resolve developer Slack user IDs via the Slack MCP (best-effort)
4. enrich each ticket with the client institution list
5. per-ticket analyzer agents (parallel) → internal-format summary blocks
6. invoke the internal-storyteller skill → Slack mrkdwn message
7. preview message in chat → user approves
8. on approval: post to #dream-team via slack_upload.py (message only, no PDFs)
```

## Output

- Slack post to the channel resolved from `SLACK_CHANNEL_INTERNAL` (default `#dream-team`, channel id `C1BCUHXT9`). Posted only after the user confirms.
- Markdown copy of the posted message written to `.claude/outputs/notes/internal/internal-notes-<YYYY-MM-DD>.md` with a header showing the channel, ts, and permalink.
- Per-ticket summary blocks written to `/tmp/internal_notes_summaries.txt` for traceability.

Compute the date via `date +%Y-%m-%d` in Bash — do NOT hardcode or guess.

## Required .env keys

| Key | Purpose | Required |
|---|---|---|
| `OPTIMUS_API_KEY` | gather Optimus tickets | Yes |
| `GITLAB_TOKEN` | gather GitLab MR diffs and author | Yes |
| `GITLAB_PROJECT_ID` | GitLab project to query | Yes |
| `GITLAB_URL` | GitLab base URL | optional, defaults to `https://gitlab.com` |
| `SLACK_CHANNEL_INTERNAL` | channel id (`C1BCUHXT9`) or `#dream-team` | Yes |
| `SLACK_BOT_TOKEN` | `xoxb-...` token with `chat:write` scope | Yes |

If any required key is missing, abort early with a clear "Missing required env keys: [...]" message — do NOT proceed to any data gathering, file generation, or Slack call.

## Required permissions

In `.claude/settings.local.json` under `permissions.allow`:

```json
"Bash(python3:*)",
"Bash(date:*)",
"Bash(cat:*)",
"Bash(mkdir:*)",
"Task",
"Skill"
```

## Flow

### Step 1 — Validate environment

Read `.env` from the current working directory. Verify the six required keys above are present. If any are missing, list them and stop.

### Step 2 — Gather data

For `status` mode (default):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py status --output /tmp/internal_notes_data.json --include-description
```

For `tickets <id1,id2,...>`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py tickets <id1,id2,...> --output /tmp/internal_notes_data.json --include-description
```

For `mr <iid>`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py mr <iid> --output /tmp/internal_notes_data.json --include-description
```

For `dry-run`: append `--dry-run` to the call, print the discovered issues + MRs, and exit before any analyzer or Slack call.

The gather script (v0.7+) emits `assignee_name`, `assignee_email`, `assignee_id` on each issue and `author_name`, `author_username` on each MR. This command depends on those fields — older script versions will fall through to "Unassigned" rendering, which is acceptable but ugly.

If zero tickets come back, print `No deploy-ready tickets found. Nothing to post.` and stop before any analyzer call.

### Step 3 — Resolve developer Slack user IDs (best-effort)

For each unique `assignee_name` / `assignee_email` in the data file, call the Slack MCP `slack_search_users` to resolve a Slack user ID. Build a name → slack-id map in memory.

Resolution preference, in order:

1. `slack_search_users` query = `assignee_email` (exact email match → highest confidence).
2. `slack_search_users` query = `assignee_name` (full name).
3. If the MR has a different author from the Optimus assignee (e.g., one engineer takes over another's ticket), also resolve the MR author via `slack_search_users` query = `author_name`.

If no match is found, leave the Slack ID empty for that developer. The internal-storyteller skill falls back to plain name rendering in that case — do not block the pipeline.

Cache resolution results across runs is out of scope for v0; just resolve fresh each run.

### Step 4 — Enrich each ticket with the client institution list

Internal notes carry the client list (e.g., `KFSHRC`, `MSUCVM`, `ADTALEM, AUC`). The ticket description and MR diffs are the source of truth.

For each ticket, build the `CLIENTS` field by:

1. Scanning the Optimus task description for an explicit "Requested by …", "Reported by …", or "Client(s): …" line. If found, extract the comma-separated client tags exactly as written.
2. If no explicit attribution exists, scan the description and MR titles for any all-caps client tag matching the pattern `[A-Z][A-Z0-9-]{2,}` that the team recognizes (e.g., `KFSHRC`, `MSUCVM`, `ADTALEM`, `AUC`, `CVM-NCSU`, `ETSU`, `OHSU`). Keep the original casing.
3. If still empty, set `CLIENTS` to `TBC` — the storyteller will then render a one-line scope description from the SUMMARY (e.g., "TBC — affects any program using case log preceptor approval w/ push notifications enabled").

Do not invent client tags. `TBC` is the correct value for platform-wide work.

### Step 5 — Per-ticket analyzer (parallel)

#### 5a. Write the analyzer instructions file

```bash
cat > /tmp/internal_rn_instructions.txt << 'INSTRUCTIONS_EOF'
You are summarizing one ticket for the internal Medtrics dev team Slack post (#dream-team).

The audience is internal: engineers, CX, account managers, leadership. They KNOW the platform vocabulary. Keep technical specifics. Keep client motivation. Keep the ticket identifier.

Inputs you receive:
  - identifier (M1-NNN / GEN-NNNNNN / MR-NNNN)
  - title
  - description (verbatim)
  - url (Optimus task URL)
  - assignee_name, assignee_email, assignee_slack_id (slack id may be empty)
  - mr titles + author names
  - mr code diffs
  - clients (already resolved by the orchestrator; one of: comma-separated tag list, or "TBC")

Classify the ticket as exactly ONE of:
  - FEATURE: entirely new capability that didn't exist before
  - ENHANCEMENT: improvement to an existing feature
  - BUG FIX: correction of broken or incorrect behavior
  - SECURITY: security-related fix or hardening
  - REFACTOR: code restructuring with no user-visible behavior change

If CATEGORY is REFACTOR and the change has no user-visible effect, return exactly:
NO_INTERNAL_VISIBLE_CHANGE

Otherwise return EXACTLY this block — no preamble, no commentary outside the block:

IDENTIFIER: {identifier}
TITLE: {short engineer-readable title — keep the platform vocabulary}
CATEGORY: {FEATURE|ENHANCEMENT|BUG FIX|SECURITY|REFACTOR}
URL: {url}
DEVELOPER_NAME: {full name of the developer most responsible — Optimus assignee unless the MR was authored by someone else, in which case use the MR author}
DEVELOPER_SLACK_ID: {slack user id, e.g. U02AB0913 — empty string if unknown}
DEVELOPER_FIRST_NAME: {first name only, lowercased}
CLIENTS: {comma-separated tag list verbatim from the orchestrator, or "TBC"}
SUMMARY: {2–4 sentence summary. Lead with the change, not self-praise. Keep technical specifics — module names, mechanism in one clause, behavior in the next. For bug fixes, lead with what was broken in one clause, then what the corrected behavior is. Keep "Requested by {CLIENT} to ..." or "Reported by {CLIENT}" when present in the description. Do NOT use marketing voice. Do NOT apologize.}

Voice rules:
  - Active voice. Past tense for completed work. Present tense for new behavior.
  - Use the team's vocabulary: "evaluation form", "case log", "preceptor approval", "duty hour violation", "bulk import", "open form", "Personal Portal", "Program Settings", "Form Settings".
  - It is fine to mention specific files, models, endpoints, or async dispatch behavior — this is internal.
  - Do NOT mention the IP guard, the storyteller skill, or the deploy pipeline.
  - Length: 2–4 sentences. Never 5+.

OUTPUT FORMAT — Return EXACTLY the 9-field block above (or NO_INTERNAL_VISIBLE_CHANGE).
INSTRUCTIONS_EOF
```

#### 5b. Prepare prompt files

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prepare_note_prompts.py \
    --data /tmp/internal_notes_data.json \
    --instructions /tmp/internal_rn_instructions.txt \
    --prefix internal \
    --output-manifest /tmp/internal_manifest.json
```

Read `/tmp/internal_manifest.json` to get the list of prompt files.

#### 5c. Spawn ALL analyzer agents in ONE assistant message

For every prompt file in the manifest:

- Use the Task tool with `subagent_type: "general-purpose"`.
- `description`: `"Summarize <identifier>"` (chunks: `"Analyze <identifier> chunk <N>"`).
- `prompt`: `Read the file <filepath> and follow the instructions it contains. Before returning, replace any developer placeholder with the resolved values the orchestrator passed at the top of the prompt file (assignee_name, assignee_email, assignee_slack_id, clients).`

All Task calls go in the same assistant message.

> **Important:** the per-ticket prompt files include the resolved `DEVELOPER_SLACK_ID` and `CLIENTS` values that the orchestrator computed in Steps 3–4. The analyzer should copy those into the output block verbatim — it should not attempt to re-resolve them.

#### 5d. Collect results

For each ticket, you now have either:

- A 9-field block, or
- `NO_INTERNAL_VISIBLE_CHANGE` (drop from downstream).

For chunked tickets, combine chunks by picking the most user-visible block. Write the collected per-ticket blocks to `/tmp/internal_notes_summaries.txt`, one block per ticket, separated by `---`.

### Step 6 — Synthesize via the internal-storyteller skill

Invoke the bundled `medtrics-release-notes:internal-storyteller` skill, passing it `/tmp/internal_notes_summaries.txt` and today's date. The skill produces the Slack mrkdwn message and writes it to `/tmp/internal_notes_message.txt`.

If the skill returns `NO_INTERNAL_NOTES — nothing customer-visible shipped this deploy`, stop the pipeline: do not preview, do not post, just print that line back to the user.

The internal-storyteller does **not** run through the IP guard or the copy-audit skill — the post is meant to carry internal vocabulary and ticket identifiers. Both of those skills are configured for customer-facing copy and would refuse the message.

### Step 7 — Preview to user

Print the composed Slack message inside a fenced block AND show the channel it will go to. Then ask:

```
Ready to post to <#CHANNEL>?
  Channel: <channel display>  (#dream-team)
  Message length: <N> chars
  Items: <X> enhancements / <Y> bug fixes

  [y] post message
  [n] cancel (no Slack action taken; summaries + draft remain on disk)
  [e] let me edit the draft message first
```

If user picks `e`, accept their edits in chat, write the edited message back to `/tmp/internal_notes_message.txt`, re-show the preview, loop until `y` or `n`.

### Step 8 — Post (only if user said `y`)

Run the bundled upload script with no `--pdf` arguments — message only:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_upload.py \
    --channel "$SLACK_CHANNEL_INTERNAL" \
    --message-file /tmp/internal_notes_message.txt
```

The script:

1. Loads `SLACK_BOT_TOKEN` from `.env`.
2. Resolves the channel (id pass-through, or `#dream-team` → id via `conversations.list`).
3. Posts the message via `chat.postMessage`.
4. Prints a JSON line `---SLACK_UPLOAD_RESULT---` followed by `{"ok": true, "channel": "...", "ts": "...", "uploaded": []}` on success.

Parse the JSON result. If `ok=true`:

- Save a copy of the message text to `.claude/outputs/notes/internal/internal-notes-<YYYY-MM-DD>.md` with a header showing the channel name, ts, permalink, and the per-ticket summary file path used to produce it.
- Print a one-line confirmation: `Posted to <#dream-team>. ts=<ts>. (<N> items: <X> enhancements, <Y> bug fixes.)`.

If the script exits non-zero, surface its stderr verbatim and do NOT retry automatically.

## Failure modes and behavior

| Condition | Behavior |
|---|---|
| Missing required env keys | Abort before any tool call, list missing keys |
| Gather returns zero tickets | Print "Nothing to post" and stop |
| Slack user resolution returns nothing for a developer | Render that developer with plain name only; continue |
| Storyteller returns `NO_INTERNAL_NOTES` | Stop, do not preview, do not post |
| Channel resolves to nothing | Print error, do not post |
| `slack_upload.py` returns non-zero | Print stderr, do not retry |
| User declines at preview | No Slack call; summaries + message draft remain on disk |

## Things this command does NOT do

- Does not run `/deploy-notes` or `/integration-notes` — those produce customer-facing artifacts and are owned by `/release-slack`. The two pipelines are independent on purpose so the internal post can ship even if a customer-facing draft is still being polished.
- Does not run the IP guard or the copy-audit skill — internal vocabulary is the whole point of this message.
- Does not render a PDF.
- Does not modify any Optimus tickets or GitLab MRs.
- Does not write to `.env` or to the plugin directory.
- Does not retry Slack failures.
- Does not auto-schedule itself.

## Coding Standards

- **Data gathering is handled by `gather_notes_data_optimus.py`.** Do NOT run individual Optimus or GitLab calls inline.
- **Developer Slack ID resolution is handled by the Slack MCP** (`slack_search_users`). Do NOT shell out to `curl`.
- **Per-ticket synthesis is handled by analyzer Task agents** — one per ticket, spawned in a single assistant message.
- **Message composition is handled by the `internal-storyteller` skill.** Do NOT compose the Slack message body directly in the command.
- **Slack delivery is handled by `slack_upload.py`** with no `--pdf` flags. Do NOT use the Slack MCP for the post itself; the bundled script handles channel resolution and `chat.postMessage` consistently with the rest of the pipeline.
- **Output filename uses today's date computed via `date +%Y-%m-%d`** — never hardcoded.
- **Channel resolution is exact-match only.** If `SLACK_CHANNEL_INTERNAL` is a name that matches multiple channels, the script will error — surface it and stop.
