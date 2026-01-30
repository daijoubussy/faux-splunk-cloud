@critical @integration
Feature: Instance Lifecycle Management
  As a developer
  I want to manage ephemeral Splunk instances
  So that I can test my applications against real Splunk environments

  Background:
    Given the API server is running
    And I am authenticated as a developer

  # ============================================================================
  # Instance Creation
  # ============================================================================

  @unit
  Scenario: Create instance with default configuration
    When I create an instance with name "test-splunk"
    Then the response status code is 201
    And the response contains an instance ID
    And the instance status is "provisioning"
    And the instance has default indexes configured

  @unit
  Scenario: Create instance with custom TTL
    When I create an instance with name "short-lived" and TTL 4 hours
    Then the response status code is 201
    And the instance expires in approximately 4 hours

  @unit
  Scenario Outline: Create instance with different topologies
    When I create an instance with topology "<topology>"
    Then the response status code is 201
    And the instance configuration shows topology "<topology>"

    Examples:
      | topology              |
      | standalone            |
      | distributed_minimal   |
      | distributed_clustered |

  @unit
  Scenario: Reject instance creation with invalid name
    When I create an instance with name "Invalid Name!"
    Then the response status code is 422
    And the error message contains "name"

  @unit
  Scenario: Reject instance creation with TTL exceeding maximum
    When I create an instance with name "long-lived" and TTL 999 hours
    Then the response status code is 422
    And the error message contains "ttl"

  # ============================================================================
  # Instance State Transitions
  # ============================================================================

  @integration @docker
  Scenario: Start a stopped instance
    Given an instance "paused-splunk" exists in "stopped" state
    When I start the instance "paused-splunk"
    Then the response status code is 200
    And the instance status is "starting"

  @integration @docker
  Scenario: Stop a running instance
    Given an instance "active-splunk" exists in "running" state
    When I stop the instance "active-splunk"
    Then the response status code is 200
    And the instance status is "stopped"

  @unit
  Scenario: Cannot start an already running instance
    Given an instance "running-splunk" exists in "running" state
    When I start the instance "running-splunk"
    Then the response status code is 400
    And the error message contains "already running"

  @unit
  Scenario: Cannot stop an already stopped instance
    Given an instance "stopped-splunk" exists in "stopped" state
    When I stop the instance "stopped-splunk"
    Then the response status code is 400
    And the error message contains "not running"

  # ============================================================================
  # Instance Destruction
  # ============================================================================

  @integration @docker
  Scenario: Destroy a running instance
    Given an instance "doomed-splunk" exists in "running" state
    When I destroy the instance "doomed-splunk"
    Then the response status code is 204
    And the instance no longer exists

  @unit
  Scenario: Destroy a stopped instance
    Given an instance "stopped-doomed" exists in "stopped" state
    When I destroy the instance "stopped-doomed"
    Then the response status code is 204
    And the instance no longer exists

  # ============================================================================
  # Instance Queries
  # ============================================================================

  @unit
  Scenario: List all instances
    Given the following instances exist:
      | name       | status   |
      | instance-a | running  |
      | instance-b | stopped  |
      | instance-c | running  |
    When I list all instances
    Then the response contains 3 instances

  @unit
  Scenario: Filter instances by status
    Given the following instances exist:
      | name       | status   |
      | instance-a | running  |
      | instance-b | stopped  |
      | instance-c | running  |
    When I list instances with status "running"
    Then the response contains 2 instances
    And all returned instances have status "running"

  @unit
  Scenario: Get instance details
    Given an instance "detail-test" exists in "running" state
    When I get the instance "detail-test"
    Then the response status code is 200
    And the response contains instance endpoints
    And the response contains instance credentials

  @unit
  Scenario: Get non-existent instance returns 404
    When I get the instance "non-existent-id"
    Then the response status code is 404

  # ============================================================================
  # TTL Management
  # ============================================================================

  @unit
  Scenario: Extend instance TTL
    Given an instance "expiring-soon" exists in "running" state
    And the instance expires in 1 hour
    When I extend the instance TTL by 24 hours
    Then the response status code is 200
    And the instance expires in approximately 25 hours

  @unit
  Scenario: Cannot extend TTL beyond maximum
    Given an instance "max-ttl" exists in "running" state
    When I extend the instance TTL by 999 hours
    Then the response status code is 400
    And the error message contains "maximum"

  # ============================================================================
  # Health and Logs
  # ============================================================================

  @integration @docker
  Scenario: Check health of running instance
    Given an instance "healthy-splunk" exists in "running" state
    When I check the health of instance "healthy-splunk"
    Then the response status code is 200
    And the health status is "running"

  @integration @docker
  Scenario: Get container logs
    Given an instance "logged-splunk" exists in "running" state
    When I get the logs for instance "logged-splunk" with tail 50
    Then the response status code is 200
    And the response contains log lines

  # ============================================================================
  # Wait for Ready
  # ============================================================================

  @integration @docker @slow
  Scenario: Wait for instance to become ready
    Given an instance "starting-splunk" exists in "starting" state
    When I wait for instance "starting-splunk" to be ready with timeout 60 seconds
    Then the response status code is 200
    And the instance status is "running"

  @unit
  Scenario: Wait timeout for stuck instance
    Given an instance "stuck-splunk" exists in "error" state
    When I wait for instance "stuck-splunk" to be ready with timeout 5 seconds
    Then the response status code is 408
    And the error message contains "timeout"
