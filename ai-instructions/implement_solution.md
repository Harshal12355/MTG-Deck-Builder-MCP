# Solution Implementation

After completing `/plan_solution` and having a confirmed `{problem_name}_solution.md`, follow these steps to implement.

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

Write epics and tickets in JSON:

```json
{
  "solution": "{problem_name}",
  "epics": [
    {
      "epic_id": "EPIC-1",
      "name": "Epic Name",
      "description": "What this epic delivers",
      "tickets": [
        {
          "ticket_id": "T1.1",
          "title": "Ticket Title",
          "description": "What this ticket accomplishes",
          "implementation_details": {
            "files": ["path/to/file1.py", "path/to/file2.py"],
            "approach": "Description of implementation approach",
            "key_considerations": ["Consideration 1", "Consideration 2"]
          },
          "acceptance_criteria": [
            "Criterion 1 - specific, testable",
            "Criterion 2 - specific, testable",
            "Criterion 3 - specific, testable"
          ],
          "prerequisite_tickets": [],
          "completion_status": "not_started"
        },
        {
          "ticket_id": "T1.2",
          "title": "Another Ticket",
          "description": "What this ticket accomplishes",
          "implementation_details": {
            "files": ["path/to/file.py"],
            "approach": "Description",
            "key_considerations": []
          },
          "acceptance_criteria": [
            "Criterion 1",
            "Criterion 2"
          ],
          "prerequisite_tickets": ["T1.1"],
          "completion_status": "not_started"
        }
      ]
    }
  ]
}
```

### Ticket fields explained

| Field | Purpose |
|-------|---------|
| `ticket_id` | Unique ID: T{epic#}.{ticket#} |
| `title` | Short, descriptive name |
| `description` | What the ticket accomplishes |
| `implementation_details` | Files to touch, approach, considerations |
| `acceptance_criteria` | Specific, testable conditions for "done" |
| `prerequisite_tickets` | Tickets that must complete first |
| `completion_status` | `not_started`, `in_progress`, `completed` |

---

## Step 7: Epic and Ticket Review

Before implementing, review the breakdown:

### Check for

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

After user confirms, write the breakdown to: `{problem_name}_tickets.json`

---

## Step 8: Ticket Implementation

Implement tickets one at a time, in order.

### Setup (once per solution)

Ask the user for the branch number, then create the branch:

```bash
git checkout -b problem-name-DEV-####
```

### Per-ticket workflow

#### 8.1 Context Loading

Read:
- The ticket details from `{problem_name}_tickets.json`
- The full solution from `{problem_name}_solution.md`
- Any relevant AGENTS.md files for the modules being touched

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
- Conventions in AGENTS.md files
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

Follow `write_tests.md` and `webatds/tests/AGENTS.md`:

- Write tests covering the acceptance criteria
- Run tests to verify they pass
- Ensure no existing tests are broken

```bash
python manage.py test webatds.tests.{module}.{test_file}
```

#### 8.7 Document Implementation

Write implementation notes to: `{problem_name}_T{ticket_id}_implementation.md`

```markdown
# T1.2 Implementation Summary

## Changes Made
- file1.py: Added X method for Y
- file2.py: Modified Z to support W

## Variances from Plan
- Changed approach from A to B because [reason]

## Notes
- Important consideration for future work
- Known limitation

## Tests Added
- test_feature_does_x
- test_feature_handles_edge_case
```

#### 8.8 Update Ticket Status

In `{problem_name}_tickets.json`, update:
```json
"completion_status": "completed"
```

#### 8.9 Commit

```bash
git add [specific files]
git commit -m "$(cat <<'EOF'
T1.2: [Concise description of changes]

- Detail 1
- Detail 2

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

#### 8.10 Next Ticket

Move to the next ticket and repeat from step 8.1.

---

## Completion

After all tickets are complete:

1. Verify all ticket statuses are `completed`
2. Run full test suite for affected modules
3. Create PR following standard process

```bash
gh pr create --title "[Problem Name]" --body "$(cat <<'EOF'
## Summary
[Brief description of what this PR delivers]

## Solution Document
See: {problem_name}_solution.md

## Tickets Completed
- T1.1: [Title]
- T1.2: [Title]
- T2.1: [Title]

## Test Plan
- [ ] Unit tests pass
- [ ] Manual verification of [key flows]

Generated with Claude Code
EOF
)"
```
