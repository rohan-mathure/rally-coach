"""
ITF court dimensions in feet (origin = near baseline center).

Coordinate system (court_x, court_y):
  court_x: distance from center (negative = left, positive = right)
  court_y: distance from near baseline (0) to far baseline (78)

Key dimensions:
  Total length:      78 ft
  Singles width:     27 ft (±13.5 from center)
  Doubles width:     36 ft (±18 from center)
  Net position:      39 ft from each baseline
  Net height center: 3 ft
  Net height post:   3.5 ft
  Service box depth: 21 ft from net = 18 ft from baseline
"""

COURT_LENGTH_FT = 78.0
SINGLES_WIDTH_FT = 27.0
DOUBLES_WIDTH_FT = 36.0
HALF_COURT_FT = COURT_LENGTH_FT / 2       # 39.0
SINGLES_HALF_WIDTH_FT = SINGLES_WIDTH_FT / 2  # 13.5
NET_HEIGHT_CENTER_FT = 3.0
NET_HEIGHT_POST_FT = 3.5
SERVICE_LINE_FROM_NET_FT = 21.0
SERVICE_LINE_Y_NEAR = COURT_LENGTH_FT - SERVICE_LINE_FROM_NET_FT  # 57 ft from near baseline

# The four corners of the singles court in feet (court coords):
# [near-left, near-right, far-right, far-left]
ITF_CORNERS_FEET = [
    [-SINGLES_HALF_WIDTH_FT, 0.0],           # near-left baseline
    [SINGLES_HALF_WIDTH_FT,  0.0],           # near-right baseline
    [SINGLES_HALF_WIDTH_FT,  COURT_LENGTH_FT],  # far-right baseline
    [-SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT],  # far-left baseline
]

# Singles in-bounds polygon (court coords)
SINGLES_BOUNDS = [
    [-SINGLES_HALF_WIDTH_FT, 0.0],
    [SINGLES_HALF_WIDTH_FT,  0.0],
    [SINGLES_HALF_WIDTH_FT,  COURT_LENGTH_FT],
    [-SINGLES_HALF_WIDTH_FT, COURT_LENGTH_FT],
]

# Close-call threshold (feet)
CLOSE_CALL_THRESHOLD_FT = 0.5  # 6 inches
