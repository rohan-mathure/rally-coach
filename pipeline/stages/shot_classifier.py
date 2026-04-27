from app.models.shot import Shot, BallPosition
from pipeline.models.homography import CourtHomography
from pipeline.utils.court_constants import HALF_COURT_FT, NET_HEIGHT_CENTER_FT


def _classify_from_pose(shot: Shot, homography: CourtHomography | None) -> tuple[str, float]:
    pose = shot.pose
    if pose is None:
        return "unknown", 0.0

    wrist_x = pose.dominant_wrist_x   # normalized 0-1
    hip_x = pose.hip_center_x

    traj = shot.trajectory
    if len(traj) < 3:
        return "unknown", 0.0

    # Ball incoming direction: where did ball come from relative to contact frame
    contact_traj = [p for p in traj if p.frame_idx <= shot.contact_frame]
    if len(contact_traj) >= 2:
        ball_incoming_x = contact_traj[-1].x - contact_traj[0].x
    else:
        ball_incoming_x = 0.0

    # Check overhead: wrist above head
    try:
        nose_y = pose.landmarks[0]["y"]  # landmark 0 = nose
        if pose.dominant_wrist_y < nose_y - 0.05:
            return "overhead", 0.85
    except (IndexError, KeyError):
        pass

    # Check volley: contact at net zone (high ball, near net)
    if homography is not None and traj:
        contact_pos = next((p for p in traj if p.frame_idx == shot.contact_frame), traj[0])
        _, court_y = homography.pixel_to_court(contact_pos.x, contact_pos.y)
        if 30 < court_y < 48:  # within ±9ft of net
            # player foot position
            left_foot = pose.landmarks[31] if len(pose.landmarks) > 31 else None
            right_foot = pose.landmarks[32] if len(pose.landmarks) > 32 else None
            if left_foot and right_foot:
                foot_y = (left_foot["y"] + right_foot["y"]) / 2
                if foot_y > 0.6:  # feet near bottom of frame (net zone)
                    return "volley", 0.80

    # Forehand vs backhand: wrist cross-body?
    # If wrist_x is on opposite side from hip_x (relative to center), it's backhand contact extension
    wrist_offset = wrist_x - hip_x
    # Positive = wrist right of hip (forehand for right-handed player); negative = backhand
    if ball_incoming_x > 0:  # ball came from right → player on left, expects forehand on right
        if wrist_offset > 0.05:
            return "forehand", 0.75
        else:
            return "backhand", 0.70
    else:
        if wrist_offset < -0.05:
            return "forehand", 0.75
        else:
            return "backhand", 0.70


def _classify_from_trajectory(shot: Shot) -> tuple[str, float]:
    """Fallback: use ball departure direction relative to last known player position."""
    traj = shot.trajectory
    if len(traj) < 4:
        return "unknown", 0.0

    # Post-contact trajectory: ball direction after contact
    post = [p for p in traj if p.frame_idx >= shot.contact_frame]
    if len(post) < 2:
        return "unknown", 0.0

    dx = post[-1].x - post[0].x
    # Very rough: if ball goes strongly to one side assume forehand/backhand
    if abs(dx) > 50:
        return "forehand", 0.40   # can't reliably distinguish without pose
    return "unknown", 0.0


def classify_shots(shots: list[Shot], homography: CourtHomography | None) -> list[Shot]:
    updated = []
    for shot in shots:
        if shot.pose is not None:
            shot_type, conf = _classify_from_pose(shot, homography)
        else:
            shot_type, conf = _classify_from_trajectory(shot)
        updated.append(shot.model_copy(update={
            "shot_type": shot_type,
            "shot_type_confidence": conf,
        }))
    return updated
