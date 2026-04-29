Feature: Quality scoring

  Scenario: In-bounds deep shot with net clearance scores high
    Given a shot that is in bounds, cleared the net, landed deep, and has speed_mph 70
    When quality scoring runs
    Then the quality_score is at least 80

  Scenario: Out-of-bounds shot scores low
    Given a shot that is out of bounds, did not clear the net, and has speed_mph 30
    When quality scoring runs
    Then the quality_score is at most 30

  Scenario: Multiple shots all receive a quality score
    Given 3 shots with varying speeds 40 50 and 60 mph
    When quality scoring runs
    Then all shots have a quality_score between 0 and 100
