"""
Phase 3: Single Camera Virtual Line Crossing Detection Module
=============================================================
Detects vehicle ENTRY and EXIT using a virtual horizontal line across a single camera view.
- Movement TOP -> DOWN across line = ENTRY
- Movement DOWN -> UP across line = EXIT
- Incorporates anti-jitter dead zone (hysteresis)
- Requires minimum track age & minimum vertical movement
- Debounce and cooldown to prevent duplicate events
"""

import time
from typing import Dict, List, Optional, Tuple, Any, Collection, Set, Union
from dataclasses import dataclass, field


@dataclass
class TrackCrossingState:
    """Maintains trajectory and crossing state for an individual tracked plate/vehicle."""
    track_id: int
    first_center_y: float
    previous_center_y: float
    current_center_y: float
    previous_side: str = "UNKNOWN"   # "ABOVE", "BELOW", or "DEAD_ZONE"
    current_side: str = "UNKNOWN"    # "ABOVE", "BELOW", or "DEAD_ZONE"
    first_seen_time: float = field(default_factory=time.time)
    last_seen_time: float = field(default_factory=time.time)
    total_frames: int = 1
    event_triggered: bool = False
    last_event_time: float = 0.0
    last_event_type: Optional[str] = None  # "ENTRY" or "EXIT"


class LineCrossingDetector:
    """
    Evaluates vehicle plate coordinates relative to a virtual horizontal line.
    Calculates line position dynamically based on frame height.
    """

    def __init__(
        self,
        camera_id: str = "GATE_CAMERA_01",
        camera_name: str = "Gate Camera 01",
        line_position_percent: float = 50.0,
        dead_zone: int = 20,
        min_track_age: int = 5,
        min_vertical_movement: int = 15,
        cooldown_seconds: float = 5.0,
    ):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.line_position_percent = float(line_position_percent)
        self.dead_zone = int(dead_zone)
        self.min_track_age = int(min_track_age)
        self.min_vertical_movement = int(min_vertical_movement)
        self.cooldown_seconds = float(cooldown_seconds)

        self.track_states: Dict[int, TrackCrossingState] = {}

    def get_line_y(self, frame_height: int) -> float:
        """Dynamically computes the Y-coordinate of the virtual horizontal line."""
        return float(frame_height) * (self.line_position_percent / 100.0)

    def get_side(self, center_y: float, frame_height: int) -> str:
        """
        Determines whether the given Y coordinate is ABOVE, BELOW, or in the DEAD_ZONE.
        Dead zone acts as hysteresis buffer around the line.
        """
        line_y = self.get_line_y(frame_height)
        threshold_above = line_y - self.dead_zone
        threshold_below = line_y + self.dead_zone

        if center_y < threshold_above:
            return "ABOVE"
        elif center_y > threshold_below:
            return "BELOW"
        else:
            return "DEAD_ZONE"

    def update(
        self,
        track_id: int,
        center_y: float,
        frame_height: int,
        current_time: Optional[float] = None,
    ) -> Optional[str]:
        """
        Updates the trajectory of a tracked plate and checks for line crossing.
        Returns:
            "ENTRY" if crossed from TOP -> DOWN,
            "EXIT"  if crossed from DOWN -> UP,
            None    if no valid crossing event.
        """
        now = current_time if current_time is not None else time.time()
        detected_side = self.get_side(center_y, frame_height)

        if track_id not in self.track_states:
            # First observation of this track
            state = TrackCrossingState(
                track_id=track_id,
                first_center_y=center_y,
                previous_center_y=center_y,
                current_center_y=center_y,
                previous_side=detected_side,
                current_side=detected_side,
                first_seen_time=now,
                last_seen_time=now,
                total_frames=1,
                event_triggered=False,
                last_event_time=0.0,
                last_event_type=None,
            )
            self.track_states[track_id] = state
            return None

        state = self.track_states[track_id]
        state.total_frames += 1
        state.last_seen_time = now
        state.previous_center_y = state.current_center_y
        state.current_center_y = center_y

        # If detected_side is DEAD_ZONE, we do NOT change previous_side
        # so the side prior to entering the dead zone is retained for hysteresis.
        if detected_side != "DEAD_ZONE":
            if state.current_side != "DEAD_ZONE":
                state.previous_side = state.current_side
            state.current_side = detected_side

        # Evaluate crossing condition only when track age requirement is met
        if state.total_frames < self.min_track_age:
            return None

        # Check total vertical displacement to reject static noise
        total_movement = abs(state.current_center_y - state.first_center_y)
        if total_movement < self.min_vertical_movement:
            return None

        crossing_event: Optional[str] = None

        # TOP -> DOWN crossing = ENTRY
        if state.previous_side == "ABOVE" and state.current_side == "BELOW":
            crossing_event = "ENTRY"
            print(f"[LINE] ID={track_id} ABOVE -> BELOW (Movement: {total_movement:.1f}px)")

        # DOWN -> UP crossing = EXIT
        elif state.previous_side == "BELOW" and state.current_side == "ABOVE":
            crossing_event = "EXIT"
            print(f"[LINE] ID={track_id} BELOW -> ABOVE (Movement: {total_movement:.1f}px)")

        if crossing_event:
            # Check event cooldown debounce
            time_since_last = now - state.last_event_time
            if state.event_triggered and time_since_last < self.cooldown_seconds:
                return None

            state.event_triggered = True
            state.last_event_time = now
            state.last_event_type = crossing_event
            # Update baseline Y to current to allow future return crossings
            state.first_center_y = state.current_center_y
            state.previous_side = state.current_side
            return crossing_event

        return None

    def reset_track(self, track_id: int):
        """Clears state for a specific track ID."""
        if track_id in self.track_states:
            del self.track_states[track_id]

    def cleanup_expired_tracks(self, active_track_ids: Union[List[int], Set[int], Collection[int]], max_idle_seconds: float = 10.0, current_time: Optional[float] = None):
        """Removes tracks that have disappeared from the camera view."""
        now = current_time if current_time is not None else time.time()
        active_set = set(active_track_ids)

        for track_id in list(self.track_states.keys()):
            if track_id not in active_set:
                idle = now - self.track_states[track_id].last_seen_time
                if idle >= max_idle_seconds:
                    del self.track_states[track_id]

    def get_track_state(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Returns diagnostic dict for a track."""
        if track_id not in self.track_states:
            return None
        st = self.track_states[track_id]
        return {
            "track_id": st.track_id,
            "first_center_y": st.first_center_y,
            "current_center_y": st.current_center_y,
            "previous_side": st.previous_side,
            "current_side": st.current_side,
            "total_frames": st.total_frames,
            "event_triggered": st.event_triggered,
            "last_event_type": st.last_event_type,
        }

    def get_config(self) -> Dict[str, Any]:
        """Returns camera configuration dict."""
        return {
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "line_position_percent": self.line_position_percent,
            "dead_zone": self.dead_zone,
            "min_track_age": self.min_track_age,
            "min_vertical_movement": self.min_vertical_movement,
            "cooldown_seconds": self.cooldown_seconds,
            "enabled": True,
        }

    def update_config(self, **kwargs):
        """Updates line crossing parameters dynamically."""
        if "line_position_percent" in kwargs and kwargs["line_position_percent"] is not None:
            self.line_position_percent = float(kwargs["line_position_percent"])
        if "dead_zone" in kwargs and kwargs["dead_zone"] is not None:
            self.dead_zone = int(kwargs["dead_zone"])
        if "min_track_age" in kwargs and kwargs["min_track_age"] is not None:
            self.min_track_age = int(kwargs["min_track_age"])
        if "min_vertical_movement" in kwargs and kwargs["min_vertical_movement"] is not None:
            self.min_vertical_movement = int(kwargs["min_vertical_movement"])
        if "cooldown_seconds" in kwargs and kwargs["cooldown_seconds"] is not None:
            self.cooldown_seconds = float(kwargs["cooldown_seconds"])
        if "camera_name" in kwargs and kwargs["camera_name"] is not None:
            self.camera_name = str(kwargs["camera_name"])
