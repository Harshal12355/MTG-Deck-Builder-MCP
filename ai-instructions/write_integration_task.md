# Writing Integration Tasks

## Quick Reference

When creating scheduled integration tasks, follow these patterns.

### Pre-Flight Checklist

Before writing a task:
1. Read [conventions.md](./conventions.md) for naming and coding conventions
2. Read the integrations AGENTS.md (`webatds/integrations/AGENTS.md`) for architecture context
3. Identify the target provider and whether its directory already exists
4. Find an existing scheduled task in the same provider as reference

---

## Step 1: Gather Requirements

Before writing any code, ask the user for the following information. Present choices where applicable.

### Task Type

Ask the user:

> Is this a scheduled task or an event-driven task?
> - **Scheduled task** — runs on a timer via Celery Beat
> - **Event-driven task** — reacts to a Django Event via EventRouter

**If event-driven:** Stop and inform the user that this command currently only supports scheduled tasks. Refer them to the integrations `AGENTS.md` for the event-driven pattern.

### Provider Selection

Discover existing providers by listing directories under `webatds/integrations/providers/`. Present them to the user:

> Which provider is this task for?
> - List each existing provider directory (e.g., `veson`, `valero`)
> - **New provider** — will create the directory structure

**If new provider:** Ask for the provider name (lowercase, no spaces). Create the directory structure:
```
integrations/providers/<provider_name>/
├── __init__.py
├── handlers.py
├── tasks.py
├── helpers.py
└── scheduled_tasks.py
```

### Task Details

Ask the user for:

1. **Task name** — The Celery task name (e.g., `sync_veson_invoice_statuses`). Must be unique across the project.
2. **What does it do?** — Brief description of the task's purpose.
3. **Which CompanyIntegrationSetting slug(s) does it need?** — Show the user the existing slug constants from `CompanyIntegrationSetting`:
   - `VESON_VOYAGE_ORDERS` = `"veson-voyage-orders"`
   - `VESON_VOYAGE_INSTRUCTIONS` = `"veson-voyage-instructions"`
   - Or a new slug (will need to be added as a constant)
4. **Schedule interval** — How often should it run? (e.g., every 30 minutes, every hour, daily)
5. **Lock timeout** — How long should the cache lock last? Default: 600 seconds (10 minutes). Use longer for tasks that process large datasets.
6. **Default company_id** — The default company to process (e.g., 420 for EM).

---

## Step 2: Write the Scheduled Task

Add the task to the provider's `scheduled_tasks.py` file. Follow this boilerplate exactly.

### Task Boilerplate

```python
@shared_task(name="<task_name>")
def <task_name>(company_id=<default_company_id>):
    """<Brief description of what the task does>.

    Args:
        company_id: Company ID to process (default: <default_company_id>)
    """
    logger.info(
        f"Integrations: <provider> starting <task_name> for company {company_id}"
    )

    try:
        company = webatds_models.Company.objects.get(id=company_id)
        send_tasks_to_dd("<task_name>", company.name)

        # Get integration settings
        settings = models.CompanyIntegrationSetting.objects.filter(
            company=company,
            slug=models.CompanyIntegrationSetting.<SLUG_CONSTANT>,
        ).first()

        if not settings:
            logger.warning(
                f"Integrations: <provider> no settings found for company {company_id}"
            )
            return {"status": "no_settings"}

        # Acquire lock to prevent concurrent runs
        lock_id = f"<task_name>_{company_id}"
        if not cache.add(lock_id, True, timeout=<lock_timeout>):
            logger.info(
                "Integrations: <provider> <task_name> failed to acquire lock",
                extra={"company_id": company.id},
            )
            return {"status": "lock_failed", "message": "Task already running"}

        try:
            # === BUSINESS LOGIC GOES HERE ===
            # TODO: Implement task logic
            result = {}

            logger.info(
                "Integrations: <provider> <task_name> completed",
                extra={"company_id": company.id, "result": result},
            )
            return {"status": "success", **result}

        except Exception as e:
            logger.exception(
                "Integrations: <provider> <task_name> failed",
                extra={"company_id": company.id, "error": str(e)},
            )
            raise
        finally:
            cache.delete(lock_id)

    except webatds_models.Company.DoesNotExist:
        logger.error(f"Integrations: <provider> company {company_id} does not exist")
        return {"status": "error", "message": "Company not found"}
```

### Required Imports

Ensure these imports are at the top of `scheduled_tasks.py`:

```python
import logging

from celery import shared_task
from django.core.cache import cache

from webatds import models as webatds_models
from webatds.integrations import models
from webatds.integrations.utils import send_tasks_to_dd

logger = logging.getLogger(__name__)
```

Only add imports that the task actually uses. Don't add speculative imports.

---

## Step 3: Register in Celery Beat

Add the schedule entry to `atds/settings/base.py` inside `CELERY_BEAT_SCHEDULE`:

```python
"<task-name-with-dashes>": {
    "task": "<task_name>",
    "schedule": timezone.timedelta(<interval>),
    "options": {"MessageGroupId": "<task_name>"},
},
```

Use the same naming pattern as existing entries:
- Dict key: task name with dashes (e.g., `"sync-veson-voyage-statuses"`)
- `task`: the `name` argument from `@shared_task` (e.g., `"sync_veson_voyage_statuses"`)
- `MessageGroupId`: same as task name (ensures SQS FIFO deduplication)

---

## Patterns to Follow

### Logging Convention

All integration log messages follow the format:
```
"Integrations: <provider> <action description>"
```

Always include structured `extra` data for DataDog:
```python
logger.info(
    "Integrations: veson processed 50 records",
    extra={"company_id": company.id, "record_count": 50},
)
```

### Cache Lock Pattern

Every scheduled task MUST use a cache lock to prevent concurrent execution:

```python
lock_id = f"<task_name>_{company_id}"
if not cache.add(lock_id, True, timeout=<seconds>):
    # Lock not acquired — task is already running
    return {"status": "lock_failed", "message": "Task already running"}

try:
    # ... task logic ...
finally:
    cache.delete(lock_id)  # Always release lock
```

**Lock timeout guidelines:**
- Quick tasks (API call + small DB update): 600 seconds (10 minutes)
- Medium tasks (batch processing): 1200 seconds (20 minutes)
- Long tasks (full data sync): 1800+ seconds

### DataDog Metrics

Always call `send_tasks_to_dd` at the start of the task:

```python
from webatds.integrations.utils import send_tasks_to_dd

send_tasks_to_dd("<task_name>", company.name)
```

### Return Values

Return a dictionary with at least a `status` key:

```python
# Success
return {"status": "success", "processed_count": 10, "updated_count": 3}

# No settings found
return {"status": "no_settings"}

# Lock failed
return {"status": "lock_failed", "message": "Task already running"}

# Error
return {"status": "error", "message": "Company not found"}
```

---

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Forget the cache lock | Always use `cache.add` / `cache.delete` pattern |
| Hardcode company IDs in task body | Use `company_id` parameter with a default |
| Hardcode API credentials | Use `CompanyIntegrationSetting.api_key` and `.api_url` |
| Call external APIs without timeout | Always pass `timeout=` to `requests.get/post` |
| Swallow exceptions silently | Log with `logger.exception()` then re-raise or return error status |
| Put business logic directly in the task function | Extract into helper functions in the same file or `helpers.py` |
| Skip DataDog metrics | Always call `send_tasks_to_dd` for observability |
| Use `print()` for logging | Use the `logger` with structured `extra` data |

---

## Checklist

After creating the task, verify:

- [ ] Task is in `providers/<provider>/scheduled_tasks.py`
- [ ] `@shared_task(name="<unique_name>")` decorator is set
- [ ] Cache lock is implemented with appropriate timeout
- [ ] `send_tasks_to_dd` is called for DataDog metrics
- [ ] `CompanyIntegrationSetting` is fetched (not hardcoded credentials)
- [ ] Structured logging with `extra` dicts is used throughout
- [ ] Celery Beat entry added to `atds/settings/base.py`
- [ ] All external API calls have a `timeout` parameter
- [ ] Task returns a status dictionary
