# MineMeld → Backstage Migration Architecture

## Executive Summary

This document maps MineMeld's threat intelligence processing architecture to a modern Backstage-based implementation. MineMeld was officially archived in March 2023, making migration essential for continued threat intel operations.

## MineMeld Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MINEMELD ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────┐     ┌─────────────┐     ┌──────────┐                         │
│   │ MINERS  │────▶│ PROCESSORS  │────▶│ OUTPUTS  │                         │
│   └─────────┘     └─────────────┘     └──────────┘                         │
│        │                │                   │                              │
│        ▼                ▼                   ▼                              │
│   Fetch from       Aggregate,         Export to                            │
│   external         deduplicate,       firewalls,                           │
│   feeds            filter             SIEMs, TAXII                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| MineMeld Component | Function | Data Flow |
|-------------------|----------|-----------|
| **Miner** | Fetch indicators from external sources | Input only |
| **Processor** | Aggregate, deduplicate, filter indicators | Input → Output |
| **Output** | Transform and export to consumers | Output only |

### Node Types (Prototypes)

**Miners:**
- `stdlib.feedHCgreen` - Hail a TAXII feed
- `stdlib.listIPv4` - Static IP list
- `localdb` - Local database storage
- `taxii.client` - TAXII 1.x/2.x client

**Processors:**
- `stdlib.aggregatorIPv4` - IPv4 deduplication
- `stdlib.aggregatorURL` - URL aggregation
- `stdlib.aggregatorDomain` - Domain aggregation
- `stdlib.feedHCtrigger` - Conditional triggers

**Outputs:**
- `stdlib.EDL` - External Dynamic List (Palo Alto)
- `taxii.server` - TAXII server endpoint
- `stdlib.CSV` - CSV file export
- `stdlib.STIX` - STIX format output

---

## Backstage Migration Mapping

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACKSTAGE THREAT INTEL PLATFORM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    BACKSTAGE FRONTEND                              │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │    │
│   │  │  Workflow   │  │  Feed       │  │  Dashboard  │               │    │
│   │  │  Editor     │  │  Manager    │  │  & Sankey   │               │    │
│   │  │  (WYSIWYG)  │  │  (CRUD)     │  │  Diagrams   │               │    │
│   │  └─────────────┘  └─────────────┘  └─────────────┘               │    │
│   │                     Splunk UI Components                          │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    BACKSTAGE BACKEND                               │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │    │
│   │  │  Workflow   │  │  Feed       │  │  Output     │               │    │
│   │  │  Engine     │  │  Connectors │  │  Adapters   │               │    │
│   │  │  (Miners→   │  │  (TAXII,    │  │  (EDL,      │               │    │
│   │  │  Processors)│  │  REST, CSV) │  │  STIX, HEC) │               │    │
│   │  └─────────────┘  └─────────────┘  └─────────────┘               │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    ▼                                        │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │              EPHEMERAL SPLUNK (Faux Splunk Cloud)                  │    │
│   │         For testing detection rules against generated logs         │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MineMeld → Backstage Entity Mapping

| MineMeld Concept | Backstage Equivalent | Implementation |
|-----------------|---------------------|----------------|
| **Prototype** | Software Template | YAML scaffolder templates |
| **Node** | Component Entity | catalog-info.yaml entries |
| **Graph** | System Entity | Workflow definition |
| **Config** | Entity Annotations | Metadata + TechDocs |
| **Feed User** | Keycloak User + Role | SAML integration |
| **Admin User** | Keycloak Admin Role | RBAC policies |

### Workflow Engine Design

```typescript
// Workflow Node Types (replaces MineMeld prototypes)
interface WorkflowNode {
  id: string;
  type: 'miner' | 'processor' | 'output';
  prototype: string;  // e.g., 'taxii.client', 'aggregator.ipv4'
  config: Record<string, unknown>;
  inputs: string[];   // Node IDs this receives from
  outputs: string[];  // Node IDs this sends to
  position: { x: number; y: number };  // For WYSIWYG editor
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  schedule?: CronExpression;
  status: 'draft' | 'active' | 'paused' | 'error';
}

interface WorkflowEdge {
  id: string;
  source: string;  // Node ID
  target: string;  // Node ID
  filters?: IndicatorFilter[];  // Optional filtering on edge
}
```

---

## Authentication & Authorization

### MineMeld Current State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MINEMELD AUTH (Limited)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Admin User                    Feed User                                   │
│   ──────────                    ─────────                                   │
│   • Basic Auth                  • Basic Auth                                │
│   • Full system access          • Read-only feed access                     │
│   • Local credentials           • Tag-based authorization                   │
│   • No SSO/SAML                 • Per-feed credentials                      │
│                                                                             │
│   LIMITATIONS:                                                              │
│   • No LDAP integration                                                     │
│   • No SSO (GitHub issue #166 - never implemented)                          │
│   • No role-based access control beyond admin/feed                          │
│   • No multi-tenancy                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Backstage + Keycloak Target State

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KEYCLOAK SAML INTEGRATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐          ┌─────────────────┐                         │
│   │    KEYCLOAK     │◀────────▶│   BACKSTAGE     │                         │
│   │                 │   SAML   │                 │                         │
│   │  • Identity     │          │  • Auth Plugin  │                         │
│   │  • Roles        │          │  • Permission   │                         │
│   │  • Groups       │          │    Framework    │                         │
│   └─────────────────┘          └─────────────────┘                         │
│                                                                             │
│   ROLES:                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Platform Admin    │ Full system access, user management            │  │
│   │  Workflow Admin    │ Create/edit workflows, manage feeds            │  │
│   │  Workflow Operator │ Start/stop workflows, view logs               │  │
│   │  Feed Consumer     │ Read-only access to specific feeds            │  │
│   │  Viewer            │ Dashboard and monitoring only                  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   PERMISSIONS:                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  workflow.create   │ Create new threat intel workflows              │  │
│   │  workflow.edit     │ Modify existing workflows                      │  │
│   │  workflow.delete   │ Remove workflows                               │  │
│   │  workflow.execute  │ Start/stop/pause workflows                     │  │
│   │  feed.read         │ Consume indicator feeds                        │  │
│   │  feed.manage       │ Configure feed sources                         │  │
│   │  instance.manage   │ Manage Faux Splunk instances                   │  │
│   │  attack.simulate   │ Run attack simulations                         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

### Indicator Processing Pipeline

```
                           ┌──────────────────┐
                           │  External Feeds  │
                           │  (TAXII, REST,   │
                           │   CSV, STIX)     │
                           └────────┬─────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MINER LAYER                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ TAXII Miner │  │ REST Miner  │  │ CSV Miner   │  │ LocalDB     │       │
│  │ (scheduled) │  │ (webhook)   │  │ (file watch)│  │ (manual)    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PROCESSOR LAYER                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ Deduplication   │  │ Filtering       │  │ Enrichment      │            │
│  │ (by indicator   │  │ (by type, age,  │  │ (add metadata,  │            │
│  │  type + value)  │  │  confidence)    │  │  scoring)       │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OUTPUT LAYER                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐ │
│  │ EDL       │  │ TAXII     │  │ Splunk    │  │ STIX      │  │ Webhook │ │
│  │ (PAN FW)  │  │ Server    │  │ HEC       │  │ Bundle    │  │ (REST)  │ │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
          ┌─────────────────┐             ┌─────────────────┐
          │ Palo Alto FW    │             │ Splunk SIEM     │
          │ (External       │             │ (Threat Intel   │
          │  Dynamic List)  │             │  Correlation)   │
          └─────────────────┘             └─────────────────┘
```

---

## Migration Pain Points Addressed

| MineMeld Limitation | Backstage Solution |
|--------------------|-------------------|
| **No SSO/SAML** | Keycloak SAML integration |
| **No multi-tenancy** | Backstage permission framework + namespaces |
| **Poor scalability** | Kubernetes-native, horizontal scaling |
| **Limited API** | REST + GraphQL API-first design |
| **YAML config only** | WYSIWYG workflow editor + API |
| **Batch processing** | Event-driven with streaming option |
| **Legacy WebUI** | Modern Splunk UI components |
| **No automation** | Full SOAR-style playbook support |

---

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] Faux Splunk Cloud ephemeral instances
- [x] BDD test infrastructure
- [x] Docker deployment
- [ ] Keycloak integration research

### Phase 2: Core Platform
- [ ] Backstage plugin scaffold
- [ ] Splunk UI component migration
- [ ] Basic workflow engine
- [ ] Feed connector framework

### Phase 3: Workflow Editor
- [ ] WYSIWYG node editor (React Flow / similar)
- [ ] MineMeld prototype port (miners)
- [ ] MineMeld prototype port (processors)
- [ ] MineMeld prototype port (outputs)

### Phase 4: Advanced Features
- [ ] Sankey diagram visualization
- [ ] Attack simulation integration
- [ ] Multi-tenant isolation
- [ ] Production hardening

---

## Technical Specifications

### Indicator Data Model

```typescript
interface Indicator {
  id: string;
  type: 'ipv4' | 'ipv6' | 'domain' | 'url' | 'hash_md5' | 'hash_sha256' | 'email';
  value: string;
  confidence: number;  // 0-100
  severity: 'low' | 'medium' | 'high' | 'critical';

  // STIX compatible fields
  first_seen: ISO8601DateTime;
  last_seen: ISO8601DateTime;
  valid_from?: ISO8601DateTime;
  valid_until?: ISO8601DateTime;

  // Source tracking
  sources: IndicatorSource[];

  // MineMeld compatibility
  share_level: 'white' | 'green' | 'amber' | 'red';

  // Custom metadata
  tags: string[];
  metadata: Record<string, unknown>;
}

interface IndicatorSource {
  feed_id: string;
  feed_name: string;
  confidence: number;
  first_seen: ISO8601DateTime;
  last_seen: ISO8601DateTime;
}
```

### API Endpoints (Backstage Backend Plugin)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflows` | GET | List all workflows |
| `/api/workflows` | POST | Create workflow |
| `/api/workflows/:id` | GET | Get workflow details |
| `/api/workflows/:id` | PUT | Update workflow |
| `/api/workflows/:id` | DELETE | Delete workflow |
| `/api/workflows/:id/execute` | POST | Start workflow |
| `/api/workflows/:id/pause` | POST | Pause workflow |
| `/api/feeds` | GET | List configured feeds |
| `/api/feeds/:id/indicators` | GET | Get indicators from feed |
| `/api/indicators` | GET | Search indicators |
| `/api/indicators/export` | GET | Export indicators (EDL, STIX, CSV) |

---

## References

- MineMeld GitHub (Archived): https://github.com/PaloAltoNetworks/minemeld
- MineMeld Wiki: https://github.com/PaloAltoNetworks/minemeld/wiki
- Cortex XSOAR Migration Guide: https://xsoar.pan.dev/docs/reference/articles/minemeld-migration
- Backstage Plugin Development: https://backstage.io/docs/plugins/
- STIX/TAXII Specifications: https://oasis-open.github.io/cti-documentation/
