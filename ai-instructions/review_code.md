# Code Review

Review the current branch's changes, triage findings collaboratively, and surface validated issues for discussion.

This command uses a two-phase approach: a **review agent** produces raw findings, then the **session agent** (who has full context of what was built and why) triages those findings before presenting them to the user.

---

## How It Works

```text
┌─────────────────┐     raw findings     ┌─────────────────┐     validated findings     ┌──────┐
│  Review Agent   │ ──────────────────▶  │  Session Agent  │ ──────────────────────────▶ │ User │
│  (fresh eyes)   │                      │  (knows context)│ ◀────────────────────────── │      │
└─────────────────┘                      └─────────────────┘    discuss / fix / dismiss  └──────┘
```

- **Review Agent**: Spawned as a sub-agent. Has no conversation context. Reviews the code with fresh eyes using only the diff, full files, and project conventions. Produces raw findings.
- **Session Agent**: You (the main session). You have the full conversation history — you know *what* was built, *why* decisions were made, and *what trade-offs were accepted*. You triage the raw findings before presenting them.

---

## Step 1: Spawn the Review Agent

Launch a review sub-agent using the Task tool.

### Before spawning the agent

The session agent (you) must gather all git context BEFORE spawning the review agent. This avoids the review agent needing to run git commands itself (which triggers repeated permission prompts).

Run this single command to collect everything the review agent needs:

```bash
BASE=$(git log --oneline HEAD ^master --grep="Merge branch 'master'" | head -1 | cut -d' ' -f1); if [ -z "$BASE" ]; then BASE=$(git merge-base master HEAD); fi; echo "=== BASE: $BASE ===" && echo "=== BRANCH: $(git branch --show-current) ===" && echo "=== CHANGED FILES ===" && git diff --name-only ${BASE}..HEAD && echo "=== DIFF ===" && git diff ${BASE}..HEAD
```

Then pass the output (changed file list + diff) directly into the review agent's prompt. The review agent should NOT need to run any git commands.

### What the review agent does

With the diff and file list provided in its prompt, the agent should:

1. **Read changed files in full** - Don't review diffs in isolation; read the complete files to understand context
2. **Load module rules** - For each touched module, check if an `AGENTS.md` exists and read it
3. **Load module ADRs** - For each touched module, check if a `decisions/` directory exists and read relevant ADRs. Also check `docs/decisions/` for cross-cutting ADRs.
4. **Read `ai-instructions/conventions.md`** for project-wide rules
5. **Run linter check** - Run ruff on all changed `.py` files (see Linting criteria in Step 2 for reporting details)
6. **Apply review criteria** (see Step 2 below) and produce raw findings in the structured format (see Step 3 below)
7. **Be thorough** - Flag anything suspicious, even if uncertain

### What the review agent returns

- List of all changed files with a short description of what changed
- Which modules are affected
- Whether tests were added/modified
- Whether migrations were added/modified
- Ruff linter output (pass/fail + any violations)
- Raw findings in the structured format

---

## Step 2: Review Criteria

The review agent checks every change against these criteria. Reference `conventions.md` rules throughout.

### Correctness

- Does the code do what it's supposed to do?
- Are there logical errors, off-by-one mistakes, or missed edge cases?
- Check boundary conditions: empty lists, None values, zero-length strings at every public method entry point
- Check for duplicate keys in list inputs where uniqueness is assumed (e.g., iterating a list but validating with a set)
- Are database queries correct? (wrong filters, missing `.distinct()`, N+1 queries)
- Are status transitions valid? (check model state machines)
- For any method that reads or changes status: enumerate every status the object could have when entering that method, and verify the outcome is correct for each one. Don't just check the happy path — check what happens when the object is already in the target state, or in an adjacent state that wasn't explicitly handled.
- If this PR adds a new relationship or state field to an existing model (a self-referencing FK, a new status value, a "merged/linked/grouped" concept), find every other place in the codebase that mutates that model and verify each one correctly handles rows in the new state. Check every mutation path, not just `ModelName.objects.` calls: instance `save()`/`delete()`, manager/QuerySet writes (`create()`, `update()`, `delete()`, `bulk_create()`, `bulk_update()`, `get_or_create()`, `update_or_create()`), related-manager writes, and service or raw-SQL paths. A row already in the new state being silently deleted, overwritten, or double-processed by an older code path is a CRITICAL finding.
- Are error conditions handled at system boundaries?

### Linting

- Run `ruff check <changed .py files>` and `ruff format --check <changed .py files>`
- Report any violations as findings (severity: ISSUE)
- If ruff passes cleanly, note it in the summary as "Ruff: PASS"
- If ruff fails, include the full output and list each violation with file and line number

### Conventions Compliance

- **Comments** - Only where necessary, explaining "why" not "what" (conventions.md)
- **Migrations** - Auto-generated for schema changes, manual only for `RunPython` (conventions.md)
- **URL naming** - Singular, matching model name (conventions.md)
- **No over-engineering** - No unnecessary abstractions, error handling for impossible cases, or future-proofing

### Security

- No secrets, credentials, or API keys in code
- No SQL injection (raw queries with string formatting)
- No XSS vectors (unescaped user input in templates/responses)
- Permissions checked on endpoints
- No command injection in subprocess calls

### Performance

- No N+1 queries (missing `select_related`/`prefetch_related`)
- No unbounded querysets (missing pagination or limits)
- No expensive operations inside loops
- Appropriate use of `bulk_create`/`bulk_update` for batch operations
- Database indexes for fields used in filters/ordering

### Test Coverage

- Are new code paths covered by tests?
- Do tests follow `write_tests.md` patterns? (behavior-based, `setUpTestData`, proper assertions)
- Are edge cases tested?
- Are mocks scoped correctly? (mock external services, not internal logic)

### Migration Safety

- Will the migration lock tables on large datasets? (adding non-nullable columns without defaults, creating indexes without `CONCURRENTLY`)
- Is the migration backwards-compatible with the current running code? (can old code run against the new schema during deploy?)
- Are there data migrations (`RunPython`) that could timeout on large tables?
- Are there irreversible operations without a rollback plan?
- Are there duplicate indexes? (e.g., `db_index=True` on a field that also appears in `Meta.indexes`)

### API Contract / Breaking Changes

- Are any serializer fields removed or renamed? (breaking change for frontend)
- Are any endpoint URLs changed or removed?
- Are required fields added to request serializers? (breaks existing API callers)
- Do response format changes need frontend coordination?
- Are new endpoints missing from `drf-spectacular` schema decorators?

### Concurrency / Race Conditions

- Are there race conditions between concurrent Celery tasks operating on the same objects?
- Are database operations that need atomicity wrapped in `transaction.atomic()`?
- Are there TOCTOU (time-of-check-time-of-use) bugs? (checking a condition then acting on it without holding a lock or transaction)
- Are read-then-update patterns protected with `select_for_update()` or `F()` expressions where appropriate?
- For Celery tasks: is the task idempotent? Can it be safely retried?
- Are there shared mutable state issues between request threads?

### ADR Compliance

- Do changes conflict with any ADRs in `docs/decisions/` or the module's `decisions/` directory?
- Examples: putting business logic in models (violates ADR-001 service layer), making synchronous external API calls (violates ADR-002 event-driven integrations), directly creating line items outside Invoice aggregate (violates invoicing ADR-003)
- If a change intentionally deviates from an ADR, flag it — the ADR may need to be updated or superseded

### Module-Specific Rules

- Check the relevant `AGENTS.md` for any module-specific conventions that apply
- Flag violations of module-specific patterns

### Dependency / Import Boundaries

- Are new packages added? Are they maintained and not duplicating existing dependencies?
- Do new cross-module imports respect module boundaries? (e.g., external code importing from a module's `services/` internals rather than its public interface)
- Are there new circular import risks beyond what's already flagged under Clean Code?

### Logging & Observability

- Do new error paths have logging? (will failures be visible in Datadog?)
- Do Celery tasks log enough context for debugging? (event_id, voyage_id in `extra` dict)
- Are there bare `except` clauses that swallow errors silently?
- Are new endpoints or tasks missing structured logging?

### Clean Code

- No dead code, commented-out code, or debug statements (`print`, `breakpoint`, `console.log`)
- No TODO/FIXME/HACK comments without a clear explanation
- Imports organized (stdlib, third-party, local)
- No circular import risks (check for local imports that should be top-level or vice versa)

---

## Step 3: Raw Finding Format

The review agent returns findings in this format:

### Severity Levels

| Level | Meaning | Action Required |
|-------|---------|-----------------|
| **CRITICAL** | Bug, security issue, data loss risk, or broken functionality | Must fix before merge |
| **ISSUE** | Code smell, convention violation, or potential problem | Should fix before merge |
| **SUGGESTION** | Improvement idea, minor style nit, or alternative approach | Discuss, fix if agreed |

### Finding Format

```text
### [SEVERITY] Short description

**File:** `path/to/file.py:LINE`

**What:** Description of the issue.

**Why it matters:** Impact or risk.

**Suggested fix:** Concrete suggestion (code snippet if helpful).
```

---

## Step 4: Triage Findings (Session Agent)

This is the collaborative step. Once the review agent returns raw findings, the session agent (you) triages each one using your knowledge of the conversation context.

### For each finding, decide

1. **AGREE** - The finding is valid. You confirm it's a real issue.
2. **DISMISS** - The finding is wrong given the context. You know *why* the code is written that way and the reviewer didn't have that context.
3. **PARTIAL** - The reviewer has a point, but the suggested fix is wrong or the severity is off. Adjust it.

### How to triage

For each finding, evaluate:

- **Was this an intentional decision?** - If the conversation history shows this was a deliberate choice, dismiss it and explain why.
- **Does the reviewer lack context?** - The reviewer doesn't know what the user asked for. If a finding contradicts the user's requirements, dismiss it.
- **Is the reviewer right despite our intent?** - Sometimes we made a mistake even though we had reasons. If the logic is actually wrong, agree with the finding.
- **Is the severity correct?** - A "CRITICAL" might actually be a "SUGGESTION" in context, or vice versa.

### Rules for "pre-existing code" dismissals

**NEVER dismiss a finding by claiming code is "pre-existing" or "not part of this branch" unless you can verify it from the diff.** Lines prefixed with `+` in the diff are new code from this branch. Lines with no prefix are context lines.

- If a finding references code that appears with a `+` prefix in the diff, it IS from this branch — do not dismiss it as pre-existing.
- If you are unsure whether code is pre-existing or new, **do not dismiss it**. Keep the finding and let the user decide.
- When in doubt, check the diff output that was collected in Step 1. If the relevant code is not visible in the diff at all, it may genuinely be pre-existing — but say "I could not confirm this in the diff" rather than asserting it as fact.

### Triage output

Present the triaged findings to the user like this:

```text
## Code Review Results

**Branch:** branch-name
**Files changed:** N
**Raw findings from reviewer:** X total
**After triage:** Y validated, Z dismissed

---

### Validated Findings

#### #1 [SEVERITY] Short description
**File:** `path/to/file.py:LINE`
**Reviewer said:** ...
**My assessment:** I agree — this is a real issue because...
**Suggested fix:** ...

#### #2 [SEVERITY] Short description
**File:** `path/to/file.py:LINE`
**Reviewer said:** ...
**My assessment:** Partially agree — the reviewer has a point about X, but Y is intentional. Adjusted severity from CRITICAL to SUGGESTION.
**Suggested fix:** ...

---

### Dismissed Findings

#### [DISMISSED] Short description
**Reviewer said:** ...
**Why dismissed:** This was intentional — we discussed in this session that [reason]. The reviewer didn't have this context.

---
```

### Triage rules

- **Be honest** - If the reviewer found a real bug, admit it even if you wrote the code
- **Explain dismissals** - Always say *why* a finding was dismissed, referencing the specific context
- **Don't over-dismiss** - When in doubt, keep the finding and let the user decide
- **Adjust severity freely** - The reviewer doesn't have context to judge severity accurately; you do

---

## Step 5: Discussion with User

After presenting triaged findings:

1. **Wait for response** - The user may agree, disagree, or want to discuss specific findings
2. **Fix on request** - If the user says "fix it" or "fix #2", apply the suggested fix directly
3. **Dismiss on request** - If the user disagrees with a finding, drop it — no arguing
4. **Reinstate on request** - If the user thinks a dismissed finding was actually valid, bring it back
5. **Re-review on request** - After fixes are applied, the user can ask to re-run the full review

### Discussion rules

- Don't be defensive about findings — if the user says it's fine, it's fine
- Don't repeat dismissed findings
- Keep responses focused on the specific finding being discussed
- When fixing, make the minimal change needed — don't expand scope

---

## Checklist

Before presenting the review:

- [ ] Review agent has read all changed files in full (not just diffs)
- [ ] Review agent checked module-specific AGENTS.md rules
- [ ] Review agent checked relevant ADRs in `decisions/` directories
- [ ] Review agent applied conventions.md rules
- [ ] Review agent ran `ruff check` and `ruff format --check` on changed files
- [ ] Review agent checked migration safety (if migrations present)
- [ ] Review agent checked for API breaking changes (if serializers/views changed)
- [ ] Every finding has a file path and line number
- [ ] Session agent has triaged every raw finding
- [ ] Dismissed findings include clear reasoning
- [ ] Validated findings are categorized by severity
- [ ] Summary with counts is included
