---
description: Generate dev, deploy, and integration release notes in parallel
---

# All Notes Generator

Generates all three types of notes in parallel: dev notes, deploy (release) notes, and integration change notes.

## Usage

```
/notes                              # Issues currently in QA1, QA2, Code Review, Needs Changes, Pipeline Issue
/notes status                       # Same as above (explicit)
/notes tickets M1-583,GEN-128592,M1-848   # Specific tickets from a deploy
/notes mr 6567                      # Analyze a single GitLab MR
/notes status dry-run               # Preview issues and matched MRs (no analysis)
/notes tickets M1-583,GEN-128592 dry-run
/notes mr 6567 dry-run
```

## Required Permissions

For autonomous execution without per-command approval prompts, ensure these are in `.claude/settings.local.json` under `permissions.allow`:

```json
"Bash(python3:*)",
"Bash(date:*)",
"Bash(cat:*)",
"Bash(cp:*)",
"Bash(mkdir:*)",
"Task"
```

## Arguments

Parse `$ARGUMENTS` exactly as the individual commands do:

- **No arguments or `status`**: Status mode
- **`tickets <id1,id2,...>`**: Tickets mode — comma-separated list of Optimus task identifiers
- **`mr <iid>`**: Single MR mode
- **`dry-run`** (can be appended to any mode): Preview only

## Execution

### Step 1: Gather data once, then derive per-command data files

Run the shared data gathering script **once** with `--include-description` (all commands now use it). Then copy and filter for each command's needs.

**Status mode:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py status --output /tmp/dev_notes_data.json --include-description
cp /tmp/dev_notes_data.json /tmp/release_notes_data.json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py status --output /tmp/integration_notes_data.json --include-description --filter-integration
```

**Tickets mode:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py tickets <id1,id2,...> --output /tmp/dev_notes_data.json --include-description
cp /tmp/dev_notes_data.json /tmp/release_notes_data.json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py tickets <id1,id2,...> --output /tmp/integration_notes_data.json --include-description --filter-integration
```

**MR mode:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py mr <iid> --output /tmp/dev_notes_data.json --include-description
cp /tmp/dev_notes_data.json /tmp/release_notes_data.json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gather_notes_data_optimus.py mr <iid> --output /tmp/integration_notes_data.json --include-description --filter-integration
```

If `dry-run`, add `--dry-run` to the first command. Display the summary output and stop. Do not proceed further.

**Note:** The integration data still requires a second script run because `--filter-integration` filters diffs at fetch time (removing non-integration files and discarding MRs with zero relevant diffs). This cannot be done by post-processing the full data file.

### Step 2: Prepare prompts for all 3 note types (orchestrator does this)

**IMPORTANT: The orchestrator (you) must do ALL prompt preparation. Sub-agents cannot reliably use Bash or Write tools due to permission inheritance limitations.**

#### 2a. Write instruction files

Write the 3 instruction files. These contain the analysis instructions that get appended to each prompt:

```bash
cat > /tmp/dn_instructions.txt << 'INSTRUCTIONS_EOF'
Summarize this ticket for a developer-facing technical change notes document.

CONTEXT:
You are given an Optimus task (with title and description) and one or more GitLab MRs (with titles and code diffs). Your job is to write both a clear summary of what this change does AND a technical breakdown of how it was implemented.

INSTRUCTIONS:
1. Read the task description carefully — this is the primary source of what the ticket delivers.
2. Read the diffs carefully — understand what files were changed, what logic was added/modified/removed.
3. If the diffs are large or the task description is sparse, use codebase context — read related source files to understand the broader picture.
4. Classify the ticket as exactly ONE of:
   - FEATURE: Entirely new capability that didn't exist before
   - ENHANCEMENT: Improvement or addition to an existing feature
   - BUG FIX: Correction of broken or incorrect behavior
   - REFACTOR: Code restructuring with no user-facing behavior change
5. Write a 2-4 sentence summary in plain language explaining what the ticket delivers (similar to release notes — what can users now do, or what problem was fixed).
6. Write a technical details section covering:
   - Key files modified and why
   - Notable implementation decisions (new models, serializer changes, permission changes, migration details, frontend component changes, etc.)
   - Any important side effects or dependencies introduced

OUTPUT FORMAT — Return EXACTLY this structure (no preamble, no explanation outside the structure):

CATEGORY: [FEATURE|ENHANCEMENT|BUG FIX|REFACTOR]
IDENTIFIER: {issue_identifier}
TITLE: {short descriptive title}
SUMMARY: {2-4 sentence plain-language summary}
TECHNICAL DETAILS:
{bullet-pointed technical breakdown}
INSTRUCTIONS_EOF
```

```bash
cat > /tmp/rn_instructions.txt << 'INSTRUCTIONS_EOF'
Summarize this ticket for a client-facing release notes document.

CONTEXT:
You are given an Optimus task (with title and description) and one or more GitLab MRs (with title and code diffs). Your job is to write a short, clear summary of what this change does for end users.

INSTRUCTIONS:
1. Read the task description carefully — this is the primary source of what the ticket delivers.
2. Read the diffs to understand the scope and specifics of what was changed (e.g., which modules are affected: schedules, evaluations, users, etc.).
3. If the task description is sparse or unclear, use codebase context — read related source files to understand the broader picture.
4. Classify the ticket as exactly ONE of:
   - FEATURE: Entirely new capability that didn't exist before
   - ENHANCEMENT: Improvement or addition to an existing feature
   - BUG FIX: Correction of broken or incorrect behavior
   - SECURITY: Security-related fix or hardening
5. Write a 2-4 sentence summary in plain language. Focus on what the user can now do or what problem was resolved. Avoid technical jargon (no mention of serializers, viewsets, migrations, querysets, etc.). Write as if explaining to a program administrator, not a developer.

OUTPUT FORMAT — Return EXACTLY this structure (no preamble, no explanation outside the structure):

CATEGORY: [FEATURE|ENHANCEMENT|BUG FIX|SECURITY]
IDENTIFIER: {issue_identifier}
TITLE: {short user-friendly title — rewrite the task title if it's too technical}
SUMMARY: {2-4 sentence plain-language summary of what changed and what users can now do}
INSTRUCTIONS_EOF
```

```bash
cat > /tmp/in_instructions.txt << 'INSTRUCTIONS_EOF'
Analyze this issue's integration-relevant diffs for a client-facing change notes document.

INSTRUCTIONS:
1. Read the diffs carefully — identify what fields, endpoints, permissions, or schema elements were added, changed, or removed.
2. Use codebase context — Read source files on the current branch to understand the BASELINE structure (what existed before the MR). The diff shows what changed. For example:
   - If a serializer field was added, check the model to understand the field type and whether it's nullable/optional.
   - If a viewset method was changed, check the URL routing to understand which endpoint is affected.
   - If a migration was added, the diff already contains the migration content.
3. Classify the change as:
   - BREAKING: Removals, renames, type changes, permission restrictions — anything that will break existing integrations
   - NON-BREAKING: New optional fields, new endpoints, new filters — additions that don't affect existing behavior
   - DEPRECATION: Features marked for future removal

OUTPUT FORMAT — Return EXACTLY this markdown structure (no preamble, no explanation outside the structure):

### [BREAKING|NON-BREAKING|DEPRECATION] Short description
**Source:** {issue_identifier} — {issue_title} (MR !{iid})
**Files:** {list of affected files}

**What changed:**
Description of the change with specifics (field names, types, endpoints, etc.).

**Impact:**
How this affects API consumers.

**Migration guide:** (only for BREAKING and DEPRECATION)
Step-by-step instructions for updating integrations.

If the issue's MR(s) have no meaningful integration impact after analysis (e.g., whitespace-only migration), return exactly:
SKIP: {issue_identifier} — {reason}
INSTRUCTIONS_EOF
```

#### 2b. Run the prompt preparation script for all 3 types

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prepare_note_prompts.py \
    --data /tmp/dev_notes_data.json \
    --instructions /tmp/dn_instructions.txt \
    --prefix dn \
    --output-manifest /tmp/dn_manifest.json

python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prepare_note_prompts.py \
    --data /tmp/release_notes_data.json \
    --instructions /tmp/rn_instructions.txt \
    --prefix rn \
    --output-manifest /tmp/rn_manifest.json

python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prepare_note_prompts.py \
    --data /tmp/integration_notes_data.json \
    --instructions /tmp/in_instructions.txt \
    --prefix in \
    --output-manifest /tmp/in_manifest.json
```

Read all 3 manifests to confirm prompt counts.

### Step 3: Spawn 3 command agents in ONE message

**HARD RULE: Spawn ALL 3 agents in a SINGLE assistant message. Do NOT spawn them sequentially.**

Each agent reads the respective command file and follows Steps 2b-3 only (data gathering AND prompt preparation are already done).

**Agent 1 — Dev Notes:**
- `subagent_type: "general-purpose"`
- `description: "Generate dev notes"`

**Agent 2 — Deploy Notes:**
- `subagent_type: "general-purpose"`
- `description: "Generate deploy notes"`

**Agent 3 — Integration Notes:**
- `subagent_type: "general-purpose"`
- `description: "Generate integration notes"`

**Agent prompt template:**
```
Read the file .claude/commands/<COMMAND>.md for context on the output format and assembly rules.

You are generating <NOTE_TYPE> notes. Data gathering (Step 1) and prompt preparation (Step 2a) have ALREADY been completed by the orchestrator. Do NOT run the gather script or prepare_note_prompts.py. Do NOT write instruction files.

The manifest of prompt files is at <MANIFEST_PATH>. Read it to get the list of prompt files.

Start from Step 2b (Spawn ALL agents in ONE message) and continue through Step 3 (Assemble Output).

At Step 3, instead of writing to a file, OUTPUT THE FULL ASSEMBLED MARKDOWN DOCUMENT as your response. Start your response with the exact line "---OUTPUT_START---" followed by the full markdown content, then end with "---OUTPUT_END---". Do not include any other text outside these markers. The orchestrator will write it to the output file.

Important:
- The manifest is ready at <MANIFEST_PATH> — read it and proceed directly to agent spawning.
- Today's date: <TODAY>
- Do NOT use Bash, Write, or any file-writing tools for the final output. Just return the content.
```

| Agent | Command file | Note type | Manifest path |
|---|---|---|---|
| Dev Notes | `dev-notes.md` | developer technical | `/tmp/dn_manifest.json` |
| Deploy Notes | `deploy-notes.md` | client-facing release | `/tmp/rn_manifest.json` |
| Integration Notes | `integration-notes.md` | integration change | `/tmp/in_manifest.json` |

Compute `<TODAY>` via `date +%Y-%m-%d` before spawning agents.

### Step 4: Write outputs and report results

After all 3 agents complete, extract the markdown content from each agent's result (between `---OUTPUT_START---` and `---OUTPUT_END---` markers) and write to the final output files:

```bash
mkdir -p .claude/outputs/notes/dev .claude/outputs/notes/deploy .claude/outputs/notes/integration
```

Determine the output filename suffix based on mode:
- **status mode**: `status-<YYYY-MM-DD>` (use the same date computed earlier)
- **milestone mode**: `milestone-<name>`
- **mr mode**: `mr-<iid>`

Write each file using the Write tool:
- `.claude/outputs/notes/dev/dev-notes-<suffix>.md`
- `.claude/outputs/notes/deploy/deploy-notes-<suffix>.md`
- `.claude/outputs/notes/integration/integration-notes-<suffix>.md`

If an agent's result doesn't contain the output markers (e.g., the agent hit an error), check:
1. Whether the agent wrote to the legacy temp path (`/tmp/<type>_notes_output.md`) as a fallback
2. Whether the agent's result message contains usable content that can be extracted

Report which output files were generated and any failures.

## Important Notes

- **The orchestrator handles ALL file I/O.** Sub-agents (command agents and their Task sub-agents) cannot reliably use Bash or Write tools due to permission inheritance limitations. The orchestrator writes instruction files, runs preparation scripts, and writes final output files. Agents only read files, spawn Tasks, and return assembled content.
- The data gathering script runs twice: once for the full data (dev/deploy share it via copy), and once with `--filter-integration` for integration notes.
- Each agent independently handles its own Task spawning (Step 2b) and result collection/assembly (Steps 2c-2d and 3). The master command does NOT manage individual issue analysis.
- If one agent fails, the others should still complete. Report any failures at the end.
