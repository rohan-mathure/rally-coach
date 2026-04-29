Feature: Speed estimation

  Scenario: Speed computed with valid homography
    Given a shot with 6 post-contact positions moving 10 pixels per frame
    When speed estimation runs at 30 fps with valid homography
    Then speed_mph is between 5 and 160
    And speed_confidence is greater than 0

  Scenario: No homography yields no speed
    Given a shot with 6 post-contact positions moving 10 pixels per frame
    When speed estimation runs at 30 fps with no homography
    Then speed_mph is None
    And speed_confidence is 0.0

  Scenario: Physically implausible speed is discarded
    Given a shot with 6 post-contact positions moving 5000 pixels per frame
    When speed estimation runs at 30 fps with valid homography
    Then speed_mph is None
