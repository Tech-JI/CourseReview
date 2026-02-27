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

Recommended:

```text
/etc/coursereview/
  secrets.env
  config.yaml
```

Suggested ownership and permissions:

- directory owned by `root:coursereview`
- `secrets.env` readable by group `coursereview`
- `config.yaml` readable by group `coursereview`

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
- one Django container

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

## Static files and Django admin

The Vue frontend is separate, but Django admin still needs Django static assets.

So production still needs a static-files strategy for admin, typically `collectstatic`
