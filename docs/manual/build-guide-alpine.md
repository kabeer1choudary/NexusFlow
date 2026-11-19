# Building NexusFlow on Alpine Linux 3.21

Two separate tracks, pick one:

- **[Track A — Alpine 3.21 VM](#track-a--alpine-31-vm-native)** — everything runs natively on the
  guest: venv, Postgres service, uvicorn. Best for development and for running the test suite.
- **[Track B — Alpine 3.21 container image](#track-b--alpine-31-container-image)** — build a
  musl-based API image with the Rust CLI binary baked in, and run it beside a
  `postgres:16.16-alpine` container. Best for deployment and CI parity.

Both were run on `alpine:3.21` (3.21.10) against the committed locks. Both produce the same
`nxflow` CLI binary — Track A builds it with rustup (A6), Track B compiles it in a throwaway
builder stage and copies the static binary into the runtime image (B1, B6).

## Shared facts

| Item | Alpine 3.21 value |
|---|---|
| Python | `python3` → 3.12.16, includes pip + venv |
| Postgres | `postgresql16` → **16.16** (same as CI) |
| `uv` (repo package) | 0.5.31 — **too old**, install 0.13.8 via pip |
| Rust (repo package) | 1.83.0 — **too old** for the CLI, use rustup 1.100.0 |
| Compiler for Python deps | not required |

---

# Track A — Alpine 3.21 VM (native)

Everything installs into a local venv; Postgres runs as an OpenRC service on the guest.

## A1. Packages

```bash
apk add python3 git curl
apk add postgresql16 postgresql16-client
```

`python3 -m venv` already provides pip 25.0.1 — `py3-pip` is not needed. Install `curl`
explicitly: Alpine ships only BusyBox `wget` by default.

## A2. Install from the locks

```bash
git clone <repo-url> NexusFlow && cd NexusFlow

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

python -m pip install -r requirements-dev.lock --require-hashes
python -m pip install -r requirements-build.lock --require-hashes
python -m pip install --no-deps --no-build-isolation -e .
```

Runtime only: swap `requirements-dev.lock` for `requirements.lock`.

```bash
python -c "import nxflow; print(nxflow.__version__, nxflow.__file__)"
# 0.1.0 /home/<you>/NexusFlow/api/src/nxflow/__init__.py
```

`requirements-build.lock` is required only because `--no-build-isolation` forbids pip from
downloading `setuptools` mid-build. It is a pure-Python wheel, so still no compiler.

## A3. Start Postgres as a service

The `postgresql16` package registers an OpenRC service that auto-runs `initdb` on first start
and creates the data and socket directories itself:

```bash
rc-update add postgresql default
rc-service postgresql start
```

> If you are not on a real init system (chroot, container), OpenRC cannot run. Use the manual
> path in [A3b](#a3b-manual-postgres-without-openrc) instead.

Create the app role and databases as the `postgres` system user:

```bash
su postgres -c "psql -c \"CREATE ROLE nxflow LOGIN PASSWORD 'nxflow';\""
su postgres -c "createdb -O nxflow nxflow"
su postgres -c "createdb -O nxflow nxflow_test"
```

`nxflow_test` is for the test suite — the fixture wipes it on every run.

### A3b. Manual Postgres (without OpenRC)

Same result without a service manager. Two directories must exist and be owned by `postgres`;
a missing `/run/postgresql` is the usual cause of `could not create lock file`:

```bash
install -d -m 0750 -o postgres -g postgres /var/lib/postgresql/16/data
install -d -m 0755 -o postgres -g postgres /run/postgresql

su postgres -c "/usr/bin/initdb -A trust --pgdata /var/lib/postgresql/16/data"
su postgres -c "/usr/libexec/postgresql16/pg_ctl \
  -D /var/lib/postgresql/16/data -l /tmp/pg.log \
  -o '-c listen_addresses=127.0.0.1' start"

su postgres -c "psql -c \"CREATE ROLE nxflow LOGIN PASSWORD 'nxflow';\""
su postgres -c "createdb -O nxflow nxflow"
su postgres -c "createdb -O nxflow nxflow_test"
```

`initdb -A trust` is fine for a throwaway VM. On anything shared, drop it and use real
passwords.

Postgres never runs as root; every command above goes through `su postgres`.

## A4. Migrate, seed, run

```bash
cp .env.example .env      # edit NXFLOW_DATABASE_URL if needed

python -m alembic -c api/alembic.ini upgrade head
python scripts/seed.py 200
uvicorn nxflow.main:app --reload --port 8000
```

Smoke test in a second terminal (venv active):

```bash
curl http://localhost:8000/healthz
# {"status":"ok"}

curl -X POST http://localhost:8000/api/v1/resources \
  -H 'content-type: application/json' -H 'x-api-key: change-me' \
  -d '{"type":"server","name":"web-01","status":"active","location":"dc1/row3/rack7","tags":["prod"],"attributes":{"power":450},"metadata":{"asset_id":"A-1042"}}'
```

## A5. Tests

`testcontainers` needs a Docker API socket, which an Alpine VM usually does not have. Point the
suite at the real database — on this track that is the supported path:

```bash
export NXFLOW_TEST_DATABASE_URL=postgresql+asyncpg://nxflow:nxflow@127.0.0.1:5432/nxflow_test
python -m pytest -q          # 33 passed
```

The DB-free subset needs no database at all:

```bash
python -m pytest tests/test_search_unit.py -q    # 11 passed
```

Quality gates: `python -m ruff check api/src tests scripts` and `python -m mypy api/src`.

## A6. CLI — build, configure, use (the one real gotcha)

**Do not use Alpine's `rust`/`cargo` packages.** 3.21 ships Rust **1.83.0**, and the pinned crate
graph needs `edition2024`, stabilized in 1.85:

```text
error: failed to parse manifest at .../idna_adapter-1.2.2/Cargo.toml
Caused by: feature `edition2024` is required
```

Use rustup for 1.100.0. It needs `libgcc` — the musl toolchain fails to relocate
`librustc_driver` without it:

```bash
apk add curl bash ca-certificates libgcc gcc musl-dev
curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.100.0 --profile minimal
export PATH=$HOME/.cargo/bin:$PATH

cd cli
cargo build --release --locked
./target/release/nxflow --version    # nxflow 0.1.0
cargo test --locked                  # 1 passed
```

The musl binary is ~6.0 MB (glibc build ~6.2 MB) and comes out **static-pie linked**, so it runs
on any x86-64 Linux regardless of libc — build here, ship to glibc hosts.

With the API from §A4 running, configure the CLI and exercise it:

```bash
install -m 0755 target/release/nxflow /usr/local/bin/nxflow   # root; else keep ./target/release
nxflow config init --url http://localhost:8000 --api-key change-me
nxflow config show

nxflow resource create --type server --name web-01 --status active --tag prod --attr power=450
nxflow resource list --q "status:active tag:prod"
nxflow search "status:active tag:prod"
nxflow export > inventory.json
```

`config init` writes `~/.config/nxflow/config.toml` (honouring `$XDG_CONFIG_HOME`) and stores the
API key in plaintext. The full command surface — `config init/show`,
`resource list/get/create/update/delete`, `search`, `history`, `rel add/list/rm`, `import`,
`export` — is the same one Track B bakes into the image; B6 has the complete list plus scripting
notes.

## A7. Regenerating locks

Alpine's packaged `uv` is 0.5.31, too old for these files:

```bash
python -m pip install uv==0.13.8      # musllinux wheel, no compiler

uv pip compile pyproject.toml --python-version 3.12 --universal --generate-hashes \
  -o requirements.lock
uv pip compile pyproject.toml --extra dev --python-version 3.12 --universal \
  --generate-hashes -o requirements-dev.lock
```

Regenerating on Alpine reproduces the committed locks byte-for-byte (only the `-o` path in the
header comment differs), so musl and glibc machines agree on the dependency set.

## Fastest path (Track A)

```bash
apk add python3 git curl postgresql16 postgresql16-client
git clone <repo> NexusFlow && cd NexusFlow
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-dev.lock --require-hashes
python -m pip install -r requirements-build.lock --require-hashes
python -m pip install --no-deps --no-build-isolation -e .

rc-update add postgresql default && rc-service postgresql start
su postgres -c "psql -c \"CREATE ROLE nxflow LOGIN PASSWORD 'nxflow';\""
su postgres -c "createdb -O nxflow nxflow"

cp .env.example .env
python -m alembic -c api/alembic.ini upgrade head
python scripts/seed.py 200

# CLI: rustup, not Alpine's rust 1.83 (§A6)
apk add bash ca-certificates libgcc gcc musl-dev
curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.100.0 --profile minimal
export PATH=$HOME/.cargo/bin:$PATH
(cd cli && cargo build --release --locked)
install -m 0755 cli/target/release/nxflow /usr/local/bin/nxflow
nxflow config init --url http://localhost:8000 --api-key change-me
nxflow --version                     # nxflow 0.1.0

uvicorn nxflow.main:app --reload
```

With the API running, drive it from a second terminal — no venv needed, the CLI is a static
binary that reads `~/.config/nxflow/config.toml` written by `config init` above:

```bash
nxflow resource list --limit 5
nxflow search "status:active tag:prod"
nxflow export > inventory.json
```

`install -m 0755` writes to `/usr/local/bin`, so it needs root (the default user on a fresh
Alpine VM). Without root, instead run the binary in place:
`export PATH="$PWD/cli/target/release:$PATH"`.

---

# Track B — Alpine 3.21 container image

Build a musl API image with the Rust CLI baked in, then run it against a Postgres container.
Nothing is installed on the host except a container runtime.

## B1. The Dockerfile

Save as `deploy/api.alpine.Dockerfile` (the existing `deploy/api.Dockerfile` is the Debian one):

```dockerfile
# --- CLI builder: Rust toolchain lives here only, never in the final image ---
FROM alpine:3.21@sha256:bc21487101ae47172509130ee1092cc273a831968d64b617776d1f69c81e42ab AS cli-builder

# Alpine's rust/cargo are 1.83, too old for edition2024 (§A6) — use rustup.
RUN apk add --no-cache curl bash ca-certificates libgcc gcc musl-dev
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.100.0 --profile minimal
ENV PATH=/root/.cargo/bin:$PATH

WORKDIR /build
COPY cli ./cli
RUN cd cli && cargo build --release --locked

# --- Runtime: Python API + the static CLI binary ---
FROM alpine:3.21@sha256:bc21487101ae47172509130ee1092cc273a831968d64b617776d1f69c81e42ab

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH

RUN apk add --no-cache python3 && python3 -m venv /opt/venv

WORKDIR /app
COPY requirements.lock requirements-build.lock ./
RUN pip install --require-hashes -r requirements.lock \
 && pip install --require-hashes -r requirements-build.lock

COPY pyproject.toml ./
COPY api ./api
RUN pip install --no-deps --no-build-isolation .

# Static-pie musl binary from the builder stage — needs no libc on the target.
COPY --from=cli-builder /build/cli/target/release/nxflow /usr/local/bin/nxflow

EXPOSE 8000
RUN adduser --system --uid 10001 --no-create-home nxflow \
 && mkdir -p /home/nxflow && chown nxflow:nxflow /home/nxflow
ENV HOME=/home/nxflow
USER nxflow
```

Notes that differ from the Debian Dockerfile:

- No `gcc`/`musl-dev` in the **runtime** stage — every wheel is prebuilt for musl, and the CLI
  arrives as a static binary. Result is **≈159 MB** (153 MB API + ~6 MB CLI).
- The Rust toolchain is confined to the `cli-builder` stage; the runtime image contains only
  `/usr/local/bin/nxflow`. `COPY cli ./cli` brings `Cargo.toml`, `Cargo.lock` and `src/`, so
  `--locked` is reproducible.
- `ENV HOME=/home/nxflow` gives the CLI's `dirs::config_dir()` a writable target — without it
  `nxflow config init` would fall back to the read-only `/app`.
- `adduser` is BusyBox's, so it takes `--no-create-home`, not Debian's `useradd` flags.
- `python3` is 3.12.16, matching the lock target; no `python:3.12-alpine` base image needed.
- The venv lives at `/opt/venv` and is on `PATH` via `ENV`, so plain `pip`/`uvicorn` work.

Build it from the repo root:

```bash
podman build -f deploy/api.alpine.Dockerfile -t nxflow-api:alpine .
```

## B2. Run the stack

Create a network so the API can resolve the database by name, then start Postgres:

```bash
podman network create nxflow-net

podman run -d --name nxflow-db --network nxflow-net \
  -e POSTGRES_USER=nxflow -e POSTGRES_PASSWORD=nxflow -e POSTGRES_DB=nxflow \
  -v nxflow-pgdata:/var/lib/postgresql/data \
  docker.io/library/postgres:16.16-alpine
```

Wait for it, then start the API. Migrations run inside the container on start:

```bash
until podman exec nxflow-db pg_isready -U nxflow; do sleep 1; done

podman run -d --name nxflow-api --network nxflow-net \
  -e NXFLOW_DATABASE_URL=postgresql+asyncpg://nxflow:nxflow@nxflow-db:5432/nxflow \
  -e NXFLOW_API_KEY=change-me \
  -p 8000:8000 \
  nxflow-api:alpine \
  sh -c "python -m alembic -c api/alembic.ini upgrade head && \
         uvicorn nxflow.main:app --host 0.0.0.0 --port 8000"
```

Use the fully-qualified `docker.io/library/postgres:16.16-alpine` under Podman: short-name
resolution fails without a TTY.

## B3. Verify

```bash
curl http://localhost:8000/healthz
# {"status":"ok"}

curl -X POST http://localhost:8000/api/v1/resources \
  -H 'content-type: application/json' -H 'x-api-key: change-me' \
  -d '{"type":"server","name":"ctr-01","status":"active","location":"dc1/r1/r1","tags":["prod"]}'

podman logs nxflow-api | tail
```

## B4. Compose (optional)

`deploy/docker-compose.yml` points at the Debian image. To use the Alpine one, override the
build and image in your own compose file:

```yaml
services:
  api:
    build:
      context: ..
      dockerfile: deploy/api.alpine.Dockerfile
  db:
    image: docker.io/library/postgres:16.16-alpine
```

Or skip Compose and use the two `podman run` commands from B2. Either way the `cli-builder`
stage runs, so the compose-built image carries `nxflow` too.

On Alpine itself, `podman compose` needs a provider — the wrapper is not a Compose
implementation:

```bash
apk add podman docker-cli-compose      # provides Compose v2.31
podman compose version
```

Without one it fails with `looking up compose provider failed`.

## B5. Tests against the containerized stack

`conftest.py` starts its own throwaway Postgres via testcontainers unless told otherwise. With
the stack running, point it at a test database instead:

```bash
podman exec nxflow-db createdb -U nxflow nxflow_test

export NXFLOW_TEST_DATABASE_URL=postgresql+asyncpg://nxflow:nxflow@127.0.0.1:5432/nxflow_test
python -m pytest -q
```

That needs the repo and a venv **on the host** — the runtime image deliberately has no dev
tools. Alternatively run the suite in a one-off container:

```bash
podman run --rm --network nxflow-net \
  -e NXFLOW_TEST_DATABASE_URL=postgresql+asyncpg://nxflow:nxflow@nxflow-db:5432/nxflow_test \
  -v "$PWD":/src:ro -w /src nxflow-api:alpine \
  sh -c "pip install -r requirements-dev.lock --require-hashes && \
         pip install --no-deps --no-build-isolation -e . && \
         python -m pytest -q"
```

The fixture drops and recreates every table — never point `NXFLOW_TEST_DATABASE_URL` at
`nxflow`, always at `nxflow_test`.

## B6. The CLI inside the image

The `cli-builder` stage compiles `cli/` with the same rustup 1.100.0 toolchain as §A6 and copies
the resulting static binary to `/usr/local/bin/nxflow`. Check it without touching the host:

```bash
podman run --rm nxflow-api:alpine nxflow --version    # nxflow 0.1.0
```

The CLI is an HTTP client, so run it in a one-off container on the same network as the API and
point it at the service name:

```bash
podman run --rm --network nxflow-net nxflow-api:alpine \
  sh -c "nxflow config init --url http://nxflow-api:8000 --api-key change-me && \
         nxflow resource list --limit 5"
```

`HOME=/home/nxflow` is writable, so `config init` writes
`/home/nxflow/.config/nxflow/config.toml`. That file lives and dies with the throwaway
container — mount `-v nxflow-cli:/home/nxflow/.config` to keep it between runs. To drive the
API from the host instead, use `--network host` and `--url http://localhost:8000`:

```bash
podman run --rm --network host nxflow-api:alpine \
  sh -c "nxflow config init --url http://localhost:8000 --api-key change-me && nxflow config show"
```

The full command surface (identical to what §A6 builds; details in `docs/code-guide.md`):

```bash
nxflow config init --url URL --api-key KEY   # writes ~/.config/nxflow/config.toml
nxflow config show

nxflow resource list --q "status:active tag:prod" --limit 50 --offset 0
nxflow resource get <id>
nxflow resource create --type server --name web-01 --status active \
  --tag prod --attr power=450 --meta warranty=2027-01-01
nxflow resource update <id> --version 1 --status retired
nxflow resource delete <id>

nxflow search "status:active tag:prod"       # same endpoint as `resource list --q`
nxflow history <id> --limit 100

nxflow rel add --source <id> --target <id> --type racks --meta slot=3
nxflow rel list <id>
nxflow rel rm <relationship-id>

nxflow import resources.json                 # bulk create from a JSON file
nxflow export --q "type:server" > inventory.json
```

Two behaviours worth knowing when scripting it in a container: every non-2xx response is printed
as `error: HTTP <code>: <body>` on stderr with exit status `1`, and `x-api-key` is only sent
when `config init --api-key` was given a value. The CLI speaks to
`/api/v1/resources`, `/api/v1/relationships`, `/api/v1/import` and `/api/v1/export`, so it needs
the same `NXFLOW_API_KEY` as any other client (§B3, troubleshooting).

---

# Track comparison

| Topic | A — VM (native) | B — Container image |
|---|---|---|
| Host packages | `python3 git curl postgresql16` + CLI deps in §A6 (`bash libgcc gcc musl-dev`) | container runtime only |
| Python env | project-local `.venv` | `/opt/venv` in image, on `PATH` |
| Postgres | OpenRC service, patchable `pg_hba` | `postgres:16.16-alpine`, data in a volume |
| Migrations | on host | on container start |
| Tests | `NXFLOW_TEST_DATABASE_URL` → local DB | same, or a one-off dev container |
| Reload on edit | `uvicorn --reload` | rebuild the image |
| CLI | rustup + `cargo build` (§A6), installed to `/usr/local/bin`, config in `~/.config/nxflow` | compiled in `cli-builder`, binary at `/usr/local/bin/nxflow` (§B6) |
| Result | n/a | ≈159 MB image |
| Best for | development, debugging, test suite | deployment, CI parity |

Both tracks install identical package versions because both read the same hash-pinned locks.

# Troubleshooting

| Symptom | Track | Fix |
|---|---|---|
| `feature edition2024 is required` | A | Alpine's `rust`/`cargo` are 1.83. Install rustup 1.100.0 (§A6). |
| `feature edition2024 is required` during `podman build` | B | The `cli-builder` stage must use rustup, not Alpine's `rust` package — keep the §B1 Dockerfile as written. |
| `nxflow: not found` inside the image | B | Stale image built before the CLI stage existed. Rebuild; the binary is `COPY --from=cli-builder`. |
| `read config ... (run nxflow config init)` from the CLI | both | No config yet. Run `nxflow config init --url ... --api-key ...` in the same shell/container (§A6, §B6); in B the file is per-container, so mount `-v nxflow-cli:/home/nxflow/.config` to keep it. |
| `error: HTTP 401: ...` from `nxflow` | both | The CLI sends `x-api-key` only if `config init --api-key` had a value; it must match `NXFLOW_API_KEY`. |
| `_Unwind_Resume: symbol not found` after rustup | A | `apk add libgcc` — musl needs it for rustc. |
| `could not create lock file "/run/postgresql/..."` | A | `/run/postgresql` missing. Use OpenRC (§A3) or create it as `postgres` (§A3b). |
| Postgres exits immediately when started manually | A | Started as root, or the data dir isn't owned by `postgres`. |
| `curl: not found` | A | Alpine ships BusyBox only. `apk add curl`, or use `wget -qO-`. |
| `uv: unrecognized arguments` | A | Alpine's `uv` is 0.5.x. Install 0.13.8 (§A7). |
| `In --require-hashes mode, all requirements must have their versions pinned` | both | Lock not regenerated after a `pyproject.toml` change, or hand-edited. See §A7. |
| `--no-build-isolation` missing backend | both | `requirements-build.lock` skipped; install it before the `-e .` step. |
| `asyncpg` tries to compile | both | Not on Python 3.12, or `--no-binary` in play. Both defeat the lock's wheels. |
| `401 invalid or missing API key` | both | `NXFLOW_API_KEY` is set. Send `x-api-key`, or **unset** it — an empty value still enables auth. |
| `/healthz` returns 500 | both | App up, DB unreachable — `healthz` runs a real `SELECT 1`. |
| `short-name resolution enforced but cannot prompt without a TTY` | B | Use `docker.io/library/postgres:16.16-alpine`, not `postgres:16.16-alpine`. |
| API container: `socket.gaierror: Name does not resolve` | B | Both containers must share `--network nxflow-net`, and the URL host must match the DB container name. |
| API container exits before serving | B | `podman logs nxflow-api` — usually the DB was not ready for the migration step. |
| `looking up compose provider failed` | B | Install `docker-cli-compose`; `podman compose` has no built-in implementation. |
