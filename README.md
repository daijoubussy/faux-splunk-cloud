# Faux Splunk Cloud

Ephemeral Splunk Cloud Victoria instances for development and testing.

## Overview

Faux Splunk Cloud provides developers with on-demand Splunk instances configured to operate as close as possible to official Splunk Cloud Victoria infrastructure. It enables:

- **Ephemeral Instances**: Spin up Victoria-like Splunk environments that automatically clean up
- **ACS API Compatibility**: Full compatibility with Splunk Terraform Provider and SDK
- **Backstage Integration**: Software templates for developer self-service
- **CI/CD Ready**: Ansible playbooks, Terraform modules, and Concourse pipelines

## Features

### Splunk Cloud Victoria Experience

- Search Head Clusters with automatic app distribution
- Indexer Clusters with configurable replication
- HTTP Event Collector (HEC) endpoints
- Real-time search enabled by default
- ACS API simulation for administrative operations

### Infrastructure as Code

- **Docker Compose** templates for local development
- **Kubernetes** manifests for production deployments
- **Terraform** modules for IaC workflows
- **Ansible** playbooks for configuration management

### Enterprise Integrations

- **HashiCorp Vault** for secrets management
- **Traefik** for reverse proxy and load balancing
- **Step CA** for certificate management
- **Spotify Backstage** for developer portal integration

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- [uv](https://github.com/astral-sh/uv) (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/daijoubussy/faux-splunk-cloud.git
cd faux-splunk-cloud

# Install with uv
uv pip install -e .

# Or install with pip
pip install -e .
```

### Create Your First Instance

```bash
# Create a standalone Splunk instance
faux-splunk create my-splunk --topology standalone --start --wait

# View instance details
faux-splunk show <instance-id>

# Access Splunk Web UI
open http://localhost:18000
```

### Start the API Server

```bash
# Start the API server
faux-splunk serve

# API documentation available at
open http://localhost:8800/docs
```

## Usage

### CLI Commands

```bash
# Create instances with different topologies
faux-splunk create dev-splunk --topology standalone
faux-splunk create test-splunk --topology distributed_minimal
faux-splunk create prod-like --topology victoria_full

# Manage instances
faux-splunk list
faux-splunk start <instance-id>
faux-splunk stop <instance-id>
faux-splunk logs <instance-id>
faux-splunk destroy <instance-id>

# Extend instance TTL
faux-splunk extend <instance-id> 24

# Start infrastructure services
faux-splunk infra up
```

### Python SDK

```python
from faux_splunk_cloud.services.instance_manager import instance_manager
from faux_splunk_cloud.models.instance import InstanceCreate, InstanceConfig, InstanceTopology

# Create an instance
config = InstanceConfig(
    topology=InstanceTopology.STANDALONE,
    enable_hec=True,
    memory_mb=2048,
)
request = InstanceCreate(
    name="my-dev-splunk",
    config=config,
    ttl_hours=24,
)

await instance_manager.start()
instance = await instance_manager.create_instance(request)
instance = await instance_manager.start_instance(instance.id)
instance = await instance_manager.wait_for_ready(instance.id)

# Use Splunk SDK
client = instance_manager.get_splunk_client(instance.id)
indexes = await client.list_indexes()
```

### Splunk SDK Compatibility

```python
import splunklib.client as client

# Connect using standard Splunk SDK
service = client.connect(
    host="localhost",
    port=18089,
    username="admin",
    password="<instance-password>"
)

# Use standard SDK operations
for index in service.indexes:
    print(index.name)
```

### ACS API

```bash
# List indexes via ACS API
curl -H "Authorization: Bearer $ACS_TOKEN" \
  http://localhost:8800/fsc-xxxxx/adminconfig/v2/indexes

# Create an index
curl -X POST \
  -H "Authorization: Bearer $ACS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "myindex", "searchableDays": 90}' \
  http://localhost:8800/fsc-xxxxx/adminconfig/v2/indexes

# List HEC tokens
curl -H "Authorization: Bearer $ACS_TOKEN" \
  http://localhost:8800/fsc-xxxxx/adminconfig/v2/inputs/http-event-collectors
```

### Terraform

```hcl
provider "fauxsplunk" {
  api_url   = "http://localhost:8800"
  api_token = var.fsc_api_token
}

resource "fauxsplunk_instance" "dev" {
  name = "terraform-managed"

  config {
    topology   = "standalone"
    experience = "victoria"
    enable_hec = true
  }

  ttl_hours = 24
}

resource "fauxsplunk_acs_index" "app_logs" {
  instance_id     = fauxsplunk_instance.dev.id
  name            = "app_logs"
  searchable_days = 90
}
```

## Topologies

### Standalone

Single Splunk instance for quick testing. Minimal resource usage.

### Distributed Minimal

Separate Search Head and Indexer. Minimum Victoria-like experience.

### Distributed Clustered

Search Head Cluster + Indexer Cluster. Production-like Victoria Experience.

### Victoria Full

Complete Victoria Experience simulation with:
- 3-node Search Head Cluster with Deployer
- 3-node Indexer Cluster with Cluster Manager
- Full replication and search factors

## Configuration

Configuration is managed via `default.yml` files following Splunk docker project best practices:

```yaml
splunk:
  conf:
    indexes:
      main:
        maxTotalDataSizeMB: 500000
        frozenTimePeriodInSecs: 7776000

    limits:
      search:
        max_mem_usage_mb: 4096

  hec:
    default:
      token: "<generated>"
      index: main
```

## Backstage Integration

Register the component in your Backstage catalog:

```yaml
# In app-config.yaml
catalog:
  locations:
    - type: url
      target: https://github.com/daijoubussy/faux-splunk-cloud/blob/main/catalog-info.yaml
    - type: url
      target: https://github.com/daijoubussy/faux-splunk-cloud/blob/main/backstage/template.yaml
```

## Architecture

See [docs/architecture.d2](docs/architecture.d2) for detailed architecture diagrams.

```
┌─────────────────────────────────────────────────────────────┐
│                    Faux Splunk Cloud                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   CLI       │  │  REST API   │  │  ACS API Simulation │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Instance Manager                           ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ││
│  │  │ Docker Orch. │  │ Splunk SDK   │  │ Auth Service │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │           Ephemeral Splunk Instances                    ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐││
│  │  │ Standalone │  │ Distributed│  │ Victoria Full      │││
│  │  └────────────┘  └────────────┘  └────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## References

- [Splunk Cloud Platform Service Details](https://help.splunk.com/en/splunk-cloud-platform/get-started/service-terms-and-policies/)
- [Splunk Validated Architectures](https://help.splunk.com/en/splunk-cloud-platform/splunk-validated-architectures/)
- [Admin Config Service (ACS) API](https://help.splunk.com/en/splunk-cloud-platform/administer/admin-config-service-manual/)
- [Splunk SDK for Python](https://github.com/splunk/splunk-sdk-python)
- [Splunk Docker Project](https://splunk.github.io/docker-splunk/)
- [Spotify Backstage](https://backstage.io/)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.
