# NexusFlow
Open Source Data Center Infrastructure Inventory Management System

## NexusFlow Overview

NexusFlow is an open-source, API-first data center infrastructure management (DCIM) and physical asset tracking engine. Built for automation engineers and DevOps teams, NexusFlow provides a GitOps-driven source of truth with lightning-fast querying, automated drift detection, and full resource history auditability.

         [ Git / SCM / Discovered Source ]
                     │
                     ▼
              (SCM Webhooks)
                     │
                     ▼
        [         NexusFlow          ]
                    ▼
        _____________________________________________
        │                   │                       │
        ▼                   ▼                       ▼
[ API Engine/CLI ] ◄─► [ Drift Engine  ] ◄─► [ Dynamic Querying ]



## Core Key Features

    API-First & CLI Driven

        Built ground-up with REST/OpenAPI endpoints for programmatic control.

        Accompanied by nxflow, a terminal-native CLI utility for quick SSH/terminal-based CRUD operations.

    Unified High-Performance Search & Filtering

        Multi-parameter filter engine allowing instant queries across complex datacenter entities.

        Tokenized search syntax enabling granular filtering by status, tags, power thresholds, physical locations, and custom key-value pairs.

    GitOps Integration & SCM Webhooks

        Built-in webhook receivers (/webhooks/scm) for GitHub, GitLab, and custom CI pipelines.

        Synchronize infrastructural state directly from declared YAML/JSON manifests in your Git repositories.

    Live Drift Detection (/diff)

        Native engine to highlight discrepancies between the declared state (Git/manifests), actual status (discovered), and recorded state in NexusFlow.

        Provides quick visibility into unapproved hardware moves, configuration shifts, or power draw changes.

    Automated Multi-Source Ingestion & Lineage

        Auto-fetch resource definitions from external automated discovery agents, SCM webhooks, or direct API inputs.

        Maintains origin metadata attached directly to the entry so you always know where a resource entry originated.

    Immutable Resource History & Audit Trail

        Complete change tracking per asset (who, when, what changed, and delta diffs).

        Retains historically logged sources for complete forensic tracing across the hardware lifecycle.

    Structured Data Model

        Predictable, predictable JSON representation: resource > attributes > relationships > tags > history.

        Extensible key-value metadata store allowing custom fields (e.g., warranty, custom tags, asset IDs) without database migrations.

    Explicit Relationship Mapping

        Simple, lightweight mapping matrix to define bidirectional dependencies (e.g., Server ↔ Rack, Server ↔ PDU Port, Switch ↔ Patch Panel).

        Allows deep graph traversal to determine downstream impacts of power or link outages.

    Seamless Import / Export Pipeline

        Native bulk operations supporting JSON, YAML, and CSV files for onboarding, updating, or purging asset records.