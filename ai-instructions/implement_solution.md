# Solution Implementation

After completing `/plan_solution` and having a confirmed `docs/solutions/{problem_name}_solution.md`, follow these steps to implement.

---

## Step 6: Epic and Ticket Generation

Break down the solution into manageable work units.

### Structure

```
Solution
└── Epic (1-3 per solution)
    └── Ticket (1-5 per epic)
```

### Guidelines

**Epics** = Meaningful, distinct groups of work
- Each epic delivers a coherent piece of functionality
- Epics can be deployed/tested independently when possible
- Name should describe the capability: "Invoice Duplicate Detection", "Veson Integration API"

**Tickets** = Atomic units of work
- Each ticket is completable in a focused session
- Clear scope - you know when it's done
- Minimal dependencies on other tickets when possible

### Output format

Append an `## Implementation Plan` section to `docs/solutions/{problem_name}_solution.md`:

```markdown
## Implementation Plan

### EPIC-1: [Epic Name]
What this epic delivers.

#### [ ] T1.1: [Ticket Title]
- **Prerequisites:** None
- **Files:** `path/to/file1.py`, `path/to/file2.py`
- **Approach:** Description of implementation approach and key considerations
- **Acceptance criteria:**
  - [ ] Criterion 1 - specific, testable
  - [ ] Criterion 2 - specific, testable

#### [ ] T1.2: [Another Ticket]
- **Prerequisites:** T1.1
- **Files:** `path/to/file.py`
- **Approach:** Description
- **Acceptance criteria:**
  - [ ] Criterion 1
  - [ ] Criterion 2
```

---

## Step 7: Epic and Ticket Review

Before implementing, verify the breakdown:

- [ ] **Coverage** - Do tickets fully implement the solution?
- [ ] **Gaps** - Any missing pieces?
- [ ] **Order** - Are prerequisites correctly identified?
- [ ] **Size** - Are tickets appropriately scoped (not too big, not too small)?
- [ ] **Clarity** - Is each ticket clear enough to implement without ambiguity?
- [ ] **Testability** - Can acceptance criteria be verified?

### User confirmation

Present the epic/ticket breakdown to the user:

```
## Proposed Breakdown

### EPIC-1: [Name]
- T1.1: [Title] - [Brief description]
- T1.2: [Title] - [Brief description]

### EPIC-2: [Name]
- T2.1: [Title] - [Brief description]

## Dependencies
- T1.2 depends on T1.1
- T2.1 can run in parallel with EPIC-1

---

Does this breakdown look right? Any tickets to add, remove, or restructure?
```

After user confirms, save the `## Implementation Plan` section into `docs/solutions/{problem_name}_solution.md`.

---

## Step 8: Ticket Implementation

Implement tickets one at a time, in order.

### Setup (once per solution)

Ask the user for the branch name/number, then create the branch (or run `/create_worktree <branch-name>`):

```bash
git checkout -b problem-name-DEV-#### origin/master
```

### Per-ticket workflow

#### 8.1 Context Loading

Read:
- The ticket details and full solution in `docs/solutions/{problem_name}_solution.md`
- `ai-instructions/conventions.md` and any relevant `AGENTS.md` files for the modules being touched

#### 8.2 Verify Ticket Readiness

Confirm the ticket has:
- [ ] Clear implementation details
- [ ] Testable acceptance criteria
- [ ] All prerequisite tickets completed

If anything is missing, fill it in before proceeding.

#### 8.3 Clarifying Questions

Ask only **important** clarifying questions. Skip minor details you can reasonably decide yourself.

```
Before implementing T1.2, I need to confirm:
- [Important question about ambiguous requirement]
```

#### 8.4 Implementation

Write the code following:
- Patterns in the codebase
- Conventions in `ai-instructions/conventions.md` and module `AGENTS.md` files
- The approach specified in the ticket

#### 8.5 User Verification

After implementation, ask the user to verify:

```
T1.2 implementation complete.

Changes:
- Added X to file1.py
- Modified Y in file2.py

Please verify:
- [ ] Functionality works as expected
- [ ] No regressions in related features

Ready for me to proceed with tests?
```

#### 8.6 Write Tests

Follow `ai-instructions/write_tests.md` and `webatds/tests/AGENTS.md`:

- Write tests covering the acceptance criteria
- Run tests to verify they pass
- Ensure no existing tests are broken

```bash
python manage.py test webatds.tests.{module}.{test_file} --keepdb
```

#### 8.7 Update Ticket Status

In `docs/solutions/{problem_name}_solution.md`, mark the ticket and its acceptance criteria complete (`#### [x] T1.2: ...`) and note any variance from the original plan under the ticket entry.

#### 8.8 Commit

```bash
git add [specific files]
git commit -m "$(cat <<'EOF'
T1.2: [Concise description of changes]

- Detail 1
- Detail 2
EOF
)"
```

#### 8.9 Next Ticket

Move to the next ticket and repeat from step 8.1.

---

## Completion

After all tickets are complete:

1. Verify all tickets in `docs/solutions/{problem_name}_solution.md` are checked off
2. Run the test suite and `ruff check` on affected modules
3. Create PR following standard process:

```bash
gh pr create --title "[Problem Name]" --body "$(cat <<'EOF'
## Summary
[Brief description of what this PR delivers]

## Solution Document
See: `docs/solutions/{problem_name}_solution.md`

## Tickets Completed
- T1.1: [Title]
- T1.2: [Title]
- T2.1: [Title]

## Test Plan
- [ ] Unit tests pass
- [ ] Manual verification of [key flows]
EOF
)"
```
