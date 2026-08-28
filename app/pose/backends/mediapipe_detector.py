"""MediaPipe Tasks pose detector (optional backend).

Requires the ``mediapipe`` extra and a downloaded pose model
(see :mod:`app.pose.backends.mediapipe_model`).
"""

from pathlib import Path

import numpy as np

from app.models.keypoints import KeypointSchema, RawPose
from app.pose.backends.mediapipe_model import default_model_path
from app.pose.capabilities import DetectorCapabilities
from app.pose.detector_base import PoseDetector
from app.pose.schemas import MEDIAPIPE_POSE

_CAPABILITIES = DetectorCapabilities(
    keypoint_count=MEDIAPIPE_POSE.keypoint_count,
    is_3d=False,
    multi_person=False,
    gpu=True,
)


class MediaPipeDetector(PoseDetector):
    """Single-person 2D pose detection with MediaPipe's ``PoseLandmarker``.

    Pass ``use_gpu=True`` to run inference on the GPU delegate where the
    platform supports it (``registry.create("mediapipe", use_gpu=True)``).
    """

    def __init__(
        self, model_path: str | Path | None = None, *, use_gpu: bool = False
    ) -> None:
        import mediapipe as mp
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import (
            PoseLandmarker,
            PoseLandmarkerOptions,
        )

        resolved = (
            Path(model_path) if model_path is not None else default_model_path()
        )

        if not resolved.exists():
            raise FileNotFoundError(
                f"Pose model not found at {resolved}. Download it with: "
                "python -m app.pose.backends.mediapipe_model"
            )

        delegate = (
            BaseOptions.Delegate.GPU if use_gpu else BaseOptions.Delegate.CPU
        )

        self._mp = mp
        self._model_path = resolved
        self._landmarker = PoseLandmarker.create_from_options(
            PoseLandmarkerOptions(
                base_options=BaseOptions(
                    model_asset_path=str(resolved), delegate=delegate
                ),
                num_poses=1,
            )
        )

    @property
    def schema(self) -> KeypointSchema:
        return MEDIAPIPE_POSE

    @property
    def capabilities(self) -> DetectorCapabilities:
        return _CAPABILITIES

    def detect(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp: float,
    ) -> RawPose | None:
        rgb = np.ascontiguousarray(frame[:, :, ::-1])
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        result = self._landmarker.detect(image)

        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks[0]
        height, width = frame.shape[:2]

        points = np.array(
            [(landmark.x * width, landmark.y * height) for landmark in landmarks],
            dtype=np.float64,
        )
        visibility = np.array(
            [
                landmark.visibility if landmark.visibility is not None else 0.0
                for landmark in landmarks
            ],
            dtype=np.float64,
        )

        world_points: np.ndarray | None = None
        depth_source = "none"

        if result.pose_world_landmarks:
            world = result.pose_world_landmarks[0]
            world_points = np.array(
                [(landmark.x, landmark.y, landmark.z) for landmark in world],
                dtype=np.float64,
            )
            depth_source = "mediapipe_world"

        return RawPose(
            schema_id=MEDIAPIPE_POSE.schema_id,
            frame_index=frame_index,
            timestamp=timestamp,
            person_index=0,
            points=points,
            visibility=visibility,
            world_points=world_points,
            depth_source=depth_source,
        )

    def close(self) -> None:
        self._landmarker.close()
