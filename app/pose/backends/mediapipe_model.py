"""Download and locate the MediaPipe pose-landmark model.

MediaPipe 1.0 removed the bundled ``solutions`` pipelines. The Tasks API
``PoseLandmarker`` needs a ``.task`` model file that is not shipped with the
package. This module downloads the "lite" pose model from the official
MediaPipe model store and reports where it lives.

Nothing here runs automatically. Fetch the model once with::

    python -m app.pose.backends.mediapipe_model
"""

from pathlib import Path
from urllib.request import urlopen

POSE_LANDMARKER_LITE_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)

_MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
_MODEL_FILENAME = "pose_landmarker_lite.task"


def default_model_path() -> Path:
    """Return the path where the pose model is expected to live."""

    return _MODELS_DIR / _MODEL_FILENAME


def download_default_model(*, force: bool = False) -> Path:
    """Download the lite pose model to :func:`default_model_path`.

    Args:
        force: Re-download even when the file is already present.

    Returns:
        The path to the model file.
    """

    destination = default_model_path()

    if destination.exists() and not force:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)

    with urlopen(POSE_LANDMARKER_LITE_URL) as response:
        payload = response.read()

    destination.write_bytes(payload)
    return destination


if __name__ == "__main__":
    path = download_default_model()
    print(f"Pose model ready at: {path}")
