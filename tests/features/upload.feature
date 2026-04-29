Feature: Video upload

  Scenario: Upload by local path creates a queued session
    Given a valid mp4 file exists on disk
    When I POST to /api/sessions/from-path with that file path
    Then the upload response status is 201
    And the upload response contains a session_id
    And the upload response status field is "queued"

  Scenario: Upload unsupported extension returns 400
    Given a txt file exists on disk
    When I POST to /api/sessions/from-path with that file path
    Then the upload response status is 400

  Scenario: Upload missing path returns 400
    When I POST to /api/sessions/from-path with path "/no/such/file.mp4"
    Then the upload response status is 400
