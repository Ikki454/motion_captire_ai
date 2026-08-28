"""Convert canonical (Y-up) motion data to Blender's (Z-up) world.

Standard library only. This mirrors the intent of
``app/math/coordinates.py`` but is a separate, dependency-free
implementation -- the two ends of the interchange must agree on the
convention, not share code.

Canonical world: right-handed, X right, Y up, Z toward the viewer.
Blender world:   right-handed, X right, Y forward, Z up.
The mapping ``(x, y, z) -> (x, -z, y)`` is a +90 deg rotation about X.
"""

import math

Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]

# Quaternion of a +90 degree rotation about the X axis.
_HALF = math.sqrt(0.5)
_FRAME: Quaternion = (_HALF, _HALF, 0.0, 0.0)


def quaternion_multiply(a: Quaternion, b: Quaternion) -> Quaternion:
    """Return the Hamilton product ``a * b``."""

    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def quaternion_conjugate(q: Quaternion) -> Quaternion:
    """Return the conjugate (inverse, for unit quaternions) of ``q``."""

    w, x, y, z = q
    return (w, -x, -y, -z)


def rotate_vector(q: Quaternion, v: Vector3) -> Vector3:
    """Rotate vector ``v`` by unit quaternion ``q``."""

    result = quaternion_multiply(
        quaternion_multiply(q, (0.0, *v)), quaternion_conjugate(q)
    )
    return (result[1], result[2], result[3])


def canonical_to_blender_location(x: float, y: float, z: float) -> Vector3:
    """Map a canonical-world point to Blender-world coordinates."""

    return (x, -z, y)


def canonical_to_blender_quaternion(
    w: float, x: float, y: float, z: float
) -> Quaternion:
    """Express a canonical-world rotation in Blender-world coordinates."""

    return quaternion_multiply(
        quaternion_multiply(_FRAME, (w, x, y, z)),
        quaternion_conjugate(_FRAME),
    )
