# NexusFlow — Test Guide (Simple Version)

It gives you the checks that catch real problems,
in plain language, without the full case matrix.

Do the **Dev** section on your own machine. Do the **Production** section after a deploy — it is
non-destructive and takes about five minutes.

> **Two words you'll see:** *dev* means your machine with throwaway data. *Production* (or *prod*)
> means the real running system with real data. The same checks apply, but in production you never
> delete anything you didn't create.

---

## Before you start

You need NexusFlow running. If it isn't, follow `build-guide.md` first.

Set two shortcuts so the commands below are shorter:

```bash
export API=http://localhost:8000
export KEY=              # put your API key here, or leave empty if auth is off

# A tiny wrapper so you never forget the key. An empty key is harmless when auth is off.
c() { curl -s -H "x-api-key: $KEY" "$@"; }
```

Every command below uses `c` instead of `curl -s`. If you'd rather type `curl -s` yourself, just
remember to add `-H "x-api-key: $KEY"` whenever NexusFlow has a key configured.

---

## Part 1 — Dev checks

### 1. Is it alive?

```bash
c $API/healthz
```

Expect `{"status":"ok"}`.

If you get `500`, the app is running but the database isn't reachable. Check `docker ps`.

### 2. Run the automated tests

```bash
python -m pytest -q
```

Expect `33 passed`. This is your main safety net — if this is green, the core behaviour works.

### 3. Create, change, and read something

This walks through the four things the app does. Run it as one block:

```bash
# create
ID=$(c -X POST $API/api/v1/resources \
  -H 'content-type: application/json' \
  -d '{"type":"qa","name":"qa-tmp-01","status":"active","tags":["qa"]}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

echo "created: $ID"

# read it back
c $API/api/v1/resources/$ID | python3 -m json.tool

# change it — note "version": 1
c -X PATCH $API/api/v1/resources/$ID \
  -H 'content-type: application/json' \
  -d '{"version":1,"status":"retired"}' | python3 -m json.tool

# delete it
c -o /dev/null -w 'delete: %{http_code}\n' -X DELETE $API/api/v1/resources/$ID
```

What to look for:

- The **create** returns `"version": 1`.
- The **update** returns `"version": 2` and `"status": "retired"`. The version number going up is
  how the app prevents two people overwriting each other's changes.
- The **delete** prints `204`. A `204` means "done, nothing to say".

### 4. The safety check: stale updates are refused

This is the most important behaviour to confirm. Two people edit the same record; the second one
must be rejected rather than silently overwriting the first.

```bash
ID=$(c -X POST $API/api/v1/resources \
  -H 'content-type: application/json' \
  -d '{"type":"qa","name":"qa-tmp-02"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

# pretend someone else already edited it — send an old version number
c -o /dev/null -w 'stale update: %{http_code}\n' -X PATCH $API/api/v1/resources/$ID \
  -H 'content-type: application/json' \
  -d '{"version":99,"status":"retired"}'

c -o /dev/null -X DELETE $API/api/v1/resources/$ID
```

Expect `stale update: 409`. A `409` means "conflict — your copy is out of date".

### 5. The audit trail records changes

NexusFlow writes a permanent diary of every change. Let's look at it:

```bash
ID=$(c -X POST $API/api/v1/resources \
  -H 'content-type: application/json' \
  -d '{"type":"qa","name":"qa-tmp-03","status":"active"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

c -X PATCH $API/api/v1/resources/$ID \
  -H 'content-type: application/json' -H 'x-actor: alice' \
  -d '{"version":1,"status":"retired"}' > /dev/null

c $API/api/v1/resources/$ID/history | python3 -m json.tool
```

You should see **two entries**, newest first:

1. An `update`, with `"actor": "alice"`, showing `status` changed from `active` to `retired`.
2. A `create`, showing the original values.

The "changed from X to Y" detail is called the **delta**. It's computed by the database, not the
app — which is why it can't drift from reality.

### 6. The diary cannot be edited

The whole point of an audit log is that nobody can rewrite history. Prove it directly:

```bash
psql "postgresql://nxflow:nxflow@localhost:5432/nxflow" \
  -c "UPDATE resource_history SET actor = 'mallory';"
```

Expect an error containing `append-only`. The same happens with `DELETE FROM resource_history`.

This is enforced **inside the database**, so it holds even if someone bypasses the app entirely.

### 7. Search works

Create three records with different statuses, then search:

```bash
for n in a b c; do
  c -o /dev/null -X POST $API/api/v1/resources \
    -H 'content-type: application/json' \
    -d "{\"type\":\"qa\",\"name\":\"qa-s-$n\",\"status\":\"active\",\"tags\":[\"qa\"]}"
done

c "$API/api/v1/resources?q=status:active" \
  | python3 -c 'import sys,json; print("found:", json.load(sys.stdin)["total"])'

c "$API/api/v1/resources?q=bogus:x" -o /dev/null -w 'bad query: %{http_code}\n'
```

Expect `found: 3` (or more, if you have other active records) and `bad query: 422`. A `422` means
"your query didn't make sense" — the app rejects unknown search words instead of guessing.

### 8. Authentication — test both states

This is the one people get wrong, because **auth only applies if you set a key**.

With `NXFLOW_API_KEY` **empty** (in `.env`), restart the app, then:

```bash
curl -s -o /dev/null -w 'no key needed: %{http_code}\n' $API/api/v1/resources
```

Expect `200`. No key is required.

Now put a key in `.env`, restart the app, and:

```bash
curl -s -o /dev/null -w 'no key sent:   %{http_code}\n' $API/api/v1/resources
curl -s -o /dev/null -w 'wrong key:     %{http_code}\n' -H 'x-api-key: nope' $API/api/v1/resources
curl -s -o /dev/null -w 'right key:     %{http_code}\n' -H "x-api-key: $KEY" $API/api/v1/resources
curl -s -o /dev/null -w 'healthz:       %{http_code}\n' $API/healthz
```

Expect `401`, `401`, `200`, `200`.

Note the last line: the health check stays public even with a key set. That's intentional — your
monitoring tools need to reach it without credentials.

---

## Part 2 — Production checks

Do these after every deploy. None of them change data.

### 1. Auth is actually turned on  ← the big one

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://YOUR-PROD-HOST/api/v1/resources
```

**Expect `401`.** If you get `200`, the API key is empty and **the entire API is open to anyone**.
Stop and fix that before doing anything else.

### 2. You're not using the default key

The compose file ships with a placeholder key:

```bash
grep NXFLOW_API_KEY deploy/docker-compose.yml
```

If that says `change-me`, it must be replaced in production with something real from your secret
store.

### 3. The container doesn't run as root

```bash
docker ps --format '{{.Names}}' | grep -i nxflow
docker exec <container-name> id -u
```

Expect `10001`. Root is `0`; anything non-zero is good. Running as a non-root user limits the
damage if the app is ever compromised.

### 4. The audit log survives deletion

This is NexusFlow's headline guarantee. A deleted asset's history must remain.

```bash
# delete a record you created, then read its history straight from the database
psql "$PROD_DATABASE_URL" -c \
  "SELECT change_type, recorded_at FROM resource_history
   WHERE resource_id = 'THE-DELETED-ID' ORDER BY id DESC;"
```

You should still see the `create` and `delete` rows.

> **Why not use the API?** The history endpoint returns `404` once a resource is gone. So this
> check has to go through the database directly. That's expected, not a bug.

### 5. Writes outside the app are still recorded

```bash
psql "$PROD_DATABASE_URL" -c \
  "UPDATE resources SET status='active' WHERE name='qa-tmp-prodcheck';"
```

Then read that record's history. You should see a new row with `actor = system`. This proves the
audit log covers changes made by scripts, admins, and future services — not just the API.

### 6. The schema actually matches the code

The automated tests build their tables from the code, **not** from the migration files. That means
a broken migration can pass every test. Check it for real, once per deploy:

```bash
# on a scratch database only — this prints SQL without touching anything
python -m alembic -c api/alembic.ini upgrade head --sql | grep -c '^CREATE'
```

Expect `16`.

---

## Things that are known, not bugs

Don't file these as new issues — they're documented limitations.

| What you might see | Status |
|---|---|
| Importing the same item twice in one batch returns `500` instead of `409` | Known bug. Everything still rolls back; only the status code is wrong. |
| Can't view history of a deleted resource through the API | By design. Query the database directly instead. |
| `x-actor` header lets any caller claim any name | Known. It's a label, not a security check — don't trust it. |
| No rate limiting, no per-user accounts | Not built yet. One shared key only. Put it behind a gateway if you need more. |
| FastAPI's `/docs` page is publicly reachable | Default behaviour, no setting to disable. Block it at the proxy if undesired. |
| Search returns 0 for `attr.power:450` | Should not happen. It means the number was sent as text, or the JSONB indexes are missing. Run Part 2 check 6. |

---

## Quick reference

**Green means go.** A release is safe when:

- [ ] `pytest -q` → 33 passed (dev)
- [ ] `/healthz` → 200 (both)
- [ ] No key in prod → **401** (prod)
- [ ] Create → patch → delete cycle works (both)
- [ ] Stale version → 409 (dev)
- [ ] History shows create + update with a delta (dev)
- [ ] `UPDATE resource_history` is rejected (dev)
- [ ] Migration renders 16 CREATEs (prod)
- [ ] Container runs as uid 10001 (prod)

If any of the bolded production checks fail, don't ship.

---

## Where to go next

- `build-guide.md` — how to get it running in the first place
