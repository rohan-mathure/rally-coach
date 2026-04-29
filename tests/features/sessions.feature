Feature: Session management

  Scenario: List returns all sessions
    Given the database has 2 sessions
    When I GET /api/sessions
    Then the sessions response status is 200
    And the sessions list has 2 items

  Scenario: Get existing session
    Given a session "test-session-1" exists
    When I GET /api/sessions/test-session-1
    Then the session response status is 200
    And the session response contains session_id "test-session-1"

  Scenario: Get missing session returns 404
    Given the sessions database is empty
    When I GET /api/sessions/no-such-id
    Then the session response status is 404

  Scenario: Manual calibration updates homography
    Given a session "calib-session-1" exists
    When I POST calibrate for session "calib-session-1" with 4 valid corners
    Then the calibrate response status is 200
    And the calibrate response status field is "calibrated"
