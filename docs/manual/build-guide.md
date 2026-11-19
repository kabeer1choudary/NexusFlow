# NexusFlow — Build Guide (Simple Version)

It gets NexusFlow running on a
fresh **Ubuntu** machine so you can try it and test it.

---

## What you're about to do

Think of NexusFlow as a filing cabinet for data-centre hardware. To use it you need three
things working together:

1. **The program** (a Python web app) — the thing that answers requests.
2. **The database** (PostgreSQL) — the filing cabinet where records are stored.
3. **The web address** (localhost:8000) — how you talk to the program.

We'll set up each one in turn, then check it works.

**Time to first request:** about 10 minutes, most of it waiting for downloads.

---

## Step 1 — Install the tools

First, check your Ubuntu version:

```bash
grep VERSION_ID /etc/os-release
```

That prints something like `VERSION_ID="24.04"`.

**On Ubuntu 24.04** (or newer), Python 3.12 is the default. Run:

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv git make curl
```

**On Ubuntu 22.04**, Python 3.12 isn't in the normal repositories. Add the community PPA first:

```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv git make curl
```

> **What's a PPA?** An extra software source you can enable. Ubuntu 22.04 shipped with Python
> 3.10; this one adds 3.12 alongside it without touching your system Python.

Now install Docker (the easiest way to run the database):

```bash
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
```

> **Important:** the `usermod` line adds you to the Docker group. It only takes effect after you
> **log out and back in**. Until then, `docker` commands fail with a permission error.

Check everything is installed:

```bash
python3.12 --version    # should say Python 3.12.x
git --version
docker --version
docker compose version
```

> **If `docker compose version` fails:** your Ubuntu release may not package
> `docker-compose-v2` under that name. Try `sudo apt install docker-compose-plugin`, or follow
> Docker's official install instructions for your release.

> **Why Python 3.12 exactly?** The project ships a list of exact software versions ("locks")
> built for 3.12. On newer Python (3.13/3.14), some packages have to be compiled from scratch and
> the build can fail. Using 3.12 is the path we know works.

---

## Step 2 — Get the code

```bash
git clone <repo-url> NexusFlow
cd NexusFlow
```

Everything from here on assumes you are inside the `NexusFlow` folder.

---

## Step 3 — Make a private Python toolbox

A **virtual environment** is a private toolbox for this project. Packages you install go in the
toolbox, not into the system Python. That way this project can't break anything else on your
machine, and nothing else can break it.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Your prompt now shows `(.venv)` at the start. That means the toolbox is active.

```bash
python -V     # must print Python 3.12.x
```

If it prints 3.13 or 3.14, delete the toolbox and start again with `python3.12`:

```bash
rm -rf .venv && python3.12 -m venv .venv && source .venv/bin/activate
```

> **Remember:** every new terminal needs `source .venv/bin/activate` again.

---

## Step 4 — Install NexusFlow

One command:

```bash
make install
```

That's it. Behind the scenes it installs the exact versions from the project's lock files and
then installs NexusFlow itself in "editable" mode — meaning any change you make to the code takes
effect immediately, with no reinstall.

> **Don't use `pip install -e ".[dev]"`** even though it looks tempting. That command ignores
> the lock files and grabs whatever is newest, which is how "it worked yesterday" bugs start.

Check it worked:

```bash
python -c "import nxflow; print(nxflow.__version__)"
```

You should see `0.1.0`.

---

## Step 5 — Create the settings file

```bash
cp .env.example .env
```

Open `.env` in a text editor. Leave the first line alone; the third line can stay as-is.

For the **API key** (line 2), you have a choice:

```ini
NXFLOW_API_KEY=
```

- **Empty** = no password required. Easiest while you're learning.
- **Anything else** = every request must send that key in an `x-api-key` header. Like a password.

For local testing, leaving it empty is the friendlier choice.

> **Gotcha:** the program looks for `.env` in the folder you run commands *from*. Always run
> commands from the `NexusFlow` folder.

---

## Step 6 — Start the database

```bash
docker compose -f deploy/docker-compose.yml up -d db
```

The `-d` means "run in the background" so you get your terminal back.

Check it's alive:

```bash
docker ps
```

You should see a container with `postgres` in the name, saying `Up`.

> **Why Docker?** PostgreSQL is a whole database server. Installing it directly means configuring
> users, permissions, and config files. Docker gives you a pre-configured one in a single command.
> It's a sealed box that behaves the same on every machine.

---

## Step 7 — Create the database tables

The database starts out empty. This next command creates all the tables, indexes, and the
"diary" rules that record every change:

```bash
make migrate
```

You should see output mentioning `Running upgrade`. Nothing else required.

> **What's a migration?** A numbered script that builds the database structure. Think of it as
> step-by-step assembly instructions, so any machine ends up with the same layout.

---

## Step 8 — Start the app

```bash
uvicorn nxflow.main:app --reload
```

Leave that terminal running. It should say something like `Uvicorn running on
http://127.0.0.1:8000`.

**Open a second terminal** for the next step, and activate the toolbox there too:

```bash
cd NexusFlow
source .venv/bin/activate
```

---

## Step 9 — Check it works

First, the simplest possible check:

```bash
curl http://localhost:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

That one line proves **both** the app and the database are working.

Now create something:

```bash
curl -X POST http://localhost:8000/api/v1/resources \
  -H 'content-type: application/json' \
  -d '{"type":"server","name":"web-01","status":"active","tags":["prod"]}'
```

You should get back a JSON record with an `id`, `"version": 1`, and timestamps.

And look for it:

```bash
curl 'http://localhost:8000/api/v1/resources?q=status:active'
```

> If you set an API key in Step 5, add `-H 'x-api-key: your-key'` to both commands.

There is also a clickable web page listing every endpoint:
**http://localhost:8000/docs** — open it in a browser.

---

## Step 10 — Run the tests

In your second terminal (toolbox active):

```bash
python -m pytest -q
```

Expected: `33 passed`.

The tests need a throwaway database. By default they start one in Docker automatically.

> **Never** point the tests at a database you care about. They **delete all tables** as part of
> the run. The tests are designed to be destructive; that's normal.

If Docker isn't working, give the tests a database directly instead:

```bash
export NXFLOW_TEST_DATABASE_URL=postgresql+asyncpg://nxflow:nxflow@localhost:5432/nxflow
python -m pytest -q
```

---

## The whole thing, in one block

Once you know what each step does, here it is compressed:

```bash
git clone <repo-url> NexusFlow && cd NexusFlow
python3.12 -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d db
make migrate
uvicorn nxflow.main:app --reload
```

Then, in a second terminal:

```bash
cd NexusFlow && source .venv/bin/activate
curl http://localhost:8000/healthz
python -m pytest -q
```

---

## When something goes wrong

| What you see | What it means | Fix |
|---|---|---|
| `ModuleNotFoundError: nxflow` | You're not in the toolbox, or Step 4 didn't run | `source .venv/bin/activate` then `make install` |
| `permission denied` on `docker` | Group change hasn't taken effect | Log out and back in |
| `connection refused` on migrate | Database isn't running | `docker compose -f deploy/docker-compose.yml up -d db` |
| `401 invalid or missing API key` | You set a key but didn't send it | Add `-H 'x-api-key: your-key'` |
| Tests hang, then mention Docker | Tests can't reach Docker | Use the `NXFLOW_TEST_DATABASE_URL` line in Step 10 |
| `asyncpg` fails to build | Not on Python 3.12 | Recreate the toolbox (Step 3) |
| `/healthz` returns 500 | App is up, database is down | `docker ps` and restart the db container |

---

## To stop everything

```bash
# in the app terminal: Ctrl+C

docker compose -f deploy/docker-compose.yml down
deactivate
```

---

## Where to go next

- `test-guide.md` — what to test once it's running
