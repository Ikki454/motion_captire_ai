"""Explicit conversions between the coordinate spaces used in the pipeline.

See ``architecture.md`` section 9. No other module converts coordinates
silently: a function that changes space is named for it and lives here.
"""

from enum import Enum

from app.models.pose import Vector3


class CoordinateSpace(str, Enum):
    """The coordinate spaces pose data can live in."""

    IMAGE_PIXELS = "image_pixels"  # 2D, origin top-left, y down
    CANONICAL_WORLD = "canonical_world"  # 3D, right-handed, y up
    BLENDER_WORLD = "blender_world"  # 3D, right-handed, z up


def image_to_canonical(x: float, y: float) -> Vector3:
    """Map a 2D image-pixel point to ``CANONICAL_WORLD``.

    Image space has y growing downward; canonical space is y-up. The x
    axis is unchanged and z is 0 (the image plane). Scale is preserved
    (still in pixels) -- callers that only need directions normalise.
    """

    return Vector3(x=x, y=-y, z=0.0)


def mediapipe_world_to_canonical(x: float, y: float, z: float) -> Vector3:
    """Map a MediaPipe world landmark to ``CANONICAL_WORLD``.

    MediaPipe world coordinates are metres, origin at the hip midpoint,
    with x to the subject's right, y downward, and z pointing away from
    the camera. Canonical space is y-up with z toward the viewer, so y
    and z are flipped (both flips keep the frame right-handed).
    """

    return Vector3(x=x, y=-y, z=-z)
