# Faux Splunk Cloud - Test Strategy & BDD Specification

## Executive Summary

This document defines the testing strategy for Faux Splunk Cloud using Behavior-Driven Development (BDD) with Gherkin specifications. All tests are designed to be **100% deterministic** through proper isolation, mocking, and seed-based randomization.

## Test Pyramid Distribution

```
                    ┌─────────────────┐
                    │   E2E (10%)     │  Playwright + Cucumber
                    │   ~15 scenarios │  Full user workflows
                    ├─────────────────┤
                    │ Integration     │  pytest-bdd + TestClient
                    │ (20%) ~40 tests │  API chains, Docker ops
                    ├─────────────────┤
                    │   Unit (70%)    │  pytest + Jest
                    │   ~150 tests    │  Logic, validation, algorithms
                    └─────────────────┘
```

## Technology Stack

| Layer | Framework | Purpose |
|-------|-----------|---------|
| Python BDD | pytest-bdd | Gherkin scenarios for API/services |
| Python Unit | pytest + pytest-asyncio | Async unit tests |
| Test Isolation | testcontainers | Docker service isolation |
| Time Control | freezegun | Deterministic time handling |
| Test Data | factory-boy + Faker | Reproducible fixtures |
| Frontend E2E | Playwright + Cucumber | Browser automation |
| Frontend Unit | Jest + Testing Library | Component tests |
| Contract | Pact | API contract verification |

## Determinism Guarantees

### 1. Random Data Seeding
All random operations use fixed seeds set in `conftest.py`:
```python
Faker.seed(0)
random.seed(0)
```

### 2. Time Freezing
All time-dependent tests use `freezegun`:
```python
@freeze_time("2025-01-30 12:00:00")
def test_instance_expiry():
    ...
```

### 3. Docker Isolation
Each test session gets isolated containers via testcontainers:
```python
@pytest.fixture(scope="session")
def docker_services():
    with DockerCompose("docker-compose.test.yml") as compose:
        yield compose
```

### 4. Database Isolation
Each test uses transaction rollback:
```python
@pytest.fixture
async def db_session():
    async with session.begin():
        yield session
        # Automatic rollback
```

---

## User Stories & Feature Specifications

### Epic 1: Instance Lifecycle Management

#### Story 1.1: Create Ephemeral Instance
**As a** developer
**I want to** create an ephemeral Splunk instance
**So that** I can test my application against a real Splunk environment

**Acceptance Criteria:**
- Instance is created with unique ID
- Instance starts in PROVISIONING state
- Instance transitions to RUNNING within timeout
- Default indexes are created (main, summary, _internal, _audit)
- HEC endpoint is available
- Credentials are generated and returned

#### Story 1.2: Manage Instance Lifecycle
**As a** developer
**I want to** start, stop, and destroy instances
**So that** I can control resource usage

**Acceptance Criteria:**
- Running instance can be stopped
- Stopped instance can be started
- Any instance can be destroyed
- Destroyed instances free all resources
- Invalid state transitions return clear errors

#### Story 1.3: Instance Auto-Expiration
**As a** platform administrator
**I want** instances to automatically expire after TTL
**So that** resources are not wasted on forgotten instances

**Acceptance Criteria:**
- Instances expire after configured TTL
- TTL can be extended before expiration
- Expired instances are automatically cleaned up
- Users are notified before expiration (future)

---

### Epic 2: ACS API Compatibility

#### Story 2.1: Manage Indexes via ACS API
**As a** Terraform user
**I want to** manage indexes using the ACS API
**So that** my existing IaC configurations work unchanged

**Acceptance Criteria:**
- Create index with name, datatype, searchableDays
- List all indexes on stack
- Delete index by name
- API responses match Splunk Cloud ACS format

#### Story 2.2: Manage HEC Tokens via ACS API
**As an** application developer
**I want to** create HEC tokens programmatically
**So that** I can configure data ingestion

**Acceptance Criteria:**
- Create HEC token with name and default index
- List all HEC tokens
- Delete HEC token
- Token value is returned on creation

---

### Epic 3: Attack Simulation

#### Story 3.1: Launch Attack Campaign
**As a** security analyst
**I want to** simulate attacks against my Splunk instance
**So that** I can test detection rules

**Acceptance Criteria:**
- Select threat actor profile (APT29, Lazarus, etc.)
- Campaign progresses through kill chain phases
- Realistic logs are generated
- Campaign can be paused and resumed

#### Story 3.2: Monitor Attack Progress
**As a** security analyst
**I want to** monitor attack campaign progress
**So that** I can observe detection effectiveness

**Acceptance Criteria:**
- View current kill chain phase
- View completed attack steps
- View generated logs
- See detection status

#### Story 3.3: Execute Predefined Scenarios
**As a** SOC trainer
**I want to** execute predefined attack scenarios
**So that** I can train analysts on specific attack patterns

**Acceptance Criteria:**
- List available scenarios (APT intrusion, ransomware, etc.)
- Execute scenario against target instance
- Scenario maps to appropriate threat actor
- Campaign is created and started automatically

---

### Epic 4: User Interface

#### Story 4.1: Dashboard Overview
**As a** user
**I want to** see an overview of my instances and campaigns
**So that** I can quickly assess system status

**Acceptance Criteria:**
- Display instance count by status
- Display active campaign count
- Show recent activity
- Provide quick action buttons

#### Story 4.2: Instance Management UI
**As a** developer
**I want to** manage instances through a web interface
**So that** I don't need to use the CLI

**Acceptance Criteria:**
- List all instances with status
- Create new instance with form
- View instance details and logs
- Start/stop/destroy instances

---

## Test Tags

| Tag | Purpose | Run Command |
|-----|---------|-------------|
| `@unit` | Fast isolated tests | `pytest -m unit` |
| `@integration` | API + service tests | `pytest -m integration` |
| `@e2e` | Full workflow tests | `pytest -m e2e` |
| `@slow` | Tests > 5 seconds | `pytest -m "not slow"` |
| `@docker` | Requires Docker | `pytest -m docker` |
| `@critical` | Must pass for deploy | `pytest -m critical` |
| `@wip` | Work in progress | `pytest -m "not wip"` |

---

## Directory Structure

```
tests/
├── conftest.py                 # Global fixtures, seeds, hooks
├── factories.py                # Factory Boy definitions
├── pytest.ini                  # Pytest configuration
│
├── unit/                       # 70% - Fast, isolated
│   ├── test_auth.py
│   ├── test_models.py
│   ├── test_kill_chain.py
│   ├── test_threat_actors.py
│   └── test_data_generators.py
│
├── integration/                # 20% - API + services
│   ├── conftest.py            # Integration fixtures
│   ├── test_instance_api.py
│   ├── test_acs_api.py
│   └── test_attack_api.py
│
├── features/                   # BDD Gherkin specs
│   ├── instance_lifecycle.feature
│   ├── acs_api.feature
│   ├── attack_simulation.feature
│   └── steps/
│       ├── conftest.py
│       ├── instance_steps.py
│       ├── acs_steps.py
│       └── attack_steps.py
│
└── e2e/                        # 10% - Full workflows
    ├── conftest.py
    └── test_complete_workflows.py

ui/tests/
├── unit/                       # Jest component tests
│   └── components/
├── e2e/                        # Playwright E2E
│   ├── features/
│   └── steps/
└── jest.config.js
```

---

## Blockers & Dependencies

### Phase 0 Prerequisites (Current Phase)
- [x] Research BDD frameworks → pytest-bdd selected
- [x] Analyze testable surfaces → Inventory complete
- [ ] Set up test infrastructure → In progress
- [ ] No blockers identified for test setup

### Phase 1 Dependencies
- Test fixtures require backend services to exist (✓ complete)
- Testcontainers requires Docker (✓ available)

### Phase 2 Dependencies
- E2E tests require UI to be built (✓ complete)
- Playwright requires UI running (use dev server or docker)

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Determinism | 100% | No flaky tests in 10 consecutive runs |
| Unit Coverage | >80% | pytest-cov report |
| Integration Coverage | >70% | API endpoint coverage |
| E2E Coverage | 100% critical paths | All user stories covered |
| Test Speed | <5 min total | CI pipeline duration |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-01-30 | Claude | Initial strategy document |
