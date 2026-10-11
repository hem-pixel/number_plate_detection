"""
Virtual Line Crossing Detector adapter for Backend / Phase 3 AI Pipeline.
Direction Logic:
- TOP to DOWN (increasing Y across virtual line): ENTRY
- DOWN to TOP (decreasing Y across virtual line): EXIT
"""
from typing import Optional, Dict, Tuple, Any
import time


class VirtualLineCrossingDetector:
    def __init__(
        self,
        frame_height: int = 720,
        line_position_ratio: float = 0.5,
        dead_zone: int = 15,
        cooldown_seconds: float = 3.0,
    ):
        self.frame_height = frame_height
        self.line_position_ratio = line_position_ratio
        self.line_y = float(frame_height) * line_position_ratio
        self.dead_zone = dead_zone
        self.cooldown_seconds = cooldown_seconds

        self.upper_bound = self.line_y - dead_zone
        self.lower_bound = self.line_y + dead_zone

        # track_id -> {"last_zone": "ABOVE" | "BELOW" | "DEAD_ZONE", "history": [(cx, cy, t)], "last_event_time": float}
        self.tracks: Dict[int, Dict[str, Any]] = {}

    def update(
        self,
        track_id: int,
        current_centroid: Tuple[int, int],
        timestamp: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        now = timestamp if timestamp is not None else time.time()
        cx, cy = current_centroid

        # Determine current zone
        if cy < self.upper_bound:
            current_zone = "ABOVE"
        elif cy > self.lower_bound:
            current_zone = "BELOW"
        else:
            current_zone = "DEAD_ZONE"

        track = self.tracks.get(track_id)
        if track is None:
            self.tracks[track_id] = {
                "initial_zone": current_zone,
                "last_zone": current_zone,
                "history": [(cx, cy, now)],
                "last_event_time": 0.0,
            }
            return None

        track["history"].append((cx, cy, now))
        prev_zone = track["last_zone"]
        initial_zone = track["initial_zone"]

        # If in dead zone, don't trigger yet, keep track
        if current_zone == "DEAD_ZONE":
            return None

        event = None
        if now - track["last_event_time"] >= self.cooldown_seconds:
            # Check for crossing:
            # Entry: Started or was previously ABOVE, now BELOW (top to down)
            if (initial_zone == "ABOVE" or prev_zone == "ABOVE") and current_zone == "BELOW":
                event = {
                    "track_id": track_id,
                    "direction": "ENTRY",
                    "centroid": (cx, cy),
                    "timestamp": now,
                    "line_y": self.line_y,
                }
                track["last_event_time"] = now
                track["initial_zone"] = current_zone
            # Exit: Started or was previously BELOW, now ABOVE (down to top)
            elif (initial_zone == "BELOW" or prev_zone == "BELOW") and current_zone == "ABOVE":
                event = {
                    "track_id": track_id,
                    "direction": "EXIT",
                    "centroid": (cx, cy),
                    "timestamp": now,
                    "line_y": self.line_y,
                }
                track["last_event_time"] = now
                track["initial_zone"] = current_zone

        track["last_zone"] = current_zone
        return event
