"""Quaternion rotations, backed by :mod:`scipy.spatial.transform`.

:class:`Quaternion` stores components as ``(w, x, y, z)``. SciPy uses
``(x, y, z, w)``; the conversions are contained here.
"""

from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation

from app.math.vectors import length, normalize
from app.models.pose import Vector3


@dataclass(frozen=True)
class Quaternion:
    """A unit quaternion in ``(w, x, y, z)`` order."""

    w: float
    x: float
    y: float
    z: float

    @classmethod
    def identity(cls) -> "Quaternion":
        """Return the identity rotation."""

        return cls(1.0, 0.0, 0.0, 0.0)

    @classmethod
    def from_rotation(cls, rotation: Rotation) -> "Quaternion":
        """Build a :class:`Quaternion` from a SciPy :class:`Rotation`."""

        x, y, z, w = rotation.as_quat()
        return cls(float(w), float(x), float(y), float(z))

    def to_rotation(self) -> Rotation:
        """Return the equivalent SciPy :class:`Rotation`."""

        return Rotation.from_quat([self.x, self.y, self.z, self.w])

    def multiply(self, other: "Quaternion") -> "Quaternion":
        """Return ``self * other`` (apply ``other`` first, then ``self``)."""

        return Quaternion.from_rotation(self.to_rotation() * other.to_rotation())

    def inverse(self) -> "Quaternion":
        """Return the inverse rotation."""

        return Quaternion.from_rotation(self.to_rotation().inv())

    def apply(self, vector: Vector3) -> Vector3:
        """Rotate ``vector`` by this quaternion."""

        rotated = self.to_rotation().apply([vector.x, vector.y, vector.z])
        return Vector3(float(rotated[0]), float(rotated[1]), float(rotated[2]))

    def is_unit(self, tolerance: float = 1e-6) -> bool:
        """Return whether the quaternion has unit norm."""

        norm = np.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        return abs(norm - 1.0) <= tolerance


def shortest_arc(source: Vector3, target: Vector3) -> Quaternion:
    """Return the smallest rotation taking direction ``source`` to ``target``.

    Both vectors are normalised first. Zero-length inputs, or (anti)parallel
    directions, are handled explicitly.
    """

    a = normalize(source)
    b = normalize(target)

    if length(a) < 0.5 or length(b) < 0.5:
        return Quaternion.identity()

    dot = a.x * b.x + a.y * b.y + a.z * b.z
    dot = max(-1.0, min(1.0, dot))

    if dot > 1.0 - 1e-9:
        return Quaternion.identity()

    if dot < -1.0 + 1e-9:
        axis = _any_perpendicular(a)
        return Quaternion.from_rotation(Rotation.from_rotvec(np.pi * _to_array(axis)))

    axis = np.cross(_to_array(a), _to_array(b))
    axis = axis / np.linalg.norm(axis)
    angle = np.arccos(dot)
    return Quaternion.from_rotation(Rotation.from_rotvec(angle * axis))


def _to_array(v: Vector3) -> np.ndarray:
    return np.array([v.x, v.y, v.z], dtype=np.float64)


def _any_perpendicular(v: Vector3) -> Vector3:
    reference = Vector3(1.0, 0.0, 0.0) if abs(v.x) < 0.9 else Vector3(0.0, 1.0, 0.0)
    cross = np.cross(_to_array(v), _to_array(reference))
    cross = cross / np.linalg.norm(cross)
    return Vector3(float(cross[0]), float(cross[1]), float(cross[2]))
