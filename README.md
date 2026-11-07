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