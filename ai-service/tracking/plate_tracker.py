"""
Plate Tracking & Temporal Stability Module
"""

from collections import deque, Counter
from typing import List, Tuple, Optional, Any, Dict


def compute_iou(box1: List[float], box2: List[float]) -> float:
    """
    Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2].
    """
    x1_max = max(box1[0], box2[0])
    y1_max = max(box1[1], box2[1])
    x2_min = min(box1[2], box2[2])
    y2_min = min(box1[3], box2[3])

    intersection_w = max(0, x2_min - x1_max)
    intersection_h = max(0, y2_min - y1_max)
    intersection_area = intersection_w * intersection_h

    area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
    area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])

    union_area = area1 + area2 - intersection_area
    if union_area <= 0:
        return 0.0
    return intersection_area / union_area


class TrackedPlate:
    """
    Maintains temporal state and OCR history for a detected plate over time.
    """

    def __init__(
        self,
        track_id: int,
        box: List[float],
        yolo_conf: float,
        history_window_size: int = 8,
        min_stable_count: int = 2,
        ocr_interval_unstable: int = 3,
        ocr_interval_stable: int = 12,
    ):
        self.track_id = track_id
        self.box = box
        self.yolo_conf = yolo_conf
        self.disappeared = 0
        self.frames_since_ocr = 0
        self.total_frames_observed = 1

        self.history_window_size = history_window_size
        self.min_stable_count = min_stable_count
        self.ocr_interval_unstable = ocr_interval_unstable
        self.ocr_interval_stable = ocr_interval_stable

        # OCR History buffer: stores recent valid OCR readings (text, confidence, description)
        self.ocr_history = deque(maxlen=self.history_window_size)

        # Stability state
        self.is_stable = False
        self.stable_text: Optional[str] = None
        self.stable_ocr_conf = 0.0
        self.stable_desc = ""

    def update_detection(self, box: List[float], yolo_conf: float):
        """Updates box position and resets disappearance counter."""
        self.box = box
        self.yolo_conf = yolo_conf
        self.disappeared = 0
        self.frames_since_ocr += 1
        self.total_frames_observed += 1

    def add_ocr_result(self, text: str, conf: float, desc: str):
        """
        Records a valid OCR result and evaluates temporal stability.
        Only valid Indian plate results should be passed here.
        """
        self.frames_since_ocr = 0
        if not text:
            return

        self.ocr_history.append((text, conf, desc))

        # Check frequency of readings in recent window
        texts = [item[0] for item in self.ocr_history]
        counts = Counter(texts)
        most_common_text, frequency = counts.most_common(1)[0]

        # Require at least min_stable_count matching readings to declare stability
        if frequency >= self.min_stable_count:
            matching_items = [item for item in self.ocr_history if item[0] == most_common_text]
            avg_conf = sum(item[1] for item in matching_items) / len(matching_items)
            desc_val = matching_items[-1][2]

            self.is_stable = True
            self.stable_text = most_common_text
            self.stable_ocr_conf = avg_conf
            self.stable_desc = desc_val

    def should_run_ocr(self) -> bool:
        """Determines if OCR should be executed on this frame to conserve CPU."""
        if len(self.ocr_history) == 0:
            return True

        if not self.is_stable:
            return self.frames_since_ocr >= self.ocr_interval_unstable
        else:
            return self.frames_since_ocr >= self.ocr_interval_stable


class PlateTracker:
    """
    Coordinates multi-plate tracking across continuous video frames using IoU association.
    """

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_disappeared_frames: int = 15,
        min_stable_count: int = 2,
    ):
        self.next_id = 1
        self.tracks: Dict[int, TrackedPlate] = {}
        self.iou_threshold = iou_threshold
        self.max_disappeared_frames = max_disappeared_frames
        self.min_stable_count = min_stable_count

    def update(self, current_detections: List[Tuple[List[float], float]]) -> List[TrackedPlate]:
        """
        Matches current frame detections [ (box, yolo_conf), ... ]
        with existing tracked plates using IoU.
        """
        updated_tracks = []
        unmatched_detections = list(current_detections)

        # Match existing tracks with best overlapping detection
        for track_id, track in list(self.tracks.items()):
            best_iou = 0.0
            best_det_idx = -1

            for idx, (det_box, det_conf) in enumerate(unmatched_detections):
                iou = compute_iou(track.box, det_box)
                if iou > best_iou:
                    best_iou = iou
                    best_det_idx = idx

            if best_iou >= self.iou_threshold and best_det_idx != -1:
                det_box, det_conf = unmatched_detections.pop(best_det_idx)
                track.update_detection(det_box, det_conf)
                updated_tracks.append(track)
            else:
                track.disappeared += 1
                track.frames_since_ocr += 1
                if track.disappeared > self.max_disappeared_frames:
                    del self.tracks[track_id]

        # Register any remaining unmatched detections as new tracks
        for det_box, det_conf in unmatched_detections:
            new_track = TrackedPlate(
                self.next_id,
                det_box,
                det_conf,
                min_stable_count=self.min_stable_count,
            )
            self.tracks[self.next_id] = new_track
            updated_tracks.append(new_track)
            self.next_id += 1

        return updated_tracks
