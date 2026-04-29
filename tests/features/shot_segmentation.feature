Feature: Shot segmentation

  Scenario: Two bounces produce one shot
    Given 2 bounces at frames 10 and 60 and positions covering frames 0 to 70
    When shot segmentation runs at 30 fps
    Then 1 shot is returned
    And the shot start_frame is 10 and end_frame is 60

  Scenario: Segment too short is skipped
    Given 2 bounces at frames 10 and 15 and positions covering frames 0 to 20
    When shot segmentation runs at 30 fps
    Then 0 shots are returned

  Scenario: Long interpolation gap adds pipeline warning
    Given 2 bounces at frames 10 and 60 and positions with 10 consecutive interpolated frames from 30
    When shot segmentation runs at 30 fps
    Then 1 shot is returned
    And the shot pipeline_warnings contains "long_detection_gap"
