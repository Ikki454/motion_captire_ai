"""Small vector helpers on :class:`app.models.pose.Vector3`."""

import math

from app.models.pose import Vector3


def subtract(a: Vector3, b: Vector3) -> Vector3:
    """Return ``a - b``."""

    return Vector3(a.x - b.x, a.y - b.y, a.z - b.z)


def add(a: Vector3, b: Vector3) -> Vector3:
    """Return ``a + b``."""

    return Vector3(a.x + b.x, a.y + b.y, a.z + b.z)


def scale(v: Vector3, factor: float) -> Vector3:
    """Return ``v * factor``."""

    return Vector3(v.x * factor, v.y * factor, v.z * factor)


def length(v: Vector3) -> float:
    """Return the Euclidean length of ``v``."""

    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def midpoint(a: Vector3, b: Vector3) -> Vector3:
    """Return the point halfway between ``a`` and ``b``."""

    return Vector3((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)


def normalize(v: Vector3) -> Vector3:
    """Return ``v`` scaled to unit length.

    Returns a zero vector when ``v`` has (near-)zero length.
    """

    magnitude = length(v)
    if magnitude < 1e-9:
        return Vector3(0.0, 0.0, 0.0)
    return Vector3(v.x / magnitude, v.y / magnitude, v.z / magnitude)
