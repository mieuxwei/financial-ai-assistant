# Deployment

## macOS local virtualenv note

On the current macOS/Python 3.12.14 workspace, Finder metadata may mark files under the conventional
`.venv` directory as `hidden`. This Python build then reports `Skipping hidden .pth file`, which can
make editable-install console scripts fail with `ModuleNotFoundError` even though tests launched
from the repository still work. This is local environment metadata, not repository corruption.

After an editable install, verify a console command from outside the repository. If verbose Python
startup confirms hidden `.pth` files, clear only the virtualenv metadata with:

```bash
/usr/bin/chflags -R nohidden .venv
```

Do not apply this recursively to the repository, user home, or unrelated directories.

Production deployment remains out of scope for the first M0–M2 iteration. The checked-in `docker-compose.yml` is only a local PostgreSQL option and requires values from an ignored `.env` file.

Before any public deployment:

1. Complete every external item in `m0_security_checklist.md`.
2. Use managed PostgreSQL and a platform secret manager.
3. Run `alembic upgrade head` as a controlled release step.
4. Replace transitional `X-User-ID` with verified LINE webhook identity.
5. Add rate limiting, deletion workflows, monitoring, and private/public environment separation.
6. Run tests, lint, secret scanning, migration checks, and a health-check smoke test.
