Feature: Bounce detection

  Scenario: Flat trajectory produces no bounces
    Given 30 ball positions with constant y=300
    When bounce detection runs with no homography and frame_height=600
    Then 0 bounces are detected

  Scenario: Parabolic arc produces one bounce
    Given 40 ball positions forming a downward parabola peaking at frame 20
    When bounce detection runs with no homography and frame_height=600
    Then exactly 1 bounce is detected near frame 20
