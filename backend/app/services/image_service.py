from pathlib import Path
from datetime import datetime
import cv2
import numpy as np

from backend.app.core.config import settings


class ImageService:
    """Manages file-based storage for vehicle images and cropped plate images."""

    def __init__(self):
        self.vehicles_dir = settings.VEHICLES_DIR
        self.plates_dir = settings.PLATES_DIR
        self.vehicles_dir.mkdir(parents=True, exist_ok=True)
        self.plates_dir.mkdir(parents=True, exist_ok=True)

    def save_vehicle_image(self, image: np.ndarray, event_id: str | int = None) -> str:
        """Saves full frame vehicle image and returns relative path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"vehicle_{event_id or timestamp}.jpg"
        target_path = self.vehicles_dir / filename
        cv2.imwrite(str(target_path), image)
        return f"storage/vehicles/{filename}"

    def save_plate_image(self, image: np.ndarray, event_id: str | int = None) -> str:
        """Saves cropped plate image and returns relative path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"plate_{event_id or timestamp}.jpg"
        target_path = self.plates_dir / filename
        cv2.imwrite(str(target_path), image)
        return f"storage/plates/{filename}"

    def get_full_path(self, relative_path: str) -> Path:
        return settings.PROJECT_ROOT / relative_path
