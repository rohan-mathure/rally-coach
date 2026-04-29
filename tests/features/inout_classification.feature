Feature: In/out classification

  Scenario: Bounce inside court is marked in
    Given a shot with a bounce at court position (0.0, 39.0)
    When inout classification runs with valid homography
    Then the shot is_in is True
    And the shot is_close_call is False

  Scenario: Bounce outside court is marked out
    Given a shot with a bounce at court position (20.0, 39.0)
    When inout classification runs with valid homography
    Then the shot is_in is False

  Scenario: No homography leaves shot unchanged
    Given a shot with a bounce at court position (0.0, 39.0)
    When inout classification runs with no homography
    Then the shot is returned unmodified
