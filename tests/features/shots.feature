Feature: Shot retrieval

  Scenario: List shots returns all shots ordered by shot_number
    Given a session with 3 shots exists
    When I GET the shots for that session
    Then the shots response status is 200
    And the shots list has 3 items in shot_number order

  Scenario: CSV export contains correct headers
    Given a session with 3 shots exists
    When I GET the CSV export for that session
    Then the CSV response content-type is text/csv
    And the CSV body contains the header "shot_number"
