# Solution Planning

After being given a problem, feature, or objective to implement, follow these steps in order.

---

## Step 1: Research

Explore the codebase to understand:

- **Related code** - What modules/services touch this area?
- **Current workflows** - How does the system handle similar operations today?
- **Data models** - What models exist? What are their relationships?
- **Patterns in use** - How have similar problems been solved?

### Research output

Summarize findings before proceeding:
- What exists today
- What patterns are established
- What constraints exist (technical, business, performance)

---

## Step 2: Clarify

Before designing a solution, identify gaps in understanding:

- **Ambiguous requirements** - What exactly should happen in edge cases?
- **Trade-off decisions** - Speed vs accuracy? Flexibility vs simplicity?
- **Scope boundaries** - What's in scope vs out of scope?
- **Integration points** - How should this interact with existing systems?
- **User expectations** - Who uses this? What do they expect?

### How to clarify

Ask the user directly. Group questions logically:

```
Before I proceed, I need clarification on:

**Scope:**
- Should this handle X case or is that out of scope?

**Behavior:**
- When Y happens, should the system do A or B?

**Constraints:**
- Are there performance requirements?
- Does this need to be backwards compatible?
```

Do not proceed to Step 3 until critical questions are answered.

---

## Step 3: Solution Planning

Generate a detailed solution document with:

### Required sections

```markdown
# [Problem Name] Solution Design

## Problem Statement
What problem are we solving? What's the business/user need?

## Current State
How does the system work today? What exists?

## Proposed Solution

### Overview
High-level description (2-3 sentences).

### Components
1. **Component A** - What it does, why it's needed
2. **Component B** - What it does, why it's needed

### Data Model Changes
- New models or fields
- Migration considerations

### API Changes
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/x/` | POST | Description |

### Service Layer
- New services or methods
- Business logic location

### Key Decisions
Document important design decisions and why:
- Decision 1: Chose X over Y because...
- Decision 2: Chose A over B because...

## Edge Cases
How the solution handles:
- Edge case 1
- Edge case 2
- Error scenarios

## Testing Strategy
- What to test
- Key scenarios to cover
```

---

## Step 4: Solution Iterating Loop

Review your solution for weaknesses. Check for:

### Correctness
- [ ] Does it actually solve the stated problem?
- [ ] Are there logical errors or gaps?
- [ ] Does it handle all edge cases identified?

### Consistency
- [ ] Does it follow existing codebase patterns?
- [ ] Does it align with conventions in AGENTS.md files?
- [ ] Will it integrate cleanly with existing code?

### Completeness
- [ ] Are all components specified?
- [ ] Are dependencies identified?
- [ ] Is the testing strategy adequate?

### Consequences
- [ ] Any negative downstream effects?
- [ ] Performance implications?
- [ ] Security considerations?
- [ ] Migration/deployment risks?

### Simplicity
- [ ] Is this the simplest solution that works?
- [ ] Can anything be removed without losing value?
- [ ] Are there unnecessary abstractions?

**Iterate until the solution passes all checks.** If you find issues, fix them and re-review.

---

## Step 5: Solution Confirmation

Present the solution to the user for approval.

### Present clearly

```
## Solution Summary

[2-3 sentence overview]

## Key Design Decisions

1. [Decision]: [Reasoning]
2. [Decision]: [Reasoning]

## Components

1. [Component] - [Purpose]
2. [Component] - [Purpose]

## Trade-offs

- Chose X over Y because Z

## Open Questions (if any)

- Question that needs user input?

---

Does this approach work? Any changes needed before I write it up?
```

### After user confirmation

Once the user approves (or after incorporating their feedback):

1. Check if `docs/solutions/{problem_name}_solution.md` already exists
2. **If file exists, show warning and ask user:**

```
***** WARNING: File already exists *****

docs/solutions/{problem_name}_solution.md already exists.

What do you want to do?
1. Overwrite - Replace existing file
2. Version - Create {problem_name}_solution_v2.md
3. Rename - Specify a new name
4. Cancel - Don't save, review existing file first
```

3. Proceed based on user's choice
4. If file doesn't exist, create: `docs/solutions/{problem_name}_solution.md`
5. Create the `docs/solutions/` directory if it doesn't exist
6. Update the status in the file header to "Confirmed"

**Never silently overwrite.** Always warn and ask when file exists.

### File location

All solution files go in `docs/solutions/` because:
- Not all code is modularized
- Centralized location is easier to find
- Keeps solution documents separate from code

```
project/
├── docs/
│   └── solutions/
│       ├── invoice_permissions_solution.md
│       ├── veson_integration_solution.md
│       └── ...
```

### File naming

- Use snake_case: `bulk_invoice_approval_solution.md`
- Be descriptive: `veson_integration_solution.md`
- Keep it concise: not `the_solution_for_adding_bulk_invoice_approval_feature_solution.md`

---

## Output Checklist

Before considering planning complete:

- [ ] Research findings documented
- [ ] All critical questions answered
- [ ] Solution document covers all required sections
- [ ] Solution reviewed and iterated
- [ ] User has confirmed the approach
- [ ] Solution written to `{problem_name}_solution.md`

---
