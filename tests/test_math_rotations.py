"""Tests for quaternion helpers (roadmap Phase 10)."""

import math

import pytest

from app.math.rotations import Quaternion, shortest_arc
from app.models.pose import Vector3


def _angle_of(quaternion: Quaternion) -> float:
    return 2 * math.acos(min(1.0, abs(quaternion.w)))


def test_identity_is_unit_and_does_nothing() -> None:
    identity = Quaternion.identity()

    assert identity.is_unit()
    result = identity.apply(Vector3(3.0, -2.0, 1.0))
    assert (result.x, result.y, result.z) == pytest.approx((3.0, -2.0, 1.0))


def test_shortest_arc_between_equal_directions_is_identity() -> None:
    rotation = shortest_arc(Vector3(0.0, 1.0, 0.0), Vector3(0.0, 5.0, 0.0))

    assert _angle_of(rotation) == pytest.approx(0.0, abs=1e-6)


def test_shortest_arc_ninety_degrees() -> None:
    rotation = shortest_arc(Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0))

    assert _angle_of(rotation) == pytest.approx(math.pi / 2, abs=1e-6)
    rotated = rotation.apply(Vector3(1.0, 0.0, 0.0))
    assert (rotated.x, rotated.y, rotated.z) == pytest.approx((0.0, 1.0, 0.0), abs=1e-6)


def test_shortest_arc_antiparallel_is_half_turn() -> None:
    rotation = shortest_arc(Vector3(1.0, 0.0, 0.0), Vector3(-1.0, 0.0, 0.0))

    assert _angle_of(rotation) == pytest.approx(math.pi, abs=1e-6)
    rotated = rotation.apply(Vector3(1.0, 0.0, 0.0))
    assert (rotated.x, rotated.y, rotated.z) == pytest.approx((-1.0, 0.0, 0.0), abs=1e-6)


def test_shortest_arc_with_zero_vector_is_identity() -> None:
    rotation = shortest_arc(Vector3(0.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0))

    assert _angle_of(rotation) == pytest.approx(0.0, abs=1e-6)


def test_multiply_and_inverse_round_trip() -> None:
    rotation = shortest_arc(Vector3(1.0, 0.0, 0.0), Vector3(0.3, 0.7, 0.2))

    round_trip = rotation.inverse().multiply(rotation)

    assert _angle_of(round_trip) == pytest.approx(0.0, abs=1e-6)


def test_multiply_composes_rotations() -> None:
    quarter = shortest_arc(Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0))

    half = quarter.multiply(quarter)
    rotated = half.apply(Vector3(1.0, 0.0, 0.0))

    assert (rotated.x, rotated.y, rotated.z) == pytest.approx((-1.0, 0.0, 0.0), abs=1e-6)
