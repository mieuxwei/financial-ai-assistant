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

## Controlled public web demo

R1A prepares a single fixture-only Streamlit Community Cloud app. It uses
`demo/public_app.py`, requires no FastAPI, database, `.env`, provider key or persistent storage,
and remains `PUBLIC_WEB_DEMO_READY_FOR_MANUAL_DEPLOY` until the user commits/pushes the reviewed
release and authorizes GitHub access. See [public_web_demo_release.md](public_web_demo_release.md).

This controlled release does not unlock current-market inference or production/private portfolio
features.

## Production/private deployment boundary

Production deployment remains out of scope for the completed research portfolio. The checked-in
`docker-compose.yml` is only a local PostgreSQL option and requires values from an ignored `.env`
file. F10, F11A and F11B controlled demonstrations were not deployed.

F11B-2A is an explicit deployment blocker for current-market inference: only 5/23 exact features
passed and adjusted-price training equivalence remains unresolved. Do not lower the tolerance,
silently fall back to stale data or present the controlled fixture as live.

Before any production or private-user deployment:

1. Complete every external item in `m0_security_checklist.md`.
2. Use managed PostgreSQL and a platform secret manager.
3. Run `alembic upgrade head` as a controlled release step.
4. Replace transitional `X-User-ID` with verified LINE webhook/service identity and replay-safe
   backend authentication.
5. Add rate limiting, deletion workflows, monitoring, and private/public environment separation.
6. Run tests, lint, secret scanning, migration checks, and a health-check smoke test.
