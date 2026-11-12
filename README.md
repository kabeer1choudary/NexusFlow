# NexusFlow
> Open Source Data Center Infrastructure Inventory Management System

## NexusFlow Overview

**NexusFlow** is an open-source, API-first data center infrastructure management (DCIM) and physical asset tracking engine. Built for automation engineers and DevOps teams, NexusFlow provides a GitOps-driven source of truth with lightning-fast querying, automated drift detection, and full resource history auditability.

```text
       [ Git / SCM / Discovered Source ]
                     │
                     ▼
              (SCM Webhooks)
                     │
                     ▼
        [        NexusFlow          ]
                     │
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
[ API Engine/CLI ] ◄─► [ Drift Engine ] ◄─► [ Dynamic Querying ]
```

---

## Core Key Features

### API-First & CLI Driven
* **REST & OpenAPI Native:** Built ground-up with REST/OpenAPI endpoints for seamless programmatic control and integration.
* **CLI Command Suite:** Accompanied by `nxflow`, a terminal-native CLI utility for quick SSH/terminal-based CRUD operations.

### Unified High-Performance Search & Filtering
* **Multi-Parameter Queries:** Fast filter engine allowing instant queries across complex datacenter entities.
* **Tokenized Search Syntax:** Dynamic filtering by status, tags, power thresholds, physical locations, and custom key-value pairs.

### GitOps Integration & SCM Webhooks
* **Native Webhook Receiver:** Built-in endpoints (`/webhooks/scm`) for GitHub, GitLab, and custom CI pipelines.
* **State Synchronization:** Synchronize infrastructural state directly from declared YAML/JSON manifests in your Git repositories.

### Live Drift Detection (`/diff`)
* **State Comparison Engine:** Native engine to highlight discrepancies between the declared state (Git/manifests), actual status (discovered), and recorded state in NexusFlow.
* **Visibility & Alerting:** Provides immediate visibility into unapproved hardware moves, configuration shifts, or unexpected power draw changes.

### Automated Multi-Source Ingestion & Lineage
* **Multi-Source Fetch:** Auto-fetch resource definitions from external automated discovery agents, SCM webhooks, or direct API inputs.
* **Origin Lineage:** Maintains origin metadata attached directly to each entry so you always know where a resource entry originated.

### Immutable Resource History & Audit Trail
* **Granular Audit Logs:** Complete change tracking per asset (capturing who, when, what changed, and delta diffs).
* **Forensic Tracing:** Retains historically logged sources for forensic tracing across the full hardware lifecycle.

### Structured Data Model
* **Predictable Hierarchy:** Clean JSON structure following `resource > attributes > relationships > tags > history`.
* **Extensible Metadata:** Flexible key-value metadata store allowing custom fields (e.g., warranty, custom tags, asset IDs) without requiring database migrations.

### Explicit Relationship Mapping
* **Bidirectional Matrix:** Simple, lightweight mapping matrix to define bidirectional dependencies (e.g., `Server ↔ Rack`, `Server ↔ PDU Port`, `Switch ↔ Patch Panel`).
* **Dependency Graphs:** Enables deep graph traversal to determine downstream impacts of power, switch, or link outages.

### Seamless Import / Export Pipeline
* **Bulk Data Operations:** Native bulk operations supporting JSON, YAML, and CSV files for easily onboarding, updating, or purging asset records.

---

## Getting Started

### Docker Compose (Postgres + API)
```bash
cp .env.example .env          # set NXFLOW_API_KEY
make up                       # builds API, starts Postgres, runs migrations
curl http://localhost:8000/healthz
```

### Local development
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export NXFLOW_DATABASE_URL=postgresql+asyncpg://nxflow:nxflow@localhost:5432/nxflow
python -m alembic -c api/alembic.ini upgrade head
python scripts/seed.py 1000
uvicorn nxflow.main:app --reload
```

### API examples
```bash
API=http://localhost:8000; KEY=change-me

curl -X POST $API/api/v1/resources -H "x-api-key: $KEY" -H 'content-type: application/json' -d '{
  "type":"server","name":"web-01","status":"active","location":"dc1/row3/rack7",
  "tags":["prod","web"],"attributes":{"cpu":32,"power":450},
  "metadata":{"warranty":"2027-01-01","asset_id":"A-1042"},
  "origin":{"source":"manual","ref":null}}'

curl "$API/api/v1/resources?q=status:active%20tag:prod" -H "x-api-key: $KEY"
curl "$API/api/v1/resources/<id>/history" -H "x-api-key: $KEY"
```

Every request except `/healthz` requires `X-API-Key` when `NXFLOW_API_KEY` is set.
PATCH bodies must include the current `version`; a stale version returns `409`.

### Search syntax (MVP)
Whitespace-separated `key:value` predicates, ANDed:
`status:active`, `type:server`, `tag:prod`, `location:dc1/row3*` (prefix),
`attr.power:450`, `meta.asset_id:A-1042`, and free text for `name` matches.

### CLI
```bash
cd cli && cargo build --release
target/release/nxflow config init --url http://localhost:8000 --api-key change-me
nxflow resource create --type server --name web-01 --status active --tag prod --attr power=450
nxflow resource list --q "status:active tag:prod"
nxflow history <resource-id>
nxflow rel add --source <id> --target <id> --type racks
nxflow export > inventory.json
```

### Tests
```bash
make test    # pytest; uses NXFLOW_TEST_DATABASE_URL or testcontainers Postgres
cd cli && cargo test
```

### Deferred to milestone 2
Drift engine (`/diff`), SCM webhooks (`/webhooks/scm`), multi-source ingestion workers,
YAML/CSV import-export, RBAC roles, and relationship graph traversal.