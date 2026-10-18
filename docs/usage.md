# Setup and Operations

This project has:

- a Django backend
- a separate frontend repo deployed to Cloudflare Pages

The backend does **not** build or serve the frontend app.
It only serves the API and Django admin.

## Tech stack

- Python 3.14
- Django 6
- PostgreSQL 18
- Valkey 9
- Podman
- uv
- ruff
- ty

## Prerequisites

Install:

- `uv`
- `podman`
- `podman-compose` (required by `podman compose`)

## Repository setup

```bash
git clone git@github.com:Tech-JI/CourseReview.git
cd CourseReview
./run.py init
```

`./run.py init` will:

- create `.venv`
- install dependencies
- install hooks
- create `.env` from `.env.example` if missing
- create `config.yaml` from `config.yaml.example` if missing

Then edit:

- `.env`
- `config.yaml`

See `docs/config.md` for details.

## Local development

Recommended workflow:

- run Postgres and Valkey in containers
- run Django on the host

Start everything:

```bash
./run.py dev
```

This will:

- start `db` and `cache`
- run migrations
- start Django at `127.0.0.1:8000`

### Common commands

- Start only infra:

  ```bash
  ./run.py infra up
  ```

- Stop infra:

  ```bash
  ./run.py infra stop
  ```

- Destroy infra:

  ```bash
  ./run.py infra destroy
  ```

- Run migrations:

  ```bash
  ./run.py django migrate
  ```

- Create migrations:

  ```bash
  ./run.py django makemigrations
  ```

- Create superuser:

  ```bash
  ./run.py django createsuperuser
  ```

- Open Django shell:

  ```bash
  ./run.py django shell
  ```

- Run tests:

  ```bash
  ./run.py test
  ```

- Pass extra pytest arguments:

  ```bash
  ./run.py test -- -q
  ```

### Why `.env` uses `db` and `cache`

Keep this in `.env`:

```env
DATABASE__URL=postgres://admin:test@db:5432/coursereview
REDIS__URL=redis://cache:6379/0
```

This works for both cases:

- Podman Compose uses `db` and `cache` directly
- host-side commands automatically rewrite them to `127.0.0.1`

So do not switch `.env` back and forth between `db` and `localhost`.

## Full container stack

If you want to run the entire backend stack in containers:

```bash
./run.py stack up --mode dev --build
```

Run migrations in the stack:

```bash
./run.py stack migrate --mode dev
```

Inspect services:

```bash
./run.py stack ps --mode dev
./run.py stack logs --mode dev
```

Stop the stack:

```bash
./run.py stack down --mode dev
```

### Service layout

`compose.yaml` defines the shared topology only: `db`, `cache`, `backend`,
`migrate`, `worker`, and `beat`. It has no host-specific bind mounts and no
Cloudflare Tunnel, so both modes start from the same file.

`compose.dev.yaml` and `compose.prod.yaml` add what differs per mode: where the
image comes from (`build` versus the pre-built `coursereview-backend`), which
`env_file` is loaded, and which config or media paths are mounted. `./run.py stack`
always passes `compose.yaml` plus exactly one overlay.

- `worker` and `beat` are separate services in both modes; beat is never folded
  into a worker with `--beat`.
- The Cloudflare Tunnel is defined only in `compose.prod.yaml`, so a dev stack
  does not start `cloudflared`.
- Application containers get configuration through `env_file` and `environment`,
  and mount only `config.yaml`; `.env` is not bind-mounted into a container.
- `LLM__BASE_URL` is interpolated by the compose process, so it can be set in
  the shell environment or in `.env` instead of being edited in the compose files.

## CI testing

Tests are run with `pytest`.

Locally:

```bash
./run.py test
```

In GitHub Actions, the workflow uses service containers for:

- `db`
- `cache`

and runs tests through `./run.py test`, so the same env normalization logic is used in CI and locally.

## Production deployment

Recommended production model:

- build the image in GitHub Actions
- publish it to `ghcr.io`
- pull it on the server with Podman
- run containers with Quadlet
- keep secrets on the server
- deploy by image digest

### Registry

Image name:

```text
ghcr.io/tech-ji/coursereview
```

Use GitHub Actions to publish images manually for now, instead of building on every push.

### Server user

Create a dedicated service user and group:

- user: `coursereview`
- group: `coursereview`

Enable lingering so rootless user services can run without login:

```bash
sudo loginctl enable-linger coursereview
```

### Server config layout

Keep deployment files outside the repository and point Compose at them through
the environment:

- `CR_SECRETS_ENV`: environment file loaded by the backend, worker, beat and
  migrate containers
- `CR_CONFIG_FILE`: non-secret `config.yaml`
- `CR_TUNNEL_ENV`: environment file loaded only by the Cloudflare Tunnel
  container
- `CR_MEDIA_DIR`: host directory mounted at `/app/media`

Set these in an untracked file and pass it with `--env-file`, for example:

```bash
./run.py stack --mode prod --env-file /path/to/compose.env up -d
```

`tunnel.env` holds only `TUNNEL_TOKEN` and is loaded by the Cloudflare Tunnel
container alone. Create it from `tunnel.env.example` in the repo. Keep the token
out of `secrets.env`.

### Quadlet

Use rootless Quadlet units under:

```text
~/.config/containers/systemd/
```

for the `coursereview` user.

Typical units:

- one network
- one Postgres container
- one Valkey container
- one Django (gunicorn) container
- one Celery worker container
- one Celery beat container
- one migration unit (oneshot)
- one Cloudflare Tunnel container, if the site is fronted by a Tunnel

Run beat as its own unit instead of passing `--beat` to a worker. A worker
started with `--beat` makes scheduled tasks and task execution share one process
and one restart domain: restarting or scaling the worker stops the schedule, and
a stuck schedule blocks the worker. Beat needs a writable schedule file, so pass
`--schedule=/tmp/celerybeat-schedule`; the distroless image runs as a non-root
user with an unwritable working directory, and the default `./celerybeat-schedule`
fails with `PermissionError`.

Keep exactly one beat unit. Multiple beat units run every scheduled task more
than once.

### Deployment workflow

Recommended deploy flow:

1. trigger GitHub Actions to publish image
2. get the image digest
3. pull that exact image on the server
4. run migrations using that image
5. restart the backend service

Prefer:

```text
ghcr.io/tech-ji/coursereview@sha256:...
```

over floating tags like `latest`.

### Migrations

Run migrations explicitly during deploy, before restarting the backend.

Do not rely on container startup to hide migration failures.

### Recycled syllabus files

Rejected or deleted syllabus uploads are moved to a `recycle/` directory under
the media root instead of being unlinked, so a mistaken rejection can be
recovered.

Orphans are not kept forever. The beat schedule runs
`purge_recycled_syllabus_files` daily at 04:00, which deletes recycled files
older than `SYLLABUS.RECYCLE_RETENTION_DAYS` (default 30) and, if the directory
is still larger than `SYLLABUS.RECYCLE_MAX_FILES` (default 500), the oldest
entries beyond that count.

The media root must be writable by both the backend and worker containers and
persistent across deploys. In `compose.yaml` this is the `/app/media` volume or
bind mount; the same volume must be mounted into the worker, since uploads are
analyzed and recycled by Celery.

## Static files and Django admin

The Vue frontend is separate, but Django admin still needs Django static assets.

So production still needs a static-files strategy for admin, typically `collectstatic`
