@critical @integration
Feature: Attack Simulation
  As a security analyst
  I want to simulate cyber attacks against Splunk instances
  So that I can test detection rules and train SOC analysts

  Background:
    Given the API server is running
    And I am authenticated as a security analyst

  # ============================================================================
  # Threat Actor Management
  # ============================================================================

  @unit
  Scenario: List all threat actors
    When I list all threat actors
    Then the response status code is 200
    And the response contains threat actors
    And each threat actor has a threat level

  @unit
  Scenario: Filter threat actors by level
    When I list threat actors with level "nation_state"
    Then the response status code is 200
    And all returned actors have threat level "nation_state"

  @unit
  Scenario: Get threat actor details
    When I get threat actor "apt29"
    Then the response status code is 200
    And the response contains threat actor name "APT29"
    And the response contains MITRE ATT&CK techniques
    And the response contains behavioral characteristics

  @unit
  Scenario: Get non-existent threat actor
    When I get threat actor "non-existent"
    Then the response status code is 404

  # ============================================================================
  # Campaign Lifecycle
  # ============================================================================

  @unit
  Scenario: Create attack campaign with threat actor
    Given a running instance "target-splunk" exists
    When I create a campaign with threat actor "apt29" targeting "target-splunk"
    Then the response status code is 201
    And the campaign status is "pending"
    And the campaign has a unique ID

  @unit
  Scenario: Create campaign with invalid threat actor
    Given a running instance "target-splunk" exists
    When I create a campaign with threat actor "invalid-actor" targeting "target-splunk"
    Then the response status code is 400
    And the error message contains "threat actor"

  @unit
  Scenario: Start attack campaign
    Given a campaign "test-campaign" exists in "pending" state
    When I start the campaign "test-campaign"
    Then the response status code is 200
    And the campaign status is "running"

  @unit
  Scenario: Pause running campaign
    Given a campaign "running-campaign" exists in "running" state
    When I pause the campaign "running-campaign"
    Then the response status code is 200
    And the campaign status is "paused"

  @unit
  Scenario: Resume paused campaign
    Given a campaign "paused-campaign" exists in "paused" state
    When I start the campaign "paused-campaign"
    Then the response status code is 200
    And the campaign status is "running"

  @unit
  Scenario: Cannot start completed campaign
    Given a campaign "done-campaign" exists in "completed" state
    When I start the campaign "done-campaign"
    Then the response status code is 400
    And the error message contains "cannot start"

  # ============================================================================
  # Campaign Monitoring
  # ============================================================================

  @unit
  Scenario: Get campaign details
    Given a campaign "monitor-campaign" exists in "running" state
    When I get campaign "monitor-campaign"
    Then the response status code is 200
    And the response contains current kill chain phase
    And the response contains completed steps count
    And the response contains total steps count

  @unit
  Scenario: Get campaign attack steps
    Given a campaign "active-campaign" exists with executed steps
    When I get steps for campaign "active-campaign"
    Then the response status code is 200
    And each step contains technique ID
    And each step contains technique name
    And each step contains timestamp
    And each step contains success status

  @unit
  Scenario: Get campaign generated logs
    Given a campaign "logged-campaign" exists with generated logs
    When I get logs for campaign "logged-campaign" with limit 100
    Then the response status code is 200
    And the response contains log entries
    And each log entry has a timestamp
    And each log entry has a sourcetype

  @unit
  Scenario: List campaigns for instance
    Given multiple campaigns exist for instance "multi-target"
    When I list campaigns for instance "multi-target"
    Then the response status code is 200
    And all returned campaigns target instance "multi-target"

  # ============================================================================
  # Attack Scenarios
  # ============================================================================

  @unit
  Scenario: List available attack scenarios
    When I list attack scenarios
    Then the response status code is 200
    And the response contains predefined scenarios
    And each scenario has a threat level
    And each scenario has estimated duration

  @unit
  Scenario: Execute predefined scenario
    Given a running instance "scenario-target" exists
    When I execute scenario "apt_intrusion" against "scenario-target"
    Then the response status code is 201
    And a campaign is created and started
    And the campaign uses the scenario's threat actor

  @unit
  Scenario: Execute scenario against non-running instance
    Given an instance "stopped-target" exists in "stopped" state
    When I execute scenario "apt_intrusion" against "stopped-target"
    Then the response status code is 400
    And the error message contains "not running"

  # ============================================================================
  # Kill Chain Progression
  # ============================================================================

  @integration @slow
  Scenario: Campaign progresses through kill chain phases
    Given a running instance "killchain-target" exists
    And a campaign "killchain-test" targeting "killchain-target" with threat actor "script_kiddie_generic"
    When I start the campaign "killchain-test"
    And I wait for the campaign to progress
    Then the campaign phase advances from "reconnaissance"
    And attack steps are recorded for each phase

  @unit
  Scenario: Campaign detects attack (simulation)
    Given a campaign "detected-campaign" with high detection probability
    When the campaign executes a detectable technique
    Then the campaign status changes to "detected"
    And the detection step is recorded

  # ============================================================================
  # Data Generation
  # ============================================================================

  @unit
  Scenario: Generated logs match expected format
    Given a campaign with threat actor "apt29"
    When the campaign generates Windows Security logs
    Then the logs contain EventCode field
    And the logs contain proper timestamp format
    And the logs match Splunk CIM format

  @unit
  Scenario Outline: Generate logs for different data sources
    Given a campaign configured for "<data_source>" generation
    When the campaign generates logs
    Then the sourcetype is "<expected_sourcetype>"

    Examples:
      | data_source         | expected_sourcetype      |
      | windows_security    | WinEventLog:Security     |
      | sysmon              | XmlWinEventLog:Microsoft-Windows-Sysmon/Operational |
      | firewall            | pan:traffic              |
      | dns                 | stream:dns               |
      | proxy               | bluecoat:proxysg:access  |
