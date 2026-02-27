#!/usr/bin/env python

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import quote, unquote, urlparse, urlunparse


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent

COMPOSE_BASE: Final[Path] = PROJECT_ROOT / "compose.yaml"
COMPOSE_DEV: Final[Path] = PROJECT_ROOT / "compose.dev.yaml"
COMPOSE_PROD: Final[Path] = PROJECT_ROOT / "compose.prod.yaml"

ENV_EXAMPLE: Final[Path] = PROJECT_ROOT / ".env.example"
ENV_DEV: Final[Path] = PROJECT_ROOT / ".env"
CONFIG_EXAMPLE: Final[Path] = PROJECT_ROOT / "config.yaml.example"
CONFIG_DEV: Final[Path] = PROJECT_ROOT / "config.yaml"


class AppError(RuntimeError):
    pass


@dataclass(frozen=True)
class Exec:
    podman: str
    compose: str
    uv: str | None


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _require(cmd: str) -> str:
    p = _which(cmd)
    if p is None:
        raise AppError(f"Required executable not found on PATH: {cmd!r}")

    return p


def _detect_exec() -> Exec:
    podman = _require("podman")
    # On Debian, `podman compose` is often provided by podman-compose anyway,
    # but the real, common entrypoint is `podman-compose`.
    compose = _which("podman-compose") or "podman compose"
    uv = _which("uv")

    return Exec(podman=podman, compose=compose, uv=uv)


def _run(
    argv: list[str],
    *,
    cwd: Path = PROJECT_ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> None:
    pretty = shlex.join(argv)
    print(f"[run] {pretty}")
    subprocess.run(argv, cwd=str(cwd), env=env, check=check)


def _parse_env_file(path: Path) -> dict[str, str]:
    """
    Minimal .env parser:
    - ignores blank lines and lines starting with '#'
    - parses KEY=VALUE
    - strips surrounding single/double quotes from VALUE
    """

    if not path.exists():
        return {}

    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip()

        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]

        if key:
            out[key] = val

    return out


def _effective_env(*, env_file: Path | None) -> dict[str, str]:
    """
    Merge env sources with the priority OS env > env_file
    """

    merged: dict[str, str] = {}
    if env_file is not None:
        merged.update(_parse_env_file(env_file))
    merged.update(os.environ)  # OS env overrides

    return merged


def _build_netloc(
    *, username: str | None, password: str | None, host: str, port: int | None
) -> str:
    """
    Re-encode user/pass safely for the URL
    """

    userinfo = ""
    if username:
        userinfo = quote(username, safe="")
        if password is not None:
            userinfo += f":{quote(password, safe='')}"
        userinfo += "@"

    hostport = host
    if port is not None:
        hostport = f"{host}:{port}"

    return f"{userinfo}{hostport}"


def _normalize_env_for_host(env: dict[str, str]) -> dict[str, str]:
    """
    Rewrite db -> 127.0.0.1 and cache -> 127.0.0.1
    for running Django on the host.
    """
    out = dict(env)

    db_url = out.get("DATABASE__URL")
    if db_url:
        p = urlparse(db_url)
        if p.hostname == "db":
            out["DATABASE__URL"] = _rewrite_url_host(db_url, new_host="127.0.0.1")
            print("[info] Rewrote DATABASE__URL host db -> 127.0.0.1 for host commands")

    redis_url = out.get("REDIS__URL")
    if redis_url:
        p = urlparse(redis_url)
        if p.hostname == "cache":
            out["REDIS__URL"] = _rewrite_url_host(redis_url, new_host="127.0.0.1")
            print("[info] Rewrote REDIS__URL host cache -> 127.0.0.1 for host commands")

    return out


def _normalize_env_for_compose(env: dict[str, str]) -> dict[str, str]:
    """
    Rewrite localhost/127.0.0.1 -> db/cache
    for running inside the container network.
    """

    out = dict(env)

    db_url = out.get("DATABASE__URL")
    if db_url:
        p = urlparse(db_url)
        if p.hostname in {"127.0.0.1", "localhost"}:
            out["DATABASE__URL"] = _rewrite_url_host(db_url, new_host="db")
            print(
                "[info] Rewrote DATABASE__URL host localhost -> db for container runs"
            )

    redis_url = out.get("REDIS__URL")
    if redis_url:
        p = urlparse(redis_url)
        if p.hostname in {"127.0.0.1", "localhost"}:
            out["REDIS__URL"] = _rewrite_url_host(redis_url, new_host="cache")
            print(
                "[info] Rewrote REDIS__URL host localhost -> cache for container runs"
            )

    return out


def _rewrite_url_host(url: str, *, new_host: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        return url

    netloc = _build_netloc(
        username=parsed.username,
        password=parsed.password,
        host=new_host,
        port=parsed.port,
    )
    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def _derive_postgres_env(env: dict[str, str]) -> dict[str, str]:
    """
    If POSTGRES_* variables are absent, derive them from DATABASE__URL.
    """

    db_url = env.get("DATABASE__URL")
    if not db_url:
        return env

    parsed = urlparse(db_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return env

    # path is "/dbname"
    db_name = parsed.path.lstrip("/") if parsed.path else ""
    user = unquote(parsed.username) if parsed.username else ""
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname or ""
    port = str(parsed.port) if parsed.port is not None else ""

    derived: dict[str, str] = {}
    if "POSTGRES_DB" not in env and db_name:
        derived["POSTGRES_DB"] = db_name
    if "POSTGRES_USER" not in env and user:
        derived["POSTGRES_USER"] = user
    if "POSTGRES_PASSWORD" not in env and password:
        derived["POSTGRES_PASSWORD"] = password
    if "POSTGRES_HOST" not in env and host:
        derived["POSTGRES_HOST"] = host
    if "POSTGRES_PORT" not in env and port:
        derived["POSTGRES_PORT"] = port

    if not derived:
        return env

    # Do not print secrets; just say what we derived.
    safe_keys = ", ".join(sorted(derived.keys()))
    print(f"[info] Derived from DATABASE__URL: {safe_keys}")

    out = dict(env)
    out.update(derived)

    return out


def _compose_argv(exec_: Exec, *, mode: str, args: list[str]) -> list[str]:
    files = [COMPOSE_BASE]
    if mode == "dev":
        files.append(COMPOSE_DEV)
    elif mode == "prod":
        files.append(COMPOSE_PROD)
    else:
        raise AppError(f"Unknown mode: {mode!r}")

    for f in files:
        if not f.exists():
            raise AppError(f"Compose file missing: {f}")

    if exec_.compose == "podman compose":
        argv = ["podman", "compose"]
    else:
        argv = [exec_.compose]

    for f in files:
        argv += ["-f", str(f)]

    argv += args

    return argv


def _warn_localhost_db_url_if_starting_backend(
    env: dict[str, str], *, starting_backend: bool
) -> None:
    if not starting_backend:
        return

    db_url = env.get("DATABASE__URL", "")
    if "@127.0.0.1" in db_url or "@localhost" in db_url:
        print(
            "[warn] DATABASE__URL points to localhost, but you are starting the backend container.\n"
            "       Inside containers, localhost refers to the container itself.\n"
            "       Use a URL with host 'db' (e.g. postgres://user:pass@db:5432/name) for container runs."
        )


def cmd_init(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()
    if exec_.uv is None:
        raise AppError(
            "uv is required for init/dev workflows but was not found on PATH."
        )

    # Copy templates if missing
    if ns.create_files:
        if ENV_EXAMPLE.exists() and not ENV_DEV.exists():
            ENV_DEV.write_text(
                ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            print("[info] Created .env from .env.example (edit secrets as needed).")
        if CONFIG_EXAMPLE.exists() and not CONFIG_DEV.exists():
            CONFIG_DEV.write_text(
                CONFIG_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            print(
                "[info] Created config.yaml from config.yaml.example (edit as needed)."
            )

    # Create venv + sync deps
    if ns.sync:
        _run([exec_.uv, "venv", ".venv"])
        _run([exec_.uv, "sync", "--all-groups"])
        if ns.install_prek:
            _run([exec_.uv, "run", "prek", "install"])


def cmd_infra(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()

    env_file = ENV_DEV if ns.env_file is None else Path(ns.env_file)
    env = _effective_env(env_file=env_file)
    env = _normalize_env_for_compose(env)
    env = _derive_postgres_env(env)

    action = ns.action
    if action == "down":
        # 'down' is destructive in compose-land; for dev infra we want non-destructive.
        print(
            "[info] 'infra down' is treated as 'infra stop' (keeps DB volume). Use 'infra destroy' for a fresh DB."
        )
        action = "stop"

    elif action == "up":
        argv = _compose_argv(exec_, mode="dev", args=["up", "-d", "db", "cache"])
        _run(argv, env=env)

    elif action == "stop":
        argv = _compose_argv(exec_, mode="dev", args=["stop", "db", "cache"])
        _run(argv, env=env)

    elif action == "start":
        # Start existing containers; if they don't exist yet, fall back to up.
        argv = _compose_argv(exec_, mode="dev", args=["start", "db", "cache"])
        try:
            _run(argv, env=env)
        except subprocess.CalledProcessError:
            argv = _compose_argv(exec_, mode="dev", args=["up", "-d", "db", "cache"])
            _run(argv, env=env)

    elif action == "restart":
        # Restart existing containers; if they don't exist yet, fall back to up.
        argv = _compose_argv(exec_, mode="dev", args=["restart", "db", "cache"])
        try:
            _run(argv, env=env)
        except subprocess.CalledProcessError:
            argv = _compose_argv(exec_, mode="dev", args=["up", "-d", "db", "cache"])
            _run(argv, env=env)

    elif action == "destroy":
        # Full teardown (may result in a fresh DB depending on podman-compose behavior/config).
        argv = _compose_argv(exec_, mode="dev", args=["down"])
        _run(argv, env=env)

    elif action == "ps":
        argv = _compose_argv(exec_, mode="dev", args=["ps"])
        _run(argv, env=env)

    else:
        raise AppError(f"Unknown infra action: {ns.action!r}")


def _uv_run_manage(exec_: Exec, args: list[str], *, env_file: Path | None) -> None:
    if exec_.uv is None:
        raise AppError(
            "uv is required for host Django commands but was not found on PATH."
        )

    env = _effective_env(env_file=env_file)
    env = _normalize_env_for_host(env)
    env = _derive_postgres_env(env)
    _run([exec_.uv, "run", "django_manage.py", *args], env=env)


def _uv_run_pytest(
    exec_: Exec, pytest_args: list[str], *, env_file: Path | None
) -> None:
    if exec_.uv is None:
        raise AppError("uv is required for host tests but was not found on PATH.")

    env = _effective_env(env_file=env_file)
    env = _normalize_env_for_host(env)
    env = _derive_postgres_env(env)
    _run([exec_.uv, "run", "pytest", *pytest_args], env=env)


def cmd_django(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()
    env_file = ENV_DEV if ns.env_file is None else Path(ns.env_file)

    match ns.action:
        case "migrate":
            _uv_run_manage(exec_, ["migrate"], env_file=env_file)
        case "makemigrations":
            _uv_run_manage(exec_, ["makemigrations"], env_file=env_file)
        case "shell":
            _uv_run_manage(exec_, ["shell"], env_file=env_file)
        case "createsuperuser":
            _uv_run_manage(exec_, ["createsuperuser"], env_file=env_file)
        case _:
            raise AppError(f"Unknown django action: {ns.action!r}")


def cmd_test(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()
    env_file = ENV_DEV if ns.env_file is None else Path(ns.env_file)

    pytest_args = list(ns.pytest_args)
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    _uv_run_pytest(exec_, pytest_args, env_file=env_file)


def cmd_dev(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()
    env_file = ENV_DEV if ns.env_file is None else Path(ns.env_file)

    if ns.infra:
        cmd_infra(argparse.Namespace(action="up", env_file=str(env_file)))

    if ns.migrate:
        cmd_django(argparse.Namespace(action="migrate", env_file=str(env_file)))

    if exec_.uv is None:
        raise AppError("uv is required for dev server but was not found on PATH.")

    _uv_run_manage(exec_, ["runserver", ns.addr], env_file=env_file)


def cmd_hooks(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()
    if exec_.uv is None:
        raise AppError("uv is required to run prek but was not found on PATH.")

    _run([exec_.uv, "run", "prek", "-a"])


def cmd_image(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()
    tag = ns.tag
    _run(
        [exec_.podman, "build", "-f", "Containerfile", "-t", tag, "."], cwd=PROJECT_ROOT
    )


def cmd_stack(ns: argparse.Namespace) -> None:
    exec_ = _detect_exec()

    env_file: Path | None
    if ns.env_file is None:
        env_file = ENV_DEV if ns.mode == "dev" else None
    else:
        env_file = Path(ns.env_file)

    env = _effective_env(env_file=env_file)
    env = _normalize_env_for_compose(env)
    env = _derive_postgres_env(env)

    starting_backend = ns.action in {"up", "restart"} and not ns.only_infra
    _warn_localhost_db_url_if_starting_backend(env, starting_backend=starting_backend)

    if ns.action == "up":
        args = ["up", "-d"]
        if ns.build:
            args.append("--build")
        if ns.only_infra:
            args += ["db", "cache"]
        argv = _compose_argv(exec_, mode=ns.mode, args=args)
        _run(argv, env=env)

    elif ns.action == "down":
        argv = _compose_argv(exec_, mode=ns.mode, args=["down"])
        _run(argv, env=env)

    elif ns.action == "migrate":
        argv = _compose_argv(exec_, mode=ns.mode, args=["run", "--rm", "migrate"])
        _run(argv, env=env)

    elif ns.action == "ps":
        argv = _compose_argv(exec_, mode=ns.mode, args=["ps"])
        _run(argv, env=env)

    elif ns.action == "logs":
        argv = _compose_argv(exec_, mode=ns.mode, args=["logs", "-f"])
        _run(argv, env=env, check=False)

    else:
        raise AppError(f"Unknown stack action: {ns.action!r}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run.py", description="Project management utility (dev/prod)."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser(
        "init", help="Bootstrap local dev environment (.venv, deps, hooks, templates)."
    )
    p_init.add_argument(
        "--no-sync", dest="sync", action="store_false", help="Skip uv venv/sync."
    )
    p_init.add_argument(
        "--no-prek",
        dest="install_prek",
        action="store_false",
        help="Skip prek install.",
    )
    p_init.add_argument(
        "--no-create-files",
        dest="create_files",
        action="store_false",
        help="Skip copying example files.",
    )
    p_init.set_defaults(sync=True, install_prek=True, create_files=True, func=cmd_init)

    p_infra = sub.add_parser(
        "infra", help="Manage dev infra containers (db/cache only)."
    )
    p_infra.add_argument(
        "action", choices=["up", "start", "stop", "restart", "down", "destroy", "ps"]
    )
    p_infra.add_argument(
        "--env-file",
        default=None,
        help="Env file for substitution/derivation (default: .env).",
    )
    p_infra.set_defaults(func=cmd_infra)

    p_dj = sub.add_parser(
        "django", help="Run Django management commands on host (via uv)."
    )
    p_dj.add_argument(
        "action", choices=["migrate", "makemigrations", "shell", "createsuperuser"]
    )
    p_dj.add_argument(
        "--env-file", default=None, help="Env file used for Django (default: .env)."
    )
    p_dj.set_defaults(func=cmd_django)

    p_test = sub.add_parser(
        "test",
        help="Run pytest on host (via uv) with host env normalization.",
    )
    p_test.add_argument(
        "--env-file", default=None, help="Env file used for tests (default: .env)."
    )
    p_test.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to pytest. Use '--' before pytest flags.",
    )
    p_test.set_defaults(func=cmd_test)

    p_dev = sub.add_parser(
        "dev",
        help="Run Django dev server on host (optionally start infra and migrate).",
    )
    p_dev.add_argument("--addr", default="127.0.0.1:8000")
    p_dev.add_argument("--no-infra", dest="infra", action="store_false")
    p_dev.add_argument("--no-migrate", dest="migrate", action="store_false")
    p_dev.add_argument(
        "--env-file", default=None, help="Env file used for Django (default: .env)."
    )
    p_dev.set_defaults(infra=True, migrate=True, func=cmd_dev)

    p_hooks = sub.add_parser("hooks", help="Run all prek hooks on all files.")
    p_hooks.set_defaults(func=cmd_hooks)

    p_img = sub.add_parser("image", help="Container image operations.")
    img_sub = p_img.add_subparsers(dest="action", required=True)
    p_build = img_sub.add_parser("build", help="Build the backend container image.")
    p_build.add_argument("--tag", default="coursereview-backend")
    p_build.set_defaults(func=cmd_image)

    p_stack = sub.add_parser("stack", help="Manage full container stack (dev/prod).")
    p_stack.add_argument("action", choices=["up", "down", "migrate", "ps", "logs"])
    p_stack.add_argument("--mode", choices=["dev", "prod"], default="dev")
    p_stack.add_argument(
        "--build",
        action="store_true",
        help="Build images when bringing up the stack (dev only usually).",
    )
    p_stack.add_argument(
        "--only-infra",
        action="store_true",
        help="Only start db/cache (ignore backend).",
    )
    p_stack.add_argument(
        "--env-file",
        default=None,
        help="Env file to load into the *compose process* for interpolation/derivation "
        "(dev default: .env; prod default: none).",
    )
    p_stack.set_defaults(func=cmd_stack)

    return p


def main(argv: list[str]) -> int:
    try:
        ns = _build_parser().parse_args(argv)
        ns.func(ns)
        return 0
    except AppError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        return e.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
