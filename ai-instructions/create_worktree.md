# Create Worktree

Invoked as `/create_worktree <branch-name>`. `<branch-name>` is whatever follows the command on the same line - use it verbatim everywhere below.

## Steps

1. Create a git worktree for a feature branch called `<branch-name>` (via `EnterWorktree`, or `git worktree add` if that tool isn't available). The new branch must always be cut from `origin/master` (not local `HEAD`, and not whatever branch the session happens to be on) - if using `EnterWorktree`, this requires `worktree.baseRef` to be `"fresh"` (the default; do not override it to `"head"` for this workflow). The session should then continue working from inside the new worktree for the rest of this task - don't stay in the original checkout.
2. From inside that worktree, run `./scripts/worktree-db.sh <branch-name>`.

This should **not** create any new docker containers or volumes - it works by creating a new Postgres database (`atds_<branch-name>`, sanitized - see the script) inside the existing shared `atds` postgres container, cloned from a frozen `atds_template` database, and applying migrations via a one-off container.

## Known issues on first migrate

- **Missing `baml_client`**: the worktree's bind-mounted checkout shadows the Docker image's generated `webatds/inbound_email/baml_client/` (gitignored, build-time only), so the first `migrate` fails with `ModuleNotFoundError: No module named 'webatds.inbound_email.baml_client'`. Fix: `COMPOSE_PROJECT_NAME=atds docker-compose run --rm django baml-cli generate --from webatds/inbound_email/baml_src`, then re-run migrate.
- **Stale `atds_template` migration history**: `atds_template` is frozen once and never auto-refreshed, so it can carry an abandoned/renamed migration that was later corrected on live `atds` (e.g. `2153_allcostsviewsettings_skip_reviewed_step` vs the current `2153_allcostsviewsettings_enable_step_review`), causing `InconsistentMigrationHistory`. Don't assume this means your changes are wrong - compare the live `atds` DB's `django_migrations` for the same app/migration numbers; if it's clean and ahead while the worktree DB has a differently-named row, it's template drift. If the affected table is empty in the worktree DB, reconcile by hand (alter the column(s) to match the current migration, fix the `django_migrations` row name) and re-run migrate. The systemic fix (periodically refreshing `atds_template` from live `atds`) is out of scope for a single worktree.

## Verify

1. `docker ps` shows no new containers were created (same containers as before the script ran).
2. `docker-compose exec -T postgres psql -U postgres -c "\l"` lists the new `atds_<branch-name>` database.
3. The script's migrate step reported either "No migrations to apply" or applied cleanly.
4. The main running stack is unaffected: `docker-compose exec -T django python manage.py sqlflush` still responds normally.

Report back what you find, including whether the one-time `atds_template` creation step (which briefly terminates other connections to the main `atds` DB - only on its first-ever run) caused any issues.

If anything here goes stale, `scripts/worktree-db.sh` at the repo root is the source of truth for the exact mechanism.
