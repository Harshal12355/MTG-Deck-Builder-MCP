# Coding Conventions

General coding rules that apply to all work in this codebase.

---

## Code Comments

**Write comments only when necessary. Avoid excessive or obvious comments.**

Good code should be self-explanatory through clear naming and structure. Comments should explain **why**, not **what**.

### When to Comment

✅ **DO comment when:**
- Explaining non-obvious business logic or domain rules
- Documenting complex algorithms or calculations
- Clarifying workarounds for bugs or limitations
- Explaining important assumptions or constraints
- Warning about potential issues or edge cases

### When NOT to Comment

❌ **DON'T comment when:**
- The code is self-explanatory
- Repeating what the code obviously does
- Stating the obvious

### Examples

```python
# ❌ BAD - Obvious comment
# Create invoice
invoice = Invoice.objects.create(...)

# ❌ BAD - Redundant comment
# Verify original was auto-approved (not a duplicate, no verification needed)
self.assertEqual(original.status, Invoice.InvoiceStatus.AUTO_APPROVED)

# ✅ GOOD - No comment needed, clear code
self.assertEqual(original.status, Invoice.InvoiceStatus.AUTO_APPROVED)

# ✅ GOOD - Explains WHY, not WHAT
# Refresh invoice to get changes from duplicate detection
matched_invoice.refresh_from_db()

# ✅ GOOD - Explains important business rule
# Auto-approve only if: no verification needed AND not a duplicate
if not needs_verification and not matched_invoice.is_duplicate:
    matched_invoice.status = Invoice.InvoiceStatus.AUTO_APPROVED
```

**Remember:** If you need a comment to explain what the code does, consider refactoring to make the code clearer instead.

---

## Django Migrations

**Use `makemigrations` whenever possible. Only write migrations manually when necessary (e.g., `RunPython` data migrations).**

### Schema Migrations (Auto-Generate)

Always generate schema migrations using Django's management command:

```bash
python manage.py makemigrations
```

- Django's migration generator ensures correct syntax and dependencies
- Manual schema migrations are error-prone and can cause database inconsistencies

### Data Migrations (Manual)

For `RunPython` or custom data migrations that can't be auto-generated, you can write them manually:

1. Generate an empty migration: `python manage.py makemigrations --empty <app_name>`
2. Add your `RunPython` operations to the generated file

### Process

1. Make changes to models in `models.py` files
2. Run `python manage.py makemigrations` to generate migration files
3. Review the generated migration to ensure it matches intended changes
4. Run `python manage.py migrate` to apply migrations to the database

### Backward-compatible migrations

Migrations run before the new code deploys, and the previous Django and Celery tasks keep serving until the rollout finishes. A migration must leave that older code working. CI checks this by running the base branch's tests against the PR's migrated schema (`test-migrations-backward-compatible` in `lint-and-test.yml`).

- **Removing a field** takes two releases. In the first, stop using the field and, in the same migration, make the column nullable (or give it a `db_default`) before removing it from Django's model state only (`SeparateDatabaseAndState`), leaving the column in the database. The new code no longer sets the field, so its inserts would otherwise fail on a `NOT NULL` column. Drop the column in a later release, after the code that reads it is gone.
- **Adding a non-null field** needs `null=True` or a `db_default`, so inserts from the older code still succeed.
- **Renames and type changes** are an add, a backfill, a switch to the new column, then a drop of the old one. Do not rename or retype a column in the same release that starts using it.

---

## API URL Conventions

**Always use singular naming that matches the model name — for both list and detail endpoints.**

```python
# ✅ Correct - singular everywhere
path("carrier/", api_views.CarrierList.as_view(), name="carrier")
path("carrier/<int:pk>/", api_views.CarrierDetail.as_view(), name="carrier")
```

### Examples from Codebase

```python
# ✅ Correct - singular for all endpoints
path("carrier/", api_views.CarrierList.as_view(), name="carrier")
path("carrier/<int:pk>/", api_views.CarrierDetail.as_view(), name="carrier")
path("voyage/", api_views.VoyageList.as_view(), name="voyage")
path("voyage/<int:pk>/", api_views.VoyageDetail.as_view(), name="voyage")
path("barge/", api_views.BargeList.as_view(), name="barge")
path("barge/<int:pk>/", api_views.BargeDetail.as_view(), name="barge")

# ❌ Incorrect - don't use plural or suffixes
path("invoices/", ...)  # Wrong - should be singular
path("invoice/<int:pk>/", ..., name="invoice_detail")  # Wrong - no _detail suffix
path("invoice/", ..., name="invoice_create")  # Wrong - no _create suffix
path("invoice/", ..., name="invoice_list")  # Wrong - no _list suffix
```

---

## Testing

### Use `reverse()` for URLs in Tests

**Always use Django's `reverse()` to resolve URLs in tests, not hardcoded path strings.**

```python
# ✅ Correct - uses reverse
from django.urls import reverse

response = self.client.post(reverse("invoice_allocate", kwargs={"pk": invoice.id}), ...)

# ❌ Incorrect - hardcoded path
response = self.client.post(f"/api/invoice/{invoice.id}/allocate/", ...)
```

This ties tests to URL names, not path strings. If a URL path changes, tests still work.

---

## QuerySet Ordering

**Order queryset method calls in this logical sequence:**

1. `filter()` / `exclude()` — which rows to fetch
2. `annotate()` — computed columns
3. `select_related()` / `prefetch_related()` — eager loading

```python
# ✅ Correct - logical order
qs = (
    CostAllocation.objects.filter(voyage_id=voyage_id, status="ALLOCATED")
    .annotate(description=Subquery(...))
    .select_related("voyage")
)

# ❌ Incorrect - select_related before annotate/filter
qs = (
    CostAllocation.objects.select_related("voyage")
    .filter(voyage_id=voyage_id, status="ALLOCATED")
    .annotate(description=Subquery(...))
)
```

---

## Exception Handling

**Catch specific exceptions. Avoid bare `except Exception` (or bare `except:`) unless no narrower exception type fits and the broad catch is genuinely necessary.**

A bare `except Exception` swallows programming errors (`KeyError`, `AttributeError`, `TypeError`, etc.) right alongside the failure you meant to handle, so real bugs disappear silently instead of surfacing. This has caused production issues in this codebase.

### When a broad catch is acceptable

- At a true isolation boundary where one failure must not take down unrelated work — e.g., a task looping over many independent rows, where one bad row shouldn't stop the rest
- Wrapping third-party/integration code whose failure modes aren't well documented
- In both cases, log with `logger.exception(...)` (or `logger.warning(...)` with details) so the traceback isn't lost, and keep the `try` block as narrow as possible — wrap the risky call, not the whole function

### When NOT to use a broad catch

- To silence an error instead of fixing its root cause
- Around code whose failure modes are known — catch those specific exceptions instead (`Voyage.DoesNotExist`, `KeyError`, `IntegrityError`, etc.)
- Wrapping an entire function/task body "just in case" — this hides bugs unrelated to the one failure you're actually trying to handle

### Examples

```python
# ❌ BAD - wraps the whole task; any bug anywhere in here is swallowed
def create_shipment_request_from_email(inbound_email_id: int) -> None:
    try:
        inbound_email = inbound_email_services.get_inbound_email(inbound_email_id)
        for row in rows:
            ...
    except Exception:
        logger.exception("Failed to create ShipmentRequests from email")


# ✅ GOOD - catch scoped to the risky call, per-row, still logged
for row in rows:
    try:
        with transaction.atomic():
            shipment_request = create_shipment_request_from_data_row(inbound_email, row)
    except Exception:
        logger.warning(
            "Failed to create ShipmentRequest from extraction row",
            extra={"shipment_request_data_id": row.id},
        )
        continue

# ✅ GOOD - specific exception when the failure mode is known
try:
    voyage = Voyage.objects.get(id=voyage_id)
except Voyage.DoesNotExist:
    return None
```

---

## Model State & Relationship Changes

**When you add a new relationship or state field to an existing model (e.g., a self-referencing FK like `merged_into`, a new status value, a "grouped" or "linked" concept), find every other place that mutates that model and explicitly check whether each site needs to account for the new state.**

### How to apply

- Audit every mutation path, not just `ModelName.objects.` calls. That includes:
  - instance `save()` / `delete()`
  - manager and QuerySet writes: `create()`, `update()`, `delete()`, `bulk_create()`, `bulk_update()`, `get_or_create()`, `update_or_create()`
  - related-manager writes, e.g. `line_item.cost_allocations.all().delete()`
  - service-layer helpers and raw SQL that write to the table
- Grep for the model name *and* its reverse relation names (`related_name`), since instance and related-manager calls won't match `ModelName.objects.`
- For each call site found, ask: "if a row is in the new state, does this call need to behave differently?"
- Prefer enforcing the invariant at the queryset/model level (e.g., overriding the custom QuerySet's `delete()`/`update()` and the model's `save()`/`delete()`) over a scattered per-call-site check, so it can't be silently bypassed by a future caller who doesn't know to look for it. Note: Django's `QuerySet.delete()` does **not** call the model instance's overridden `delete()` — a bulk `queryset.delete()` bypasses instance-level guards, so the check usually needs to live on the QuerySet itself (or a DB constraint/trigger) to actually cover every caller.

---

## LLM Calls

**Invoke BAML functions through `call_llm` (`webatds.llm.calls`), never as bare `b.FunctionName(...)`.**

`call_llm` is the single choke point for every LLM call. It saves one `LlmCall` row per call (function, answering client, tokens, duration, success) and feeds `track_llm_usage()`.

```python
from webatds.inbound_email.baml_client import b
from webatds.llm.calls import call_llm, submit_with_context

# ✅ Correct
result = call_llm(b.ExtractBargeDetails, email=content, baml_options=baml_options)
futures = [
    submit_with_context(executor, call_llm, b.ExtractBargeEvents, email=chunk) for chunk in chunks
]

# ❌ Incorrect
result = b.ExtractBargeDetails(email=content, baml_options=baml_options)
futures = [executor.submit(call_llm, b.ExtractBargeEvents, email=chunk) for chunk in chunks]
```

- Pass the bound function (`b.ExtractBargeDetails`), not its name as a string, so arguments stay type-checked and tests can keep patching `b.ExtractBargeDetails`.
- Submit thread-pool work with `submit_with_context`; a plain `executor.submit` loses the email/company attribution and agent usage tracking.
- New entry points that process an inbound email should wrap their work in `inbound_email_llm_context(inbound_email_id)`; elsewhere use `llm_context(company_id=...)`. API requests are attributed to the request's company automatically.
- Tests asserting exact BAML arguments must expect the injected collector, e.g. `baml_options={"collector": ANY}`.
- In production, `LLM_SHADOW_SAMPLE_RATE` of successful calls (except `UNSHADOWED_FUNCTIONS`) are re-run on every client in `SHADOW_CLIENTS` (`webatds.llm.shadow`), in parallel, after the transaction commits, and each challenger's result is saved as its own `ShadowLlmJudge`. Fields that only explain an answer (e.g. `reasoning`) are left out of the comparison; add a new BAML class's explanation fields to `EXPLANATION_FIELDS`. When the outputs differ, the judge sees the rendered task and any PDFs or images, and records whether the primary, the shadow, either, or neither matches the input. The shadow and judge calls are also `LlmCall` rows, with `role` of `shadow` or `judge`, so exclude those roles when reporting production metrics. The comparison row's foreign keys say which call played which part.

---

## General Principles

### Keep Changes Focused

- Only make changes that are directly requested or clearly necessary
- Don't add features, refactor code, or make "improvements" beyond what was asked
- A bug fix doesn't need surrounding code cleaned up
- A simple feature doesn't need extra configurability

### Avoid Over-Engineering

- Don't add error handling for scenarios that can't happen
- Trust internal code and framework guarantees
- Only validate at system boundaries (user input, external APIs)
- Don't create helpers or abstractions for one-time operations
- Don't design for hypothetical future requirements

### Read Before Writing

- Always understand existing code before modifying it
- Follow patterns already established in the codebase
- Check module-specific AGENTS.md files for domain conventions

### Business Logic 

#### Completing voyages
- Anytime a voyage is being completed we should attempt to use the function voyage_matching_helpers.complete_voyage 
- IF that is not feasible we need to ensure we create  Reported Event 'TRIP_END' event.

#### Starting voyages
- Anytime a voyage is being started we should attempt to use the function voyage_matching_helpers.start_voyage 
- IF that is not feasible we need to ensure we create  Reported Event 'TRIP_START' event.